#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" glader.py
    ...Writes GTK boilerplate code based on a Glade file.
    -Christopher Welborn 09-14-2014
"""

import os
import sys
from glader_util import import_fail, GladeFile, VERSIONSTR
from glader_ui import gui_main

try:
    from docopt import docopt
except ImportError as eximp:
    import_fail(eximp)

SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

USAGESTR = """{versionstr}
    Usage:
        {script} -h | -v
        {script} [FILE] [OUTFILE] [-d] [-g]

    Options:
        FILE           : Glade file to parse.
        OUTFILE        : File name for output.
                         If - is given, output will be printed to stdout.
        -d,--dynamic   : Use dynamic object initialization method.
        -g,--gui       : Force use of a GUI, even when an output file is given.
                         You still have to use the 'Save' button to apply
                         changes.
        -h,--help      : Show this help message.
        -v,--version   : Show version.

""".format(script=SCRIPT, versionstr=VERSIONSTR)


def main(argd):
    """ Main entry point, expects doctopt arg dict as argd """
    filename = argd['FILE']
    if filename and (not os.path.exists(filename)):
        print('\nFile does not exist: {}'.format(filename))
        return 1

    outfile = argd['OUTFILE']
    # Automatic command line when outputfile is given, unless --gui is used.
    if outfile and not argd['--gui']:
        # Cmdline version.
        return do_cmdline(
            filename,
            outputfile=outfile,
            dynamic_init=argd['--dynamic'])

    # Full gui. Function exits the program when finished.
    if outfile == '-':
        # No stdout is used for gui mode.
        outfile = None
    do_gui(filename, outputfile=outfile, dynamic_init=argd['--dynamic'])


def confirm(question):
    """ Confirm an action with a yes/no question. """
    ans = input('{} (y/N): '.format(question)).strip().lower()
    return ans.startswith('y')


def do_cmdline(filename, outputfile=None, dynamic_init=False):
    """ Just run the cmdline version. """
    if outputfile and os.path.exists(outputfile):
        msg = '\nFile exists: {}\n\nOverwrite it?'.format(outputfile)
        if not confirm(msg):
            print('\nUser cancelled.\n')
            return 1

    fileinfo = get_gladeinfo(filename, dynamic_init)
    if not fileinfo:
        print('\nNo usable info was found for this file: {}'.format(filename))
        return 1

    content = fileinfo.get_content()
    if outputfile.startswith('-'):
        # User wants stdout.
        print(content)
    else:
        try:
            with open(outputfile, 'w')as f:
                f.write(content)
            print('File was generated: {}'.format(outputfile))
        except (PermissionError, EnvironmentError) as ex:
            print('\nError writing file: {}\n{}'.format(outputfile, ex))
            return 1
        try:
            fileinfo.make_executable(outputfile)
            print('Mode +rwx (774) was set to make it executable.')
        except (PermissionError, EnvironmentError) as experm:
            print('Unable to make it executable:\n  {}'.format(experm))

    return 0 if content else 1


def do_gui(filename=None, outputfile=None, dynamic_init=False):
    """ Run the full gui. """
    # This function will exit the program when finished.
    gui_main(
        filename=filename,
        outputfile=outputfile,
        dynamic_init=dynamic_init)


def get_gladeinfo(filename, dynamic_init=False):
    """ Retrieve widget/object info from a glade file. """
    try:
        gladeinfo = GladeFile(filename, dynamic_init=dynamic_init)
    except Exception as ex:
        print('\nError parsing glade file!: {}\n{}'.format(filename, ex))
        return None
    return gladeinfo


if __name__ == '__main__':
    mainret = main(docopt(USAGESTR, version=VERSIONSTR))
    sys.exit(mainret)
