#!/usr/bin/env python3
""" Glader - Core
    Functions and globals that are vital to other Glader modules.
    -Christopher Welborn 03-22-20
"""
import os
import sys


NAME = 'Glader'
__version__ = '0.2.5'
VERSIONSTR = '{} v. {}'.format(NAME, __version__)

# Set with -D,--debug command-line options.
DEBUG = ('-D' in sys.argv) or ('--debug' in sys.argv)

# Config file should always liver under /home/..
CONFIGDIR = os.path.expanduser('~/.config/glader')
CONFIGFILE = os.path.join(CONFIGDIR, 'glader.conf')

SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])


def debug(*args, **kwargs):
    """ Prints to stderr, if DEBUG is truthy. """
    if not DEBUG:
        return None
    kwargs['file'] = sys.stderr
    print(*args, **kwargs)


def ensure_config_dir():
    """ Ensure the config dir exists. Create it if needed. """
    if os.path.isdir(CONFIGDIR):
        debug(f'Config dir: {CONFIGDIR}')
        return None
    try:
        os.makedirs(CONFIGDIR)
        debug(f'Created directory: {CONFIGDIR}')
    except EnvironmentError as ex:
        print(
            f'\nUnable to create config dir: {CONFIGDIR}\n{ex}',
            file=sys.stderr,
        )
        sys.exit(1)


def import_fail(err):
    """ Fail with a friendlier message when imports fail. """
    msglines = (
        '\n{namever} requires some third-party libraries.',
        'Please install requirements using \'pip\' or your package manager.',
        'The import error was:',
        '    {err}\n'
    )
    print(
        '\n'.join(msglines).format(namever=VERSIONSTR, err=err),
        file=sys.stderr,
    )
    sys.exit(1)
