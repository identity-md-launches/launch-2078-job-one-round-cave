"""Behavioral tests, including an independent exhaustive satisfiability oracle."""
import copy
import itertools
import json
from pathlib import Path
import random
import tempfile
import unittest

from resolve import Invalid, accepts, load, solve, validate


def catalog(packages, roots=None):
    return {'packages': packages, 'roots': roots or {'app': '*'}}


def brute(data):
    """Independent oracle for the random suite's exact == and * grammar."""
    packages, roots = data['packages'], data['roots']
    names = sorted(packages)
    def satisfies(v, spec):
        return spec == '*' or v == spec[2:]
    for values in itertools.product(*[[None] + list(packages[p]) for p in names]):
        selected = {p: v for p, v in zip(names, values) if v is not None}
        if any(p not in selected or not satisfies(selected[p], s) for p, s in roots.items()):
            continue
        if all(dep in selected and satisfies(selected[dep], spec)
               for p, v in selected.items() for dep, spec in packages[p][v].items()):
            return True
    return False


class ResolverTests(unittest.TestCase):
    def test_real_demo(self):
        data = load(Path(__file__).parent / 'examples/requests.json')
        result = solve(data)
        self.assertEqual(result['status'], 'resolved')
        self.assertEqual(result['selected']['requests'], '2.32.5')
        self.assertEqual(result['selected']['urllib3'], '1.26.20')
        self.assertEqual(len(result['edges']), 4)

    def test_backtrack_and_remove_abandoned_dependencies(self):
        data = catalog({'app': {'2': {'shared': '==2', 'missing': '*'},
                                '1': {'shared': '==1'}},
                        'shared': {'1': {}, '2': {}}})
        result = solve(data)
        self.assertEqual(result['selected'], {'app': '1', 'shared': '1'})

    def test_diamond_conflict_is_explained(self):
        data = catalog({'app': {'1': {'a': '*', 'b': '*'}},
                        'a': {'1': {'common': '==1'}},
                        'b': {'1': {'common': '==2'}},
                        'common': {'1': {}, '2': {}}})
        result = solve(data)
        self.assertEqual(result['status'], 'unsatisfiable')
        self.assertIn(result['conflict']['package'], ('common', 'b'))
        self.assertTrue(result['conflict']['requirements'])

    def test_satisfiable_cycle(self):
        data = catalog({'app': {'1': {'b': '==2'}}, 'b': {'2': {'app': '==1'}}})
        self.assertEqual(solve(data)['selected'], {'app': '1', 'b': '2'})

    def test_unsatisfiable_cycle(self):
        data = catalog({'app': {'1': {'b': '*'}}, 'b': {'2': {'app': '==2'}}})
        self.assertEqual(solve(data)['status'], 'unsatisfiable')

    def test_missing_package(self):
        result = solve(catalog({}))
        self.assertEqual(result['status'], 'unsatisfiable')
        self.assertEqual(result['conflict']['package'], 'app')
        self.assertEqual(result['conflict']['requirements'][0]['source'], 'root')

    def test_budget_is_inconclusive_never_unsatisfiable(self):
        data = catalog({'app': {'1': {}}})
        self.assertEqual(solve(data, 1)['status'], 'inconclusive')
        self.assertEqual(solve(data, 2)['status'], 'resolved')

    def test_depth_is_inconclusive(self):
        packages = {f'p{i}': {'1': {f'p{i+1}': '*'}} for i in range(202)}
        packages['p202'] = {'1': {}}
        self.assertEqual(solve(catalog(packages, {'p0': '*'}))['status'], 'inconclusive')

    def test_numeric_order_and_bounds(self):
        self.assertTrue(accepts('2.10', '>2.9,<3,!=2.11'))
        self.assertTrue(accepts('2.0.0', '==2,>=2.0,<=2.0.0.0'))
        self.assertFalse(accepts('2', '<2'))
        self.assertFalse(accepts('2.1', '<=2'))
        self.assertEqual(solve(catalog({'app': {'2.9': {}, '2.10': {}}}))['selected']['app'], '2.10')

    def test_reject_unsupported_versions_and_constraints(self):
        for v in ['1.0rc1', '01.0', '1.2.3.4.5', True, '1e2']:
            with self.assertRaises(Invalid):
                accepts(v, '*')
        for spec in ['^1', '~1', '1', '', '>=1 || <2', '==1.*', '>=1; python_version>3']:
            with self.assertRaises(Invalid):
                accepts('1', spec)

    def test_reject_duplicate_aliases_and_equivalent_releases(self):
        for packages in [{'A_B': {'1': {}}, 'a-b': {'1': {}}},
                         {'app': {'1': {}, '1.0': {}}}]:
            with self.assertRaises(Invalid):
                validate(catalog(packages))
        with self.assertRaises(Invalid):
            validate(catalog({'app': {'1': {'A_B': '*', 'a-b': '*'}}}))

    def test_normalize_names(self):
        data = catalog({'APP': {'1': {'Shared.Lib': '==2'}}, 'shared_lib': {'2': {}}})
        self.assertEqual(solve(data)['selected'], {'app': '1', 'shared-lib': '2'})

    def test_invalid_structures_and_limits(self):
        for data in [None, [], {}, {'packages': {}, 'roots': {}},
                     {'packages': [], 'roots': {'app': '*'}},
                     catalog({'app': []}), catalog({'app': {'1': []}}),
                     catalog({'app': {'1': {}}}, {'app': True})]:
            with self.assertRaises(Invalid):
                validate(data)
        for budget in [0, -1, True, 1000001]:
            with self.assertRaises(Invalid):
                solve(catalog({}), budget)

    def test_duplicate_json_and_read_size(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            path = Path(tmp) / 'catalog.json'
            path.write_text('{"packages":{},"packages":{},"roots":{"app":"*"}}')
            with self.assertRaises(Invalid):
                load(path)
            path.write_bytes(b' ' * 1000001)
            with self.assertRaises(Invalid):
                load(path)

    def test_external_path_rejected_without_read(self):
        with self.assertRaises(Invalid):
            load(Path.cwd().parent / 'never-read-this-file')

    def test_determinism_and_input_immutability(self):
        data = catalog({'app': {'1': {'b': '*'}, '2': {'b': '*'}}, 'b': {'1': {}, '2': {}}})
        before = copy.deepcopy(data)
        a = solve(data)
        reverse = json.loads(json.dumps(data), object_pairs_hook=lambda pairs: dict(reversed(pairs)))
        self.assertEqual(a, solve(reverse))
        self.assertEqual(data, before)

    def test_random_catalogs_against_exhaustive_oracle(self):
        rng = random.Random(737)
        for case in range(400):
            packages = {}
            names = ['a', 'b', 'c', 'd']
            for p in names:
                packages[p] = {}
                for v in ['1', '2']:
                    deps = {d: rng.choice(['*', '==1', '==2']) for d in names if rng.random() < .3}
                    packages[p][v] = deps
            data = catalog(packages, {'a': rng.choice(['*', '==1', '==2'])})
            result = solve(data)
            self.assertEqual(result['status'] == 'resolved', brute(data), (case, data, result))
            self.assertNotEqual(result['status'], 'inconclusive')


if __name__ == '__main__':
    unittest.main()
