#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" test_glader.py
    Unit tests for Glader

    -Christopher Welborn 01-24-2017
"""

import os
import sys
import unittest

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import Terminal256Formatter

pyg_lexer = get_lexer_by_name('python3')
pyg_formatter = Terminal256Formatter(bg='dark', style='monokai')


GLADER_PATH = ''
GLADER_PY_FILE = 'glader.py'
TEST_GLADE_FILE = 'example.glade'
TEST_GLADE_FILE_EXISTS = False
SHOW_CODE = os.environ.get('TEST_GLADER_CODE', None) in ('1', 'yes', 'true')
for try_path in ('.', '..', ):
    try_testfilepath = os.path.join(try_path, TEST_GLADE_FILE)
    if os.path.exists(try_testfilepath):
        TEST_GLADE_FILE = try_testfilepath
        TEST_GLADE_FILE_EXISTS = True
    try_gladerpy = os.path.join(try_path, GLADER_PY_FILE)
    if os.path.exists(try_gladerpy):
        GLADER_PY_FILE = try_gladerpy
        GLADER_PATH = os.path.split(GLADER_PY_FILE)[0]

if GLADER_PATH not in sys.path:
    sys.path.insert(0, GLADER_PATH)
try:
    from glader_util import GladeFile
except ImportError as ex:
    print('Cannot find glader_util.py!\n{}'.format(ex), file=sys.stderr)
    sys.exit(1)


def highlight_code(code):
    """ Highlight some python code for the terminal. """
    return highlight(code, pyg_lexer, pyg_formatter).strip()


class GladerTests(unittest.TestCase):

    def exec_code(self, code, filepath=None):
        """ Use ProcessOutput to run python code, and return the ProcessOutput
            object.
        """
        code = code.replace('return Gtk.main()', 'return 0')
        try:
            exec(
                compile(
                    code,
                    filepath or '<unknown>',
                    'exec',
                    dont_inherit=True,
                ),
                globals(),
            )
        except SystemExit:
            # The body template calls sys.exit(), this is okay.
            pass

    def exec_err_msg(self, exc, lbl='Code execution failed:', code=None):
        lines = [
            lbl,
            f'  Error: {type(exc).__name__}',
            f'Message: {exc}',
        ]
        if code:
            lines.extend(['Code:', highlight_code(code)])
        return '\n'.join(lines)

    def test_exec_code(self):
        """ Make sure tests.exec_code is working correctly. """
        # Testing a test, to keep my sanity.
        valid_code = (
            'import sys; sys.version',
            'x = [1, 2, 3]; x[0]',
            '[x * 2 for x in range(3)]',
        )
        for code in valid_code:
            try:
                self.exec_code(
                    code,
                    filepath='<valid code>'
                )
            except Exception as ex:
                self.fail(
                    self.exec_err_msg(
                        ex,
                        'exec_code failed on valid code: {}'.format(code),
                        code=code if SHOW_CODE else None,
                    )
                )
        invalid_code = (
            ('from blabbery import connery', (ImportError, )),
            ('x = blah', (NameError, )),
            ('x = [1, 2, 3]; x[5]', (IndexError, )),
        )
        for code, excs in invalid_code:
            try:
                self.exec_code(
                    code,
                    filepath='<invalid code>'
                )
            except excs:
                pass
            else:
                self.fail('exec_code did not fail on invalid code!: {}'.format(
                    code
                ))

    @unittest.skipUnless(TEST_GLADE_FILE_EXISTS, 'Missing test glade file.')
    def test_non_dynamic_code_compiles(self):
        """ Glader should generate valid python code in normal mode. """
        gf = GladeFile(TEST_GLADE_FILE, dynamic_init=False)
        code = gf.get_content()
        try:
            self.exec_code(
                code,
                filepath=TEST_GLADE_FILE,
            )
        except Exception as ex:
            self.fail(
                self.exec_err_msg(
                    ex,
                    'Non-dynamic code failed:',
                    code=code if SHOW_CODE else None,
                )
            )

        code = gf.get_content(lib_mode=True)
        try:
            self.exec_code(
                code,
                filepath=TEST_GLADE_FILE,
            )
        except Exception as ex:
            self.fail(
                self.exec_err_msg(
                    ex,
                    'Non-dynamic lib_mode code failed:',
                    code=code if SHOW_CODE else None,
                )
            )

    @unittest.skipUnless(TEST_GLADE_FILE_EXISTS, 'Missing test glade file.')
    def test_dynamic_code_compiles(self):
        """ Glader should generate valid python code in dynamic mode. """
        gf = GladeFile(TEST_GLADE_FILE, dynamic_init=True)
        code = gf.get_content()
        try:
            self.exec_code(code, filepath=TEST_GLADE_FILE)
        except Exception as ex:
            self.fail(
                self.exec_err_msg(
                    ex,
                    'Dynamic code failed:',
                    code=code if SHOW_CODE else None,
                )
            )

        code = gf.get_content(lib_mode=True)
        try:
            self.exec_code(
                code,
                filepath=TEST_GLADE_FILE
            )
        except Exception as ex:
            self.fail(
                self.exec_err_msg(
                    ex,
                    'Dynamic lib_mode code failed:',
                    code=code if SHOW_CODE else None,
                )
            )


if __name__ == '__main__':
    sys.exit(unittest.main(argv=sys.argv))
