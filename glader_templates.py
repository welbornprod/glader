#!/usr/bin/env python3
""" Glader - Templates
    Helpers for retrieving Glader template files/content.
    -Christopher Welborn 03-14-20
"""
import os.path
import sys
SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])
TEMPLATEDIR = os.path.join(SCRIPTDIR, 'templates')
# A dict of {name: full_path}, like: {'body': './templates/body.py'}
TEMPLATE_FILES = {
    os.path.splitext(s)[0]: os.path.join(TEMPLATEDIR, s)
    for s in os.listdir(TEMPLATEDIR)
    if s.endswith('.py')
}


def fatal_err(*args, **kwargs):
    """ Print a message to stderr and exit(1). """
    print_err(*args, **kwargs)
    sys.exit(1)


def get_template(name, indent=0):
    """ Retrieve template content by name ('body', 'cls', ...) """
    filepath = TEMPLATE_FILES.get(name, None)
    if filepath is None:
        print_err(f'\nUnknown template name: {name!r}')
        sys.exit(1)
    try:
        with open(filepath, 'r') as f:
            content = ''.join(parse_template(f, indent=indent))
    except FileNotFoundError:
        fatal_err(f'File was deleted before it was read!: {filepath}')
    except EnvironmentError as ex:
        fatal_err(f'Unable to read template file: {filepath}\n{ex}')
    return content.strip()


def parse_template(lines, indent=0):
    """ Parse an open file object, or an iterable of lines to make a "usable"
        templates.
        Yields usable lines.
    """
    spaces = ' ' * indent
    yielded = 0
    for line in lines:
        stripped = line.rstrip()
        if stripped.lower().endswith('# ignore'):
            # Ignore this line.
            continue
        if not (yielded or stripped):
            # Only blank lines so far (from ignoring lines).
            continue
        yield f'{spaces}{line}'
        yielded += 1


def print_err(*args, **kwargs):
    kwargs['file'] = kwargs.get('file', sys.stderr)
    print(*args, **kwargs)


if not os.path.exists(TEMPLATEDIR):
    fatal_err(f'\nMissing ./templates directory for Glader in: {SCRIPTDIR}')

# Ensure all template files are present.
for name, path in TEMPLATE_FILES.items():
    if not os.path.exists(path):
        fatal_err(f'Missing template file for {name!r}: {path}')
