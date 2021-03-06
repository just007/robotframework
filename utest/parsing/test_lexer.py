from io import StringIO
import os
import unittest
import tempfile

from robot.utils import PY3
from robot.utils.asserts import assert_equal

from robot.parsing import get_tokens, get_resource_tokens, Token


T = Token


def assert_tokens(source, expected, get_tokens=get_tokens, data_only=False):
    tokens = list(get_tokens(source, data_only))
    assert_equal(len(tokens), len(expected),
                 'Expected %d tokens:\n%s\n\nGot %d tokens:\n%s'
                 % (len(expected), expected, len(tokens), tokens),
                 values=False)
    for act, exp in zip(tokens, expected):
        exp = Token(*exp)
        assert_equal(act.type, exp.type)
        assert_equal(act.value, exp.value, formatter=repr)
        assert_equal(act.lineno, exp.lineno)
        assert_equal(act.columnno, exp.columnno)


class TestName(unittest.TestCase):

    def test_name_on_own_row(self):
        self._verify('My Name',
                     [(T.NAME, 'My Name', 2, 1), (T.EOL, '', 2, 8), (T.EOS, '', 2, 8)])
        self._verify('My Name    ',
                     [(T.NAME, 'My Name', 2, 1), (T.EOL, '    ', 2, 8), (T.EOS, '', 2, 12)])
        self._verify('My Name\n    Keyword',
                     [(T.NAME, 'My Name', 2, 1), (T.EOL, '\n', 2, 8), (T.EOS, '', 2, 9),
                      (T.SEPARATOR, '    ', 3, 1), (T.KEYWORD, 'Keyword', 3, 5), (T.EOL, '', 3, 12), (T.EOS, '', 3, 12)])
        self._verify('My Name  \n    Keyword',
                     [(T.NAME, 'My Name', 2, 1), (T.EOL, '  \n', 2, 8), (T.EOS, '', 2, 11),
                      (T.SEPARATOR, '    ', 3, 1), (T.KEYWORD, 'Keyword', 3, 5), (T.EOL, '', 3, 12), (T.EOS, '', 3, 12)])

    def test_name_and_keyword_on_same_row(self):
        self._verify('Name    Keyword',
                     [(T.NAME, 'Name', 2, 1), (T.EOS, '', 2, 5), (T.SEPARATOR, '    ', 2, 5),
                      (T.KEYWORD, 'Keyword', 2, 9), (T.EOL, '', 2, 16), (T.EOS, '', 2, 16)])
        self._verify('N  K  A',
                     [(T.NAME, 'N', 2, 1), (T.EOS, '', 2, 2), (T.SEPARATOR, '  ', 2, 2),
                      (T.KEYWORD, 'K', 2, 4), (T.SEPARATOR, '  ', 2, 5),
                      (T.ARGUMENT, 'A', 2, 7), (T.EOL, '', 2, 8), (T.EOS, '', 2, 8)])
        self._verify('N  ${v}=  K',
                     [(T.NAME, 'N', 2, 1), (T.EOS, '', 2, 2), (T.SEPARATOR, '  ', 2, 2),
                      (T.ASSIGN, '${v}=', 2, 4), (T.SEPARATOR, '  ', 2, 9),
                      (T.KEYWORD, 'K', 2, 11), (T.EOL, '', 2, 12), (T.EOS, '', 2, 12)])

    def test_name_and_setting_on_same_row(self):
        self._verify('Name    [Documentation]    The doc.',
                     [(T.NAME, 'Name', 2, 1), (T.EOS, '', 2, 5), (T.SEPARATOR, '    ', 2, 5),
                      (T.DOCUMENTATION, '[Documentation]', 2, 9), (T.SEPARATOR, '    ', 2, 24),
                      (T.ARGUMENT, 'The doc.', 2, 28), (T.EOL, '', 2, 36), (T.EOS, '', 2, 36)])

    def _verify(self, data, tokens):
        assert_tokens('*** Test Cases ***\n' + data,
                      [(T.TESTCASE_HEADER, '*** Test Cases ***', 1, 1),
                       (T.EOL, '\n', 1, 19),
                       (T.EOS, '', 1, 20)] + tokens)
        assert_tokens('*** Keywords ***\n' + data,
                      [(T.KEYWORD_HEADER, '*** Keywords ***', 1, 1),
                       (T.EOL, '\n', 1, 17),
                       (T.EOS, '', 1, 18)] + tokens,
                      get_tokens=get_resource_tokens)


class TestNameWithPipes(unittest.TestCase):

    def test_name_on_own_row(self):
        self._verify('| My Name',
                     [(T.SEPARATOR, '| ', 2, 1), (T.NAME, 'My Name', 2, 3), (T.EOL, '', 2, 10), (T.EOS, '', 2, 10)])
        self._verify('| My Name |',
                     [(T.SEPARATOR, '| ', 2, 1), (T.NAME, 'My Name', 2, 3), (T.SEPARATOR, ' |', 2, 10), (T.EOL, '', 2, 12), (T.EOS, '', 2, 12)])
        self._verify('| My Name | ',
                     [(T.SEPARATOR, '| ', 2, 1), (T.NAME, 'My Name', 2, 3), (T.SEPARATOR, ' |', 2, 10), (T.EOL, ' ', 2, 12), (T.EOS, '', 2, 13)])

    def test_name_and_keyword_on_same_row(self):
        self._verify('| Name | Keyword',
                     [(T.SEPARATOR, '| ', 2, 1), (T.NAME, 'Name', 2, 3), (T.EOS, '', 2, 7),
                      (T.SEPARATOR, ' | ', 2, 7), (T.KEYWORD, 'Keyword', 2, 10), (T.EOL, '', 2, 17), (T.EOS, '', 2, 17)])
        self._verify('| N | K | A |\n',
                     [(T.SEPARATOR, '| ', 2, 1), (T.NAME, 'N', 2, 3), (T.EOS, '', 2, 4),
                      (T.SEPARATOR, ' | ', 2, 4), (T.KEYWORD, 'K', 2, 7), (T.SEPARATOR, ' | ', 2, 8),
                      (T.ARGUMENT, 'A', 2, 11), (T.SEPARATOR, ' |', 2, 12), (T.EOL, '\n', 2, 14), (T.EOS, '', 2, 15)])
        self._verify('|    N  |  ${v} =    |    K    ',
                     [(T.SEPARATOR, '|    ', 2, 1), (T.NAME, 'N', 2, 6), (T.EOS, '', 2, 7),
                      (T.SEPARATOR, '  |  ', 2, 7), (T.ASSIGN, '${v} =', 2, 12), (T.SEPARATOR, '    |    ', 2, 18),
                      (T.KEYWORD, 'K', 2, 27), (T.EOL, '    ', 2, 28), (T.EOS, '', 2, 32)])

    def test_name_and_setting_on_same_row(self):
        self._verify('| Name | [Documentation] | The doc.',
                     [(T.SEPARATOR, '| ', 2, 1), (T.NAME, 'Name', 2, 3), (T.EOS, '', 2, 7), (T.SEPARATOR, ' | ', 2, 7),
                      (T.DOCUMENTATION, '[Documentation]', 2, 10), (T.SEPARATOR, ' | ', 2, 25),
                      (T.ARGUMENT, 'The doc.', 2, 28), (T.EOL, '', 2, 36), (T.EOS, '', 2, 36)])

    def _verify(self, data, tokens):
        assert_tokens('*** Test Cases ***\n' + data,
                      [(T.TESTCASE_HEADER, '*** Test Cases ***', 1, 1),
                       (T.EOL, '\n', 1, 19),
                       (T.EOS, '', 1, 20)] + tokens)
        assert_tokens('*** Keywords ***\n' + data,
                      [(T.KEYWORD_HEADER, '*** Keywords ***', 1, 1),
                       (T.EOL, '\n', 1, 17),
                       (T.EOS, '', 1, 18)] + tokens,
                      get_tokens=get_resource_tokens)


class TestGetTokensSourceFormats(unittest.TestCase):
    path = os.path.join(os.getenv('TEMPDIR') or tempfile.gettempdir(),
                        'test_lexer.robot')
    data = u'''\
*** Settings ***
Library         Easter

*** Test Cases ***
Example
    None shall pass    ${NONE}
'''
    tokens = [
        (T.SETTING_HEADER, '*** Settings ***', 1, 1),
        (T.EOL, '\n', 1, 17),
        (T.EOS, '', 1, 18),
        (T.LIBRARY, 'Library', 2, 1),
        (T.SEPARATOR, '         ', 2, 8),
        (T.ARGUMENT, 'Easter', 2, 17),
        (T.EOL, '\n', 2, 23),
        (T.EOS, '', 2, 24),
        (T.EOL, '\n', 3, 1),
        (T.EOS, '', 3, 2),
        (T.TESTCASE_HEADER, '*** Test Cases ***', 4, 1),
        (T.EOL, '\n', 4, 19),
        (T.EOS, '', 4, 20),
        (T.NAME, 'Example', 5, 1),
        (T.EOL, '\n', 5, 8),
        (T.EOS, '', 5, 9),
        (T.SEPARATOR, '    ', 6, 1),
        (T.KEYWORD, 'None shall pass', 6, 5),
        (T.SEPARATOR, '    ', 6, 20),
        (T.ARGUMENT, '${NONE}', 6, 24),
        (T.EOL, '\n', 6, 31),
        (T.EOS, '', 6, 32)
    ]
    data_tokens = [
        (T.SETTING_HEADER, '*** Settings ***', 1, 1),
        (T.EOS, '', 1, 17),
        (T.LIBRARY, 'Library', 2, 1),
        (T.ARGUMENT, 'Easter', 2, 17),
        (T.EOS, '', 2, 23),
        (T.TESTCASE_HEADER, '*** Test Cases ***', 4, 1),
        (T.EOS, '', 4, 19),
        (T.NAME, 'Example', 5, 1),
        (T.EOS, '', 5, 8),
        (T.KEYWORD, 'None shall pass', 6, 5),
        (T.ARGUMENT, '${NONE}', 6, 24),
        (T.EOS, '', 6, 31)
    ]

    @classmethod
    def setUpClass(cls):
        with open(cls.path, 'w') as f:
            f.write(cls.data)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.path)

    def test_string_path(self):
        self._verify(self.path)
        self._verify(self.path, data_only=True)

    if PY3:

        def test_pathlib_path(self):
            from pathlib import Path
            self._verify(Path(self.path))
            self._verify(Path(self.path), data_only=True)

    def test_open_file(self):
        with open(self.path) as f:
            self._verify(f)
        with open(self.path) as f:
            self._verify(f, data_only=True)

    def test_string_io(self):
        self._verify(StringIO(self.data))
        self._verify(StringIO(self.data), data_only=True)

    def test_string(self):
        self._verify(self.data)
        self._verify(self.data, data_only=True)

    def _verify(self, source, data_only=False):
        expected = self.data_tokens if data_only else self.tokens
        assert_tokens(source, expected, data_only=data_only)


class TestGetResourceTokensSourceFormats(TestGetTokensSourceFormats):
    data = u'''\
*** Variable ***
${VAR}    Value

*** KEYWORD ***
NOOP    No Operation
'''
    tokens = [
        (T.VARIABLE_HEADER, '*** Variable ***', 1, 1),
        (T.EOL, '\n', 1, 17),
        (T.EOS, '', 1, 18),
        (T.VARIABLE, '${VAR}', 2, 1),
        (T.SEPARATOR, '    ', 2, 7),
        (T.ARGUMENT, 'Value', 2, 11),
        (T.EOL, '\n', 2, 16),
        (T.EOS, '', 2, 17),
        (T.EOL, '\n', 3, 1),
        (T.EOS, '', 3, 2),
        (T.KEYWORD_HEADER, '*** KEYWORD ***', 4, 1),
        (T.EOL, '\n', 4, 16),
        (T.EOS, '', 4, 17),
        (T.NAME, 'NOOP', 5, 1),
        (T.EOS, '', 5, 5),
        (T.SEPARATOR, '    ', 5, 5),
        (T.KEYWORD, 'No Operation', 5, 9),
        (T.EOL, '\n', 5, 21),
        (T.EOS, '', 5, 22)
    ]
    data_tokens = [
        (T.VARIABLE_HEADER, '*** Variable ***', 1, 1),
        (T.EOS, '', 1, 17),
        (T.VARIABLE, '${VAR}', 2, 1),
        (T.ARGUMENT, 'Value', 2, 11),
        (T.EOS, '', 2, 16),
        (T.KEYWORD_HEADER, '*** KEYWORD ***', 4, 1),
        (T.EOS, '', 4, 16),
        (T.NAME, 'NOOP', 5, 1),
        (T.EOS, '', 5, 5),
        (T.KEYWORD, 'No Operation', 5, 9),
        (T.EOS, '', 5, 21)
    ]

    def _verify(self, source, data_only=False):
        expected = self.data_tokens if data_only else self.tokens
        assert_tokens(source, expected, get_tokens=get_resource_tokens,
                      data_only=data_only)


if __name__ == '__main__':
    unittest.main()
