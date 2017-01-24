#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" test_glader.py
    Unit tests for Glader

    -Christopher Welborn 01-24-2017
"""

import os
import sys
import unittest

GLADER_PATH = ''
GLADER_PY_FILE = 'glader.py'
TEST_GLADE_FILE = 'example.glade'
TEST_GLADE_FILE_EXISTS = False
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


class GladerTests(unittest.TestCase):

    def exec_code(self, code, filename=None):
        """ Use ProcessOutput to run python code, and return the ProcessOutput
            object.
        """
        exec(
            compile(code, filename or '<unknown>', 'exec', dont_inherit=True)
        )

    def exec_err_msg(self, exc, lbl='Code execution failed:'):
        return '\n'.join((
            lbl,
            '  Error: {exctype}',
            'Message: {exc}',
        )).format(exctype=type(exc).__name__, exc=exc)

    @unittest.skipUnless(TEST_GLADE_FILE_EXISTS, 'Missing test glade file.')
    def test_non_dynamic_code_compiles(self):
        """ Glader should generate valid python code in normal mode. """
        gf = GladeFile(TEST_GLADE_FILE, dynamic_init=False)
        try:
            self.exec_code(gf.get_content(), filename=TEST_GLADE_FILE)
        except Exception as ex:
            self.fail(self.exec_err_msg(ex, 'Non-dynamic code failed:'))

        try:
            self.exec_code(
                gf.get_content(lib_mode=True),
                filename=TEST_GLADE_FILE
            )
        except Exception as ex:
            self.fail(
                self.exec_err_msg(ex, 'Non-dynamic lib_mode code failed:')
            )

    @unittest.skipUnless(TEST_GLADE_FILE_EXISTS, 'Missing test glade file.')
    def test_dynamic_code_compiles(self):
        """ Glader should generate valid python code in dynamic mode. """
        gf = GladeFile(TEST_GLADE_FILE, dynamic_init=True)
        try:
            self.exec_code(gf.get_content(), filename=TEST_GLADE_FILE)
        except Exception as ex:
            self.fail(self.exec_err_msg(ex, 'Dynamic code failed:'))

        try:
            self.exec_code(
                gf.get_content(lib_mode=True),
                filename=TEST_GLADE_FILE
            )
        except Exception as ex:
            self.fail(
                self.exec_err_msg(ex, 'Dynamic lib_mode code failed:')
            )

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
                    filename='<valid code>'
                )
            except Exception as ex:
                self.fail(
                    self.exec_err_msg(
                        ex,
                        'exec_code failed on valid code: {}'.format(code)
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
                    filename='<invalid code>'
                )
            except excs:
                pass
            else:
                self.fail('exec_code did not fail on invalid code!: {}'.format(
                    code
                ))

if __name__ == '__main__':
    sys.exit(unittest.main(argv=sys.argv))
