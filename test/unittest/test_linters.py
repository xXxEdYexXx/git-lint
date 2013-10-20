# Copyright 2013 Sebastian Kreft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import functools
import os
import subprocess
import unittest

import mock

import gitlint.linters as linters


class LintersTest(unittest.TestCase):
    def test_filter_output(self):
        lines = ['a', 'b', 'c', 'ad']
        output = os.linesep.join(lines)
        self.assertEqual(output, linters.filter_output(output, '.'))
        self.assertEqual(os.linesep.join(['a', 'ad']), linters.filter_output(output, 'a'))
        self.assertEqual(os.linesep.join(['ad']), linters.filter_output(output, '.d'))
        self.assertEqual('', linters.filter_output(output, 'd'))
        self.assertEqual('', linters.filter_output(output, 'foo'))

    def test_lint_command_success(self):
        with mock.patch('subprocess.check_output') as check_output:
            check_output.return_value = os.linesep.join(['Line 1: 1', 'Line 5: 5', 'Line 7: 7', 'Line 9: 9'])
            command = functools.partial(linters.lint_command, 'linter', ['-f', '--compact'], '^Line (%(lines)s):')
            filename = 'foo.txt'
            self.assertEqual(os.linesep.join(['Line 5: 5', 'Line 7: 7']), command(filename, lines=[3, 5, 7]))
            self.assertEqual(os.linesep.join(['Line 1: 1', 'Line 5: 5', 'Line 7: 7', 'Line 9: 9']), command(filename, lines=None))
            expected_calls = [mock.call(['linter', '-f', '--compact', 'foo.txt'], stderr=subprocess.STDOUT), mock.call(['linter', '-f', '--compact', 'foo.txt'], stderr=subprocess.STDOUT)]
            self.assertEqual(expected_calls, check_output.call_args_list)

    def test_lint_command_error(self):
        output = os.linesep.join(['Line 1: 1', 'Line 5: 5', 'Line 7: 7', 'Line 9: 9'])
        with mock.patch('subprocess.check_output', side_effect=subprocess.CalledProcessError(1, 'linter', output)) as check_output:
            command = functools.partial(linters.lint_command, 'linter', ['-f', '--compact'], '^Line (%(lines)s):')
            filename = 'foo.txt'
            self.assertEqual(os.linesep.join(['Line 5: 5', ('Line 7: 7')]), command(filename, lines=[3, 5, 7]))
            self.assertEqual(os.linesep.join(['Line 1: 1', 'Line 5: 5', 'Line 7: 7', 'Line 9: 9']), command(filename, lines=None))
            expected_calls = [mock.call(['linter', '-f', '--compact', 'foo.txt'], stderr=subprocess.STDOUT), mock.call(['linter', '-f', '--compact', 'foo.txt'], stderr=subprocess.STDOUT)]
            self.assertEqual(expected_calls, check_output.call_args_list)

    def test_lint(self):
        linter1 = functools.partial(linters.lint_command, 'linter1', ['-f'], '^Line (%(lines)s):')
        linter2 = functools.partial(linters.lint_command, 'linter2', [], '^ line (%(lines)s):')
        config = {
            '.txt': [linter1, linter2]
        }
        outputs = [os.linesep.join(['Line 1: 1', 'Line 5: 5']),
                   os.linesep.join([' line 4: 4'])]
        with mock.patch('subprocess.check_output', side_effect=outputs) as check_output:
            filename = 'foo.txt'
            self.assertEqual(os.linesep.join(['Line 5: 5', ' line 4: 4']), linters.lint(filename, lines=[4, 5], config=config))
            expected_calls = [mock.call(['linter1', '-f', 'foo.txt'], stderr=subprocess.STDOUT), mock.call(['linter2', 'foo.txt'], stderr=subprocess.STDOUT)]
            self.assertEqual(expected_calls, check_output.call_args_list)

    def test_lint_one_empty_lint(self):
        linter1 = functools.partial(linters.lint_command, 'linter1', ['-f'], '^Line (%(lines)s):')
        linter2 = functools.partial(linters.lint_command, 'linter2', [], '^ line (%(lines)s):')
        config = {
            '.txt': [linter1, linter2]
        }
        outputs = ['',
                   os.linesep.join([' line 4: 4'])]
        with mock.patch('subprocess.check_output', side_effect=outputs) as check_output:
            filename = 'foo.txt'
            self.assertEqual(' line 4: 4', linters.lint(filename, lines=[4, 5], config=config))
            expected_calls = [mock.call(['linter1', '-f', 'foo.txt'], stderr=subprocess.STDOUT), mock.call(['linter2', 'foo.txt'], stderr=subprocess.STDOUT)]
            self.assertEqual(expected_calls, check_output.call_args_list)

    def test_lint_all_empty_lint(self):
        linter1 = functools.partial(linters.lint_command, 'linter1', ['-f'], '^Line (%(lines)s):')
        linter2 = functools.partial(linters.lint_command, 'linter2', [], '^ line (%(lines)s):')
        config = {
            '.txt': [linter1, linter2]
        }
        outputs = ['', '']
        with mock.patch('subprocess.check_output', side_effect=outputs) as check_output:
            filename = 'foo.txt'
            self.assertEqual('OK', linters.lint(filename, lines=[4, 5], config=config))
            expected_calls = [mock.call(['linter1', '-f', 'foo.txt'], stderr=subprocess.STDOUT), mock.call(['linter2', 'foo.txt'], stderr=subprocess.STDOUT)]
            self.assertEqual(expected_calls, check_output.call_args_list)

    def test_lint_extension_not_defined(self):
        config = {}
        output = linters.lint('foo.txt', lines=[4, 5], config=config)
        self.assertIn('.txt', output)
        self.assertTrue(output.startswith('SKIPPED'))