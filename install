#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" install.py
    ...An installer for python projects.

    After configuration, python projects can be installed locally or
    globally in linux.
    Designed to be dropped into any project directory.
    Executables are symlinked to the bin directry from the application's
    install directory.

    -Christopher Welborn 09-16-2014
"""
import json
import os
import re
import shutil
import subprocess
import sys
from collections import UserList

from docopt import docopt

NAME = 'Python Installer'
VERSION = '0.0.7'
VERSIONSTR = '{} v. {}'.format(NAME, VERSION)
SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])
CWD = os.getcwd()

USAGESTR = """{versionstr}
    Usage:
        {script} -h | -v
        {script} [preinstall] [-u] [-D]
        {script} (uninstall | remove) [-D]

    Options:
        -D,--debug    : Don't write or create anything.
        -h,--help     : Show this help message.
        -u,--user     : Install for this user only.
        -v,--version  : Show version.

    The default action is to install the application.
    The 'preinstall' command will just run any pre-install commands.
""".format(script=SCRIPT, versionstr=VERSIONSTR)


def main(argd):
    """ Main entry point, expects doctopt arg dict as argd """

    # The Installer does all the heavy lifting,
    # I am simply passing it a few settings and reporters for this cmdline app.
    installer = Installer(
        use_global=not argd['--user'],
        debug=argd['--debug'],
        reporter=print,
        debug_reporter=print,
        error_reporter=fail,
    )

    if argd['uninstall'] or argd['remove']:
        # Run uninstall instead.
        if installer.uninstall_files():
            print('\nSuccessfully uninstalled.')
            return 0
        else:
            print('\nUnable to uninstall, sorry.')
            return 1
    elif argd['preinstall']:
        # Just run the pre-install commands.
        return installer.run_commands()

    # Do an installation.
    if installer.install_files():
        print('\nSuccessfully installed.')
    else:
        print('\nHalf-installed, sorry.')
        return 1
    # Successful install.
    return 0


def fail(reason):
    """ Error reporter for Installer(). Prints the message and exits. """
    print('\n{}\n'.format(reason))
    sys.exit(1)


def try_reporter(reporter):
    """ If reporter is a callable, return it. Otherwise return a callable
        that does nothing.
    """
    return reporter if (reporter and callable(reporter)) else (lambda x: None)


class Command(UserList):
    """ A command argument list, with helper methods to run the command.
    """
    def __init__(self, args=None, name=None, debug_reporter=None):
        super().__init__(args or [])
        self.name = name or (self[0] if self else None)
        self.report_debug = try_reporter(debug_reporter)

    def __bool__(self):
        return bool(self.data)

    def __repr__(self):
        typename = type(self).__name__
        return f'{typename}({self.data!r}, name={self.name!r})'

    def __str__(self):
        if self.name:
            return f'{self.name}: {" ".join(self) or "<no command>"}'
        return ' '.join(self) or '<no command>'

    @classmethod
    def from_dict(cls, d, use_global=False, debug_reporter=None):
        report_debug = try_reporter(debug_reporter)
        name = d.get('name', d.get('command', [''])[0])
        if use_global:
            cmd = d['command']
            report_debug(f'Using global command: {cmd}')
        else:
            # Use user command if available.
            cmd = d.get('command_user', d['command'])
            report_debug(f'Using user command: {cmd}')
        return cls(cmd, name=name, debug_reporter=debug_reporter)

    @classmethod
    def from_list(cls, args, debug_reporter=None):
        try_reporter(debug_reporter)(f'Using global list: {args!r}')
        return cls(args, debug_reporter=debug_reporter)

    @classmethod
    def from_str(cls, s, debug_reporter=None):
        try_reporter(debug_reporter)(f'Using global str: {s!r}')
        return cls(s.split(' '), debug_reporter=debug_reporter)

    def run(self):
        try:
            subprocess.check_call(self)
        except subprocess.CalledProcessError:
            return 1
        return 0


class Commands(UserList):
    """ A list of Command objects, with helper methods to run/inspect them.
    """
    def __init__(self, commands=None, use_global=False, debug_reporter=None):
        super().__init__(commands or [])
        self.report_debug = try_reporter(debug_reporter)
        self.use_global = use_global
        self._parse_commands()
        self.errors = 0

    def _parse_commands(self):
        """ Ensure all command items are Command instances.
            Convert them if needed.
        """
        for i, x in enumerate(self[:]):
            if isinstance(x, Command):
                continue
            if isinstance(x, list):
                # An argument list.
                self[i] = Command.from_list(
                    x,
                    debug_reporter=self.report_debug,
                )
            elif isinstance(x, dict):
                # A command info dict:
                #   {'name': 'x', command': [..], 'command_user': [..]}}
                self[i] = Command.from_dict(
                    x,
                    use_global=self.use_global,
                    debug_reporter=self.report_debug,
                )
            elif isinstance(x, str):
                # A command string.
                self[i] = Command.from_str(
                    x,
                    debug_reporter=self.report_debug,
                )

    def run(self):
        self.errors = 0
        for cmd in self:
            self.report_debug(f'Running: {cmd}')
            self.errors += cmd.run()
        return self.errors


class Installer(object):

    """ Reads installer config, or uses default settings to search the current
        directory for files to install. Destination is determined through
        configuration, or by inspecting the current directory.
        Finds executables through configuration, or by inspecting executable
        files in the current directory, or finally by looking for .py files
        in the current directory. Executables are symlinked from the
        appropriate /bin directory to the application's install directory.
    """
    class FatalError(EnvironmentError):

        """ Raised on all file access/creation/deletion errors. """
        pass

    # Config to build from, or to use when no other config is provided.
    default_config = {
        # Default paths, files, behavior.
        'paths': {
            # Override using standard exe dirs and install_type choice.
            'exe_base': None,
            # Override using standard app dirs and install_type choice.
            'install_base': None,
            # Top level directory name under the main app dir.
            'toplevel': os.path.split(CWD)[1],
            # Walk the dir looking for files?
            'recurse': False,
            # Included file patterns (relative to the current dir).
            'files': [],
            # Excluded file patterns (relative to the current dir).
            'excludes': [],
            # Executable files (for installation in /usr/bin or /home/?/bin)
            'executables': []
        },
        # Default is no dependencies (not implemented yet).
        'dependencies': {},
        # Default is user-specified from init (use_global = True/False).
        # 'global' or 'local' can be used to force a preference.
        'install_type': None,
        # Extra commands to run before install.
        'commands': Commands(),
    }

    # Global directories for installing applications.
    global_app_dirs = (
        '/usr/local/share',
        '/opt',
        '/usr/share'
    )

    # Global directories for installing executable symlinks.
    global_exe_dirs = (
        '/usr/local/bin',
        '/usr/share/local/bin',
        '/usr/bin'
    )

    # Home (/home/<user>) directories for applications.
    home_app_dirs = (
        '.local/share',
        'local/share'
    )

    # Home (/home/<user>) directories for installing executable symlinks.
    home_exe_dirs = (
        'bin',
        '.local/bin',
        'local/bin'
    )

    # Config file to read from.
    config_file = 'installer.json'
    # Defailt file to save the installed-files list.
    installed_file = 'installed_files.txt'

    def __init__(self, **kwargs):
        """ Initializes the installer, gathers files/dest-files and other
            info. Gathers everything needed to run self.install_files()
            Possibly raises Installer.FatalError, when error_reporter isn't
            set.

            Arguments:
                use_global     : Do a global installation instead of local.
                config         : Premade config to use, instead of parsing the
                                 the config file.
                debug          : Debug mode, if True nothing is ever created.
                reporter       : A function that accepts one argument, a str.
                                 Can be None.
                                 If set, the reporter() is called with status
                                 messages.
                debug_reporter : Same as reporter, but called with debug
                                 messages. Only used when debug == True.
                error_reporter : Same as reporter, but called when fatal errors
                                 happen. If not set, Installer.FatalError is
                                 raised instead.
        """
        # Reporters need to be set before anything else, in case of errors.
        # Dummy function is used for debug report if nothing is set.
        self.reporter = kwargs.get('reporter', lambda s: None)
        self.debug_reporter = kwargs.get('debug_reporter', lambda s: None)
        self.set_error_reporter(kwargs.get('error_reporter', None))
        # Global, or local install.
        self.use_global = kwargs.get('use_global', False)
        self.debug = kwargs.get('debug', False)
        self.cwd = os.getcwd()
        self.scriptname = os.path.split(sys.argv[0])[1]

        # Files that have been created during this run.
        self.created = set()

        # Parse config if not passed by the user.
        self.config = kwargs.get('config', None) or self.load_config()

    @staticmethod
    def choose_path(trydirs, basedir=None):
        """ Pick a directory path from a list.
            First one that exists is returned.
            If basedir is given, each dir in trydirs is joined to it first.
            Returns None if no path could be found.
        """
        for trydir in trydirs:
            if basedir:
                trydir = os.path.join(basedir, trydir)
            if os.path.exists(trydir):
                return trydir
        return None

    def clean_up(self, reason=None):
        """ Clean up any created files for this run.
            Returns True if files were cleaned.
            Returns False if no files needed cleaning, or there was an error.
        """
        files = self.created.copy()
        if not files:
            return False
        if reason:
            self.report(reason)

        filelen = len(files)
        fileplural = 'file' if filelen == 1 else 'files'
        if self.debug:
            msg = 'Would\'ve cleaned'
        else:
            msg = 'Trying to clean up'

        self.report('\n{} {} {}...'.format(msg, filelen, fileplural))
        # Clean-up needed.
        cleanerrors = self.remove_files(files)
        if cleanerrors:
            fileplural = 'file' if cleanerrors == 1 else 'files'
            failfmt = '\nFailed to remove {} {}!'
            self.report(failfmt.format(cleanerrors, fileplural))
            return False
        # Files were cleaned.
        self.report('\nClean up was a success.')
        return True

    def dictmerge(self, basedict, newdict):
        """ Merge to dicts and return the result.
            Dicts are merged recursively so that old keys are always kept and
            new key values overwrite old ones.
            d =  {
                1: True,
                3: False,
                4: {
                    'a': True,
                    'c': False
                }
            }
            d2 = {
                2: True,
                3: True,
                4: {
                    'b': True,
                    'c': True
                }
            }
            d3 = dictmerge(d, d2)
            d3 == {
                1: True,
                2: True,
                3: True,
                4: {
                    'a':True, 'b': True, 'c': True
                }
            }
        """
        merged = {}
        for k in basedict:
            v = basedict[k]
            newv = newdict.get(k, None)
            if newv is not None:
                if isinstance(v, dict) and isinstance(newv, dict):
                    merged[k] = self.dictmerge(v, newv)
                else:
                    merged[k] = newv
            else:
                merged[k] = v
        # Grab new keys.
        oldkeys = basedict.keys()
        for newk in newdict:
            if newk not in oldkeys:
                merged[newk] = newdict[newk]
        return merged

    def ensure_dest_dir(self):
        """ Ensure that the top level destination dir exists,
            make it if needed.
            Returns install_dir.
        """

        appdir = self.get_base_dir()
        toplevel = self.get_toplevel_dir()
        installdir = os.path.join(appdir, toplevel)
        if os.path.exists(installdir):
            if not os.access(installdir, os.W_OK):
                errfmt = 'No permissions to write to: {}'
                self.report_error(errfmt.format(installdir))
        else:
            # Make the directory.
            if self.debug:
                self.report_debug('\nWould\'ve created: {}'.format(installdir))
                self.created.add(installdir)
                return installdir

            try:
                os.makedirs(installdir)
                self.created.add(installdir)
                self.installdir_created = True
            except OSError as ex:
                errfmt = 'Error making the install directory: {}\n  {}'
                self.report_error(errfmt.format(installdir, ex))
        # Exists, or created it, success.
        return installdir

    def fix_user_arg(self, s):
        """ Replace '{user_args}' with user arguments if needed. """
        if self.use_global:
            repl = ''
        else:
            repl = '--user'
        return s.format(user_args=repl)

    def get_base_dir(self):
        """ Determine the base installation directory based on config. """

        if self.config['paths'].get('install_base', None):
            return self.parse_user_path(self.config['paths']['install_base'])

        if self.use_global:
            return self.get_global_app_dir()

        # Default local install.
        return self.get_home_app_dir()

    def get_default_exes(self):
        """ Get the default executables to install when none are provided in
            the config file.
        """
        defaults = [f for f in self.srcfiles if os.access(f, os.X_OK)]
        if defaults:
            # Return truly executable files.
            destexes = []
            for destfile in self.destfiles:
                destname = os.path.split(destfile)[1]
                for srcfile in defaults:
                    srcname = os.path.split(srcfile)[1]
                    # Mark file for symlinking, but not the installer itself.
                    # (it will be copied to the dest dir for later uninstall)
                    if (srcname == destname) and (srcname != self.scriptname):
                        destexes.append(destname)
                        break
            if destexes:
                self.report_debug('\nUsing true executable files.')
                return destexes

        # No executables found, just use the .py files.
        self.report_debug('\nUsing python files as executables.')
        for filepath in self.destfiles:
            ext = os.path.splitext(filepath)[1]
            if (not ext) or (ext == '.py'):
                filename = os.path.split(filepath)[1]
                if not filename.startswith('_'):
                    defaults.append(filename)
        return defaults

    def get_dest_files(self):
        """ Get a list of full paths to install based on relative file names.
        """
        if not self.installdir:
            self.installdir = self.ensure_dest_dir()
        destfiles = []
        for filepath in self.srcfiles:
            destfiles.append(os.path.join(self.installdir, filepath))
        return destfiles

    @staticmethod
    def get_env_path():
        """ Returns the $PATH variable as a set().
            For checking to see if paths are in $PATH.
        """
        return set(os.environ.get('PATH', '').split(':'))

    def get_exe_dir(self):
        """ Determine which exe dir to use, and return it. """
        # User is overriding automatic choice based on install_type.
        if self.config['paths'].get('exe_base', None):
            return self.parse_user_path(self.config['paths']['exe_base'])

        if self.use_global:
            return self.get_global_exe_dir()
        return self.get_home_exe_dir()

    def get_executable_files(self):
        """ Get executable files to be installed in ../bin or ~/../bin
            Chooses all .py files if none are provided in config.
        """
        if not self.config:
            self.config = self.load_config()
        configexes = self.config['paths']['executables']
        if not configexes:
            configexes = self.get_default_exes()
            if not configexes:
                self.report_debug('\nNo default executable files found!')

        exes = []
        for destfile in self.destfiles:
            for configexe in configexes:
                if destfile.endswith(configexe):
                    exes.append(destfile)
                    break
        return exes

    def get_files(self):
        """ Retrieve file paths to install, using config to determine which
            files are used.
        """
        if not self.config:
            self.config = self.load_config()

        includepats = self.config['paths']['files']
        if not includepats:
            # Default action is to include all files.
            includepats = [re.compile('.+')]

        excludepats = self.config['paths']['excludes']
        filepaths = []
        if self.config['paths']['recurse']:
            for root, dirs, files in os.walk(self.cwd):
                for filename in files:
                    fullpath = os.path.join(root, filename)
                    relativepath = fullpath.replace(self.cwd, '')
                    while relativepath.startswith('/'):
                        relativepath = relativepath[1:]

                    if filename == self.scriptname:
                        # Always include the installer.
                        filepaths.append(relativepath)
                    else:
                        for includepat in includepats:
                            if includepat.search(relativepath):
                                filepaths.append(relativepath)
                                break
        else:
            for filename in os.listdir(self.cwd):
                if filename == self.scriptname:
                    filepaths.append(filename)
                else:
                    for includepat in includepats:
                        fullpath = os.path.join(self.cwd, filename)
                        if (includepat.search(filename) and
                                os.path.isfile(fullpath)):
                            filepaths.append(filename)
                            break

        # Parse excludes
        files = []
        for filepath in filepaths:
            if filepath == self.scriptname:
                # Never exclude the installer.
                files.append(filepath)
                continue
            for excludepat in excludepats:
                if excludepat.search(filepath):
                    break
            else:
                # Passed the exlude patterns.
                files.append(filepath)
        return files

    def get_global_app_dir(self):
        """ Get main directory for installing apps globally. """
        globalapps = self.choose_path(Installer.global_app_dirs)
        if globalapps:
            return globalapps
        self.report_error('Unable to determine global app directory!')

    def get_global_exe_dir(self):
        """ Get directory for global executables. """
        globalexe = self.choose_path(Installer.global_exe_dirs)
        if globalexe:
            return globalexe
        self.report_error('Unable to determine global executables directory!')

    def get_home_app_dir(self, home=None):
        """ Get main home directory for installing apps. """

        basedir = home or self.get_home_dir()
        homeapps = self.choose_path(Installer.home_app_dirs, basedir=basedir)
        if homeapps:
            return homeapps

        self.report_error('Unable to determine user app directory!')

    def get_home_dir(self):
        """ Get user's home directory. """
        home = os.path.expanduser('~')
        if os.path.exists(home):
            return home
        home = os.environ.get('HOME', None)
        if home:
            return home
        user = os.environ.get('USER', None)
        if user:
            home = os.path.join('/home', user)
            if os.path.exists(home):
                return home
        # Fail.
        self.report_error('Unable to determine /home directory!')

    def get_home_exe_dir(self, home=None):
        """ Get directory for user executables. """
        basedir = home or self.get_home_dir()
        homeexes = self.choose_path(Installer.home_exe_dirs, basedir=basedir)
        if homeexes:
            return homeexes
        self.report_error('Unable to determine user\'s executables directory!')

    def get_toplevel_dir(self):
        """ Get top level directory (for installing in apps dir.)
            If config is present use it, otherwise determine the top level
            directory from the current working dir.
        """
        if self.config['paths']['toplevel']:
            return self.config['paths']['toplevel']

        return os.path.split(self.cwd)[1].strip('/')

    def install_exes(self):
        """ Installs symlinks in the appropriate directory for executables. """
        if not os.access(self.exedir, os.W_OK):
            errmsg = 'No permissions to write to: {}'.format(self.exedir)
            if self.debug:
                debugfmt = '\nDebug mode, not failing: {}'
                self.report_debug(debugfmt.format(errmsg))
            else:
                self.report_error(errmsg)

        exes = self.get_executable_files()
        if not exes:
            self.report('\nNo executable files to install.')
            return None

        # For warning the user if the target dir is not in $PATH
        env_path = self.get_env_path()

        for exepath in exes:
            linkname = os.path.splitext(os.path.split(exepath)[1])[0]
            destlink = os.path.join(self.exedir, linkname)
            if self.debug:
                debugfmt = 'Would\'ve symlinked: {} -> {}'
                self.report_debug(debugfmt.format(destlink, exepath))
                self.created.add(destlink)
                continue
            try:
                os.symlink(exepath, destlink)
                self.created.add(destlink)
                self.report('Symlinked: {} -> {}'.format(destlink, exepath))
            except OSError as ex:
                errfmt = 'Failed to create symlink: {} -> {}\n  {}'
                self.report_error(errfmt.format(destlink, exepath, ex))
            else:
                # Created link, check the path if $PATH is available.
                linkdir = os.path.split(destlink)[0]
                if env_path and (linkdir not in env_path):
                    self.report('\n'.join((
                        '    Directory is not in $PATH: {}',
                        '    \'{}\' may not be available globally.')
                    ).format(exepath, linkname))
        return None

    def install_files(self):
        """ Installs application files. """
        # Prepare for installation.
        self.pre_install()

        for i, srcfile in enumerate(self.srcfiles):
            destfile = self.destfiles[i]
            destdir = os.path.split(destfile)[0]
            if not os.path.isdir(destdir):
                if self.debug:
                    self.report_debug(
                        'Would\'ve created dir: {}'.format(destdir)
                    )
                    self.created.add(destdir)
                else:
                    try:
                        os.makedirs(destdir, exist_ok=True)
                    except OSError as ex:
                        self.report_error(
                            'Failed to create dir: {}\n  {}'.format(
                                destdir,
                                ex,
                            )
                        )
            if self.debug:
                debugfmt = 'Would\'ve copied: {} -> {}'
                self.report_debug(debugfmt.format(srcfile, destfile))
                self.created.add(destfile)
                continue
            try:
                copiedname = shutil.copy2(srcfile, destfile)
                if sys.version_info.major < 3:
                    # Python 2, shutil returns None.
                    copiedname = destfile
                self.report('Installed: {}'.format(copiedname))
                self.created.add(copiedname)
            except OSError as ex:
                errfmt = 'Failed to copy: {} -> {}\n  {}'
                self.report_error(errfmt.format(srcfile, destfile, ex))

        self.install_exes()
        # Success,write the installed_files file.
        return self.write_installed_files()

    def load_config(self):
        """ Load config from the config file, or use default config.
            Defaults are used for missing config items.
        """
        config = Installer.default_config.copy()
        try:
            with open(Installer.config_file, 'r') as f:
                rawconfig = f.read()
        except FileNotFoundError:
            # No config file, return defaults.
            self.report_debug('Using default config.')
            return config
        except OSError as ex:
            # Unable to read config.
            errfmt = '\nUnable to read config file!: {}\n  {}'
            self.report_error(errfmt.format(Installer.config_file, ex))

        try:
            newconfig = self.parse_config(rawconfig)
        except ValueError as ex:
            # Bad config file.
            self.report_error('\n'.join((
                '\nConfiguration is corrupt. Make sure it is valid JSON.',
                '{}')).format(ex)
            )
            # Unreachable code with proper error reporter.
            return config

        # Update defaults with new config.
        config = self.dictmerge(config, newconfig)
        self.report_debug('Using config:')
        self.report_debug(json.dumps(config, indent=4, sort_keys=True))

        # Parse files/excludes patterns.
        config['paths']['files'] = self.parse_patterns(
            'files',
            config['paths'])
        config['paths']['excludes'] = self.parse_patterns(
            'excludes',
            config['paths'])

        # Global/local install in config overrides user setting.
        installtype = config.get('install_type', None)
        if installtype:
            installtype = installtype.lower()
            if installtype == 'global':
                self.use_global = True
            elif installtype == 'local':
                self.use_global = False
        return config

    def parse_config(self, configdata):
        """ Parses configuration data as a string.
            Ignores C style comments.
            Possibly raises ValueError on bad JSON config after parsing.
            Returns JSON parsed dict.
            Returns None on failure.
        """
        # Strip comments.
        commentpat = re.compile(
            r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'',
            re.DOTALL | re.MULTILINE)
        stripped_data = commentpat.sub('', configdata)
        # Parse as json (may raise ValueError)
        try:
            config = json.loads(stripped_data)
        except ValueError:
            # Let the error bubble up, but report the JSON that failed.
            self.report_debug('Invalid JSON:\n{}'.format(configdata))
            raise
        return config

    def parse_patterns(self, configname, pathconfig):
        """ Parse a list of regex pattern strings into actual regex patterns.
            Exits the installer if a bad pattern is found.
        """
        patterns = []
        for pattext in pathconfig[configname]:
            try:
                pat = re.compile(pattext)
            except re.error as expat:
                errfmt = '\n'.join((
                    'Bad config for {}, not a valid regex pattern: {}',
                    '  {}'))
                self.report_error(errfmt.format(configname, pattext, expat))
            else:
                patterns.append(pat)
        return patterns

    @staticmethod
    def parse_user_path(path):
        """ Parses paths set by the user in config.
            Expands user paths and absolute paths.
        """
        return os.path.abspath(os.path.expanduser(path)) if path else path

    def pre_install(self):
        """ Gather all the info needed for an install.
            Possibly raises Installer.FatalError.
        """
        # Executable directory for install.
        self.exedir = self.get_exe_dir()
        # Set when the install directory had to be created.
        self.installdir_created = False
        # Destination directory for install.
        self.installdir = self.ensure_dest_dir()

        # Source files for installation.
        self.srcfiles = self.get_files()
        # Destination file paths.
        self.destfiles = self.get_dest_files()
        # Executable files from the install dir.
        self.exes = self.get_executable_files()
        # Pre-install commands.
        self.cmd_errors = self.run_commands()

    def read_installed_files(self):
        """ Read previously installed files into a list. """
        try:
            with open(Installer.installed_file, 'r') as f:
                files = [l.strip() for l in f.readlines()]
        except FileNotFoundError:
            # No previously installed files.
            return None
        except OSError as ex:
            failfmt = '\nFailed to read {}:\n{}'
            self.report(failfmt.format(Installer.installed_file, ex))
            return None
        return files

    def remove_files(self, files):
        """ Deletes/removes a list files and directories.
            For files, `os.remove()` is used, but if an item is determined to
            be a directory, `shutil.rmtree()` is used instead.
            Returns number of files that errored while removing so on success
            it will return 0.
        """
        # Sort for report-formatting, but also tries to delete parent dirs
        # first.
        try:
            files.sort()
        except AttributeError:
            # None, or non-sortable object passed.
            return 0

        if self.debug:
            self.report_debug('Would\'ve removed:')
            self.report_debug('    {}'.format('\n    '.join(files)))
            return 0

        cleanerrors = 0
        for filepath in files:
            # File may have been removed with a directory removal.
            if os.path.exists(filepath):
                if os.path.isdir(filepath):
                    filetype = 'directory'
                    removefunc = shutil.rmtree
                else:
                    filetype = 'file'
                    removefunc = os.remove
                try:
                    removefunc(filepath)
                    self.report('Removed {}: {}'.format(filetype, filepath))
                except Exception as ex:
                    failfmt = 'Failed to remove: {}\n  {}'
                    self.report(failfmt.format(filepath, ex))
                    cleanerrors += 1
        return cleanerrors

    def report(self, msg):
        """ Use the reporter to report a standard message if available. """
        self.reporter(msg)

    def report_debug(self, msg):
        """ Use the reporter to report debug messages if available. """
        if self.debug:
            self.debug_reporter(msg)

    def report_error(self, msg):
        """ Use the error reporter to report a fatal error if available. """
        self.clean_up(reason=msg)
        self.error_reporter(msg)

    def run_commands(self):
        commands = Commands(
            self.config.get('commands', []),
            use_global=self.use_global,
            debug_reporter=self.report_debug,
        )
        if not commands:
            self.report_debug('No commands to run.')
            return 0
        return commands.run()

    def set_error_reporter(self, reporter):
        """ Set the error reporter, or build an exception raiser if none is
            supplied.
        """
        if reporter:
            self.error_reporter = reporter
        else:
            # Build a function that raises FatalError with a message.
            def err_raise(msg):
                raise Installer.FatalError(msg)
            self.error_reporter = err_raise

    def uninstall_files(self):
        """ Uninstall all files in installed_files.txt """
        files = self.read_installed_files()
        if not files:
            failfmt = '\nNo files to remove in: {}'
            self.report(failfmt.format(Installer.installed_file))
            return False

        errorfiles = self.remove_files(files)
        if errorfiles:
            if errorfiles == 1:
                fileplural = 'file/directory'
            else:
                fileplural = 'files/directories'
            failfmt = '\nFailed to remove {} {}!'
            self.report(failfmt.format(errorfiles, fileplural))
            return False
        # Success
        return True

    def write_installed_files(self):
        """ Save installed/created files to installed_files.txt """
        if self.debug:
            debugfmt = '\nDebug mode, Not writing {}...'
            self.report_debug(debugfmt.format(Installer.installed_file))
            return True

        if not self.created:
            # No files were created.
            return False

        try:
            with open(Installer.installed_file, 'w') as f:
                f.write('\n'.join(sorted(self.created)))
                f.write('\n')
                f.flush()
        except (TypeError, OSError) as ex:
            failfmt = '\nFailed to write {}:\n  {}'
            self.report(failfmt.format(Installer.installed_file, ex))
            return False
        # Copy installed_files.txt so it can be used in the dest dir.
        destfile = os.path.abspath(
            os.path.join(self.installdir, Installer.installed_file))
        localfile = os.path.abspath(Installer.installed_file)

        if destfile == localfile:
            # File already exists at the destination.
            # TODO: Check modification times, overwrite destfile if older?
            return True

        try:
            shutil.copy2(localfile, destfile)
        except OSError as ex:
            errfmt = '\n'.join((
                '\nUnable to copy {} to destination: {}',
                'Local file is available: {}',
                'Error: {}',
            ))
            errmsg = errfmt.format(
                Installer.installed_file,
                destfile,
                localfile,
                ex,
            )
            self.report(errmsg)
            return False
        # Success.
        return True


if __name__ == '__main__':
    mainret = main(docopt(USAGESTR, version=VERSIONSTR))
    sys.exit(mainret)
