#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" glader.py
    ...Writes GTK boilerplate code based on a Glade file.
    -Christopher Welborn 09-14-2014
"""

import os
import sys
import traceback
from glader_util import import_fail, GladeFile, VERSIONSTR
from glader_ui import gui_main

try:
    from docopt import docopt
except ImportError as eximp:
    import_fail(eximp)

try:
    from pygments import highlight as pyg_highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import Terminal256Formatter
except ImportError:
    highlight_warn = 'You must `pip install pygments`.'
    has_pygments = False

    def highlight_code(code):
        return code
else:
    # For the --highlight option, when pygments is available.
    pyg_lexer = get_lexer_by_name('python3')
    pyg_formatter = Terminal256Formatter(bg='dark', style='monokai')
    highlight_warn = ''
    has_pygments = True

    def highlight_code(code):
        return pyg_highlight(code, pyg_lexer, pyg_formatter).rstrip()


SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

USAGESTR = f"""{VERSIONSTR}
    Usage:
        {SCRIPT} -h | -v
        {SCRIPT} [FILE] [OUTFILE] [-D] [-d] [-g] [-l]
        {SCRIPT} FILE OUTFILE -o [-D] [-d] [-l]
        {SCRIPT} FILE [-H | -L] [-D] [-d] [-l]

    Options:
        FILE            : Glade file to parse.
        OUTFILE         : File name for output.
                          If - is given, output will be printed to stdout.
        -D,--debug      : Show more info on errors.
        -d,--dynamic    : Use dynamic object initialization method.
        -g,--gui        : Force use of a GUI, even when an output file is given.
                          You still have to use the 'Save' button to apply
                          changes.
        -H,--highlight  : Syntax highlight the generated code and print to
                          stdout. {highlight_warn}
        -h,--help       : Show this help message.
        -L,--layout     : Show Glader layout for the file.
        -l,--lib        : Generate a usable Gtk.Window class only, not a
                          script.
        -o,--overwrite  : Overwrite existing files without confirmation.
        -v,--version    : Show version.

"""

DEBUG = ('-D' in sys.argv) or ('--debug' in sys.argv)


def main(argd):
    """ Main entry point, expects doctopt arg dict as argd """
    filepath = argd['FILE']
    if filepath and (not os.path.exists(filepath)):
        print('\nFile does not exist: {}'.format(filepath))
        return 1
    cmdline_cmds = argd['--layout'] or argd['--highlight']
    outfile = '-' if cmdline_cmds else argd['OUTFILE']
    # Automatic command line when outputfile is given, unless --gui is used.
    if (cmdline_cmds or outfile) and not argd['--gui']:
        # Cmdline version.
        return do_cmdline(
            filepath,
            outputfile=outfile,
            dynamic_init=argd['--dynamic'],
            lib_mode=argd['--lib'],
            overwrite=argd['--overwrite'],
            highlight=argd['--highlight'],
            layout=argd['--layout'],
        )

    # Full gui. Function exits the program when finished.
    if outfile == '-':
        # No stdout is used for gui mode.
        outfile = None
    do_gui(
        filepath,
        outputfile=outfile,
        dynamic_init=argd['--dynamic'],
        lib_mode=argd['--lib'],
    )


def confirm(question):
    """ Confirm an action with a yes/no question. """
    ans = input('{} (y/N): '.format(question)).strip().lower()
    return ans.startswith('y')


def do_cmdline(
        filepath, outputfile=None, dynamic_init=False, lib_mode=False,
        overwrite=False, highlight=False, layout=False):
    """ Just run the cmdline version. """
    if not filepath:
        print_err('\nNo filepath provided!')
        return 1
    if outputfile and os.path.exists(outputfile) and (not overwrite):
        msg = '\nFile exists: {}\n\nOverwrite it?'.format(outputfile)
        if not confirm(msg):
            print('\nUser cancelled.\n')
            return 1

    fileinfo = get_gladeinfo(filepath, dynamic_init)
    if not fileinfo:
        print('\nNo usable info was found for this file: {}'.format(filepath))
        return 1

    if layout:
        print(repr(fileinfo))
        return 0

    content = fileinfo.get_content(lib_mode=lib_mode)
    if outputfile.startswith('-'):
        # User wants stdout.
        print(highlight_code(content) if highlight else content)
    else:
        try:
            with open(outputfile, 'w')as f:
                f.write(content)
            print('File was generated: {}'.format(outputfile))
        except (PermissionError, EnvironmentError) as ex:
            print_err('\nError writing file: {}\n{}'.format(outputfile, ex))
            return 1
        try:
            fileinfo.make_executable(outputfile)
            print('Mode +rwx (774) was set to make it executable.')
        except (PermissionError, EnvironmentError) as experm:
            print_err('Unable to make it executable:\n  {}'.format(experm))

    reqs = fileinfo.extra_requires_msg()
    if reqs:
        print_err(f'\n{reqs}')
    return 0 if content else 1


def do_gui(
        filepath=None, outputfile=None, dynamic_init=False, lib_mode=False):
    """ Run the full gui. """
    # This function will exit the program when finished.
    gui_main(
        filepath=filepath,
        outputfile=outputfile,
        dynamic_init=dynamic_init,
        lib_mode=lib_mode,
    )


def get_gladeinfo(filepath, dynamic_init=False):
    """ Retrieve widget/object info from a glade file. """
    try:
        gladeinfo = GladeFile(
            filepath,
            dynamic_init=dynamic_init,
        )
    except Exception as ex:
        print('\nError parsing glade file!: {}\n{}'.format(filepath, ex))
        if DEBUG:
            print_exc()
        return None
    return gladeinfo


def print_err(*args, **kwargs):
    kwargs['file'] = kwargs.get('file', sys.stderr)
    print(*args, **kwargs)


def print_exc():
    etype, evalue, etraceback = sys.exc_info()

    lines = traceback.format_exception(etype, evalue, etraceback)
    print(''.join(lines), file=sys.stderr)


if __name__ == '__main__':
    mainret = main(docopt(USAGESTR, version=VERSIONSTR))
    sys.exit(mainret)
