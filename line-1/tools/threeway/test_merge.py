"""Run from the repository root: python -B line-1/tools/threeway/test_merge.py."""

import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

from merge import MAX_BYTES, MAX_LINES, merge, read_text


class MergeTests(unittest.TestCase):
    def clean(self, base, ours, theirs, expected):
        result = merge(base, ours, theirs)
        self.assertTrue(result['clean'], result)
        self.assertEqual(result['merged'], expected)
        self.assertEqual(result['conflicts'], [])

    def test_independent_changes(self):
        self.clean('a\nb\nc\n', 'A\nb\nc\n', 'a\nb\nC\n', 'A\nb\nC\n')

    def test_adjacent_replacements(self):
        self.clean('a\nb\n', 'A\nb\n', 'a\nB\n', 'A\nB\n')

    def test_same_change_is_not_duplicated(self):
        self.clean('a\n', 'x\na\n', 'x\na\n', 'x\na\n')

    def test_empty_base(self):
        self.clean('', 'new', '', 'new')

    def test_both_empty(self):
        self.clean('old', '', '', '')

    def test_different_insertions_conflict(self):
        result = merge('a\n', 'x\na\n', 'y\na\n')
        self.assertFalse(result['clean'])
        self.assertEqual(result['conflicts'], [dict(base_start=0, base_end=0,
                                                 base='', ours='x\n', theirs='y\n')])
        self.assertTrue(result['merged'].endswith('>>>>>>> THEIRS\na\n'))

    def test_independent_insertions(self):
        self.clean('a\nb\n', 'x\na\nb\n', 'a\nb\ny\n', 'x\na\nb\ny\n')

    def test_deletion_and_independent_change(self):
        self.clean('a\nb\nc\n', 'b\nc\n', 'a\nb\nC\n', 'b\nC\n')

    def test_delete_modify_conflict(self):
        result = merge('a\nb\nc\n', 'a\nc\n', 'a\nB\nc\n')
        self.assertFalse(result['clean'])
        self.assertEqual(result['conflicts'][0]['base'], 'b\n')
        self.assertEqual(result['conflicts'][0]['ours'], '')
        self.assertEqual(result['conflicts'][0]['theirs'], 'B\n')

    def test_overlapping_multi_line_changes(self):
        result = merge('a\nb\nc\nd\n', 'X\nc\nd\n', 'a\nY\nd\n')
        self.assertFalse(result['clean'])
        self.assertEqual(result['conflicts'][0], dict(base_start=0, base_end=3,
                        base='a\nb\nc\n', ours='X\nc\n', theirs='a\nY\n'))
        self.assertTrue(result['merged'].endswith('d\n'))

    def test_two_separate_conflicts(self):
        result = merge('a\nb\nc\n', 'X\nb\nY\n', 'P\nb\nQ\n')
        self.assertEqual(len(result['conflicts']), 2)
        self.assertIn('>>>>>>> THEIRS\nb\n<<<<<<< OURS', result['merged'])

    def test_boundary_insertion_is_conservative(self):
        result = merge('a\nb\n', 'A\nb\n', 'x\na\nb\n')
        self.assertFalse(result['clean'])
        self.assertEqual(result['conflicts'][0]['theirs'], 'x\na\n')

    def test_insertion_after_replacement(self):
        self.clean('a\nb\n', 'A\nb\n', 'a\nx\nb\n', 'A\nx\nb\n')

    def test_no_newline_clean(self):
        self.clean('old', 'new', 'old', 'new')

    def test_unterminated_conflict_retains_exact_json(self):
        result = merge('old', 'ours', 'theirs')
        self.assertEqual(result['conflicts'][0]['base'], 'old')
        self.assertEqual(result['conflicts'][0]['ours'], 'ours')
        self.assertIn('ours\n||||||| BASE\nold\n=======\ntheirs\n', result['merged'])

    def test_crlf_preserved(self):
        self.clean('a\r\nb\r\n', 'A\r\nb\r\n', 'a\r\nB\r\n', 'A\r\nB\r\n')

    def test_unicode(self):
        self.clean('stone\n', 'café 🐸\n', 'stone\n', 'café 🐸\n')

    def test_reject_nul(self):
        with self.assertRaises(ValueError):
            merge('', '\x00', '')

    def test_reject_oversized(self):
        with self.assertRaises(ValueError):
            merge('', 'x' * (MAX_BYTES + 1), '')
        with self.assertRaises(ValueError):
            merge('', '\n' * (MAX_LINES + 1), '')

    def test_reject_escape_without_reading(self):
        # This path is the workspace's parent directory; no external file is opened.
        with self.assertRaisesRegex(ValueError, 'inside'):
            read_text(Path.cwd().parent)

    def test_seeded_identity_properties(self):
        rng = random.Random(737)
        for _ in range(150):
            base = ''.join(rng.choice(['a\n', 'b\n', 'c\n', '🐸\n'])
                           for _ in range(rng.randrange(20)))
            changed = ''.join(rng.choice(['a\n', 'b\n', 'X\n', 'Y'])
                              for _ in range(rng.randrange(20)))
            self.clean(base, changed, base, changed)
            self.clean(base, base, changed, changed)
            self.clean(base, changed, changed, changed)

    def test_seeded_independent_edits(self):
        rng = random.Random(21)
        base = [f'line {i}\n' for i in range(40)]
        for _ in range(100):
            i, j = rng.sample(range(len(base)), 2)
            ours, theirs, expected = base[:], base[:], base[:]
            ours[i] = expected[i] = 'ours\n'
            theirs[j] = expected[j] = 'theirs\n'
            self.clean(''.join(base), ''.join(ours), ''.join(theirs), ''.join(expected))

    def test_demo_cli(self):
        script = str(Path(__file__).with_name('merge.py'))
        result = subprocess.run([sys.executable, '-B', script, '--demo', '--format', 'json'],
                                capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertIn('verified-source.txt', parsed['merged'])
        self.assertIn('required before publishing', parsed['merged'])


if __name__ == '__main__':
    unittest.main()
