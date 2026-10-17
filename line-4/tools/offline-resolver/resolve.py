#!/usr/bin/env python3
"""Finite, deterministic dependency resolution using only the standard library."""
import argparse
import json
import re
import sys
from pathlib import Path

MAX_BYTES = 1_000_000
NAME = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}\Z')
VERSION = re.compile(r'(?:0|[1-9][0-9]{0,7})(?:\.(?:0|[1-9][0-9]{0,7})){0,3}\Z')
CLAUSE = re.compile(r'(==|!=|>=|<=|>|<)\s*(\S+)\Z')


class Invalid(ValueError):
    pass


class Exhausted(Exception):
    pass


def name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise Invalid('package names must be 1–100 ASCII letters/digits/._-')
    return re.sub(r'[-_.]+', '-', value).lower()


def version(value):
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise Invalid('release must have 1–4 numeric components: ' + repr(value))
    parts = tuple(map(int, value.split('.')))
    return parts + (0,) * (4 - len(parts))


def constraint(value):
    if not isinstance(value, str) or len(value) > 1000:
        raise Invalid('constraint must be a string of at most 1000 characters')
    if value.strip() == '*':
        return []
    result = []
    for text in value.split(','):
        match = CLAUSE.fullmatch(text.strip())
        if match is None:
            raise Invalid('unsupported constraint clause: ' + repr(text))
        result.append((match[1], version(match[2])))
    return result


def accepts(release, spec):
    v = version(release)
    for op, bound in constraint(spec):
        ok = {'==': v == bound, '!=': v != bound, '>=': v >= bound,
              '<=': v <= bound, '>': v > bound, '<': v < bound}[op]
        if not ok:
            return False
    return True


def requirements(obj, where):
    if not isinstance(obj, dict):
        raise Invalid(where + ' must be a package-to-constraint object')
    result = {}
    for raw, spec in obj.items():
        canonical = name(raw)
        if canonical in result:
            raise Invalid(where + ' has duplicate canonical package ' + canonical)
        constraint(spec)
        result[canonical] = spec
    return dict(sorted(result.items()))


def validate(data):
    if not isinstance(data, dict) or set(data) != {'packages', 'roots'}:
        raise Invalid('catalog must contain exactly packages and roots')
    if not isinstance(data['packages'], dict) or len(data['packages']) > 1000:
        raise Invalid('packages must be an object with at most 1000 packages')
    packages = {}
    total = 0
    for raw, releases in data['packages'].items():
        package = name(raw)
        if package in packages:
            raise Invalid('duplicate canonical package ' + package)
        if not isinstance(releases, dict):
            raise Invalid('releases for ' + package + ' must be an object')
        seen, entries = set(), {}
        for release, deps in releases.items():
            normalized = version(release)
            if normalized in seen:
                raise Invalid('equivalent duplicate release for ' + package)
            seen.add(normalized)
            entries[release] = requirements(deps, package + '@' + release)
            total += 1
            if total > 10000:
                raise Invalid('catalog exceeds 10000 releases')
        packages[package] = entries
    roots = requirements(data['roots'], 'roots')
    if not roots:
        raise Invalid('at least one root requirement is required')
    return packages, roots


def solve(data, max_steps=10000):
    """Search all reachable assignments, unless the explicit decision limit stops us.

    Constraints are rebuilt per branch. This prevents dependencies of abandoned
    releases from contaminating a later branch. Each requirement records its cause.
    """
    if type(max_steps) is not int or not 1 <= max_steps <= 1000000:
        raise Invalid('max_steps must be an integer between 1 and 1000000')
    packages, roots = validate(data)
    steps = 0

    def search(selected, depth):
        nonlocal steps
        if depth > 200:
            raise Exhausted('reachable dependency depth exceeds 200')
        steps += 1
        if steps > max_steps:
            raise Exhausted('decision budget exhausted')
        needed = {p: [{'constraint': s, 'source': 'root'}] for p, s in roots.items()}
        for p, v in sorted(selected.items()):
            for dep, spec in packages[p][v].items():
                needed.setdefault(dep, []).append({'constraint': spec, 'source': p + '@' + v})
        choices = []
        for p, causes in sorted(needed.items()):
            available = sorted(packages.get(p, {}), key=version, reverse=True)
            allowed = [v for v in available if all(accepts(v, c['constraint']) for c in causes)]
            if p in selected:
                allowed = [v for v in allowed if v == selected[p]]
            if not allowed:
                return None, {'package': p, 'requirements': causes,
                              'available_versions': available,
                              'selected_version': selected.get(p),
                              'branch': dict(sorted(selected.items()))}
            if p not in selected:
                choices.append((len(allowed), p, allowed))
        if not choices:
            return dict(sorted(selected.items())), None
        _, p, allowed = min(choices)
        # A bounded representative conflict is retained, never an unbounded tree.
        first_conflict = None
        for v in allowed:
            answer, conflict = search(dict(selected, **{p: v}), depth + 1)
            if answer is not None:
                return answer, None
            if first_conflict is None:
                first_conflict = conflict
        return None, first_conflict

    try:
        selected, conflict = search({}, 0)
    except Exhausted as exc:
        return {'status': 'inconclusive', 'reason': str(exc),
                'steps': min(steps, max_steps), 'max_steps': max_steps}
    if selected is None:
        return {'status': 'unsatisfiable', 'steps': steps, 'max_steps': max_steps,
                'conflict': conflict,
                'explanation': 'All reachable candidate assignments were exhausted. '
                'The conflict is one representative dead end, not a minimal unsatisfiable core.'}
    # Independent final checks catch inconsistent selections including cycles.
    for p, spec in roots.items():
        if p not in selected or not accepts(selected[p], spec):
            raise AssertionError('internal root validation failed')
    edges = []
    for p, v in selected.items():
        for dep, spec in sorted(packages[p][v].items()):
            if dep not in selected or not accepts(selected[dep], spec):
                raise AssertionError('internal dependency validation failed')
            edges.append({'from': p + '@' + v, 'to': dep + '@' + selected[dep],
                          'constraint': spec})
    return {'status': 'resolved', 'steps': steps, 'max_steps': max_steps,
            'selected': selected, 'roots': roots, 'edges': edges}


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise Invalid('duplicate JSON key: ' + key)
        obj[key] = value
    return obj


def load(path):
    # No discovery, home-directory access, config lookup, or external symlink reads.
    root = Path.cwd().resolve()
    target = Path(path).resolve()
    if not target.is_relative_to(root):
        raise Invalid('catalog must be inside the current workspace')
    with target.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise Invalid('catalog exceeds 1000000 bytes')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog', help='workspace-local catalog JSON, or demo')
    parser.add_argument('--max-steps', type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        path = Path(__file__).parent / 'examples/requests.json' if args.catalog == 'demo' else args.catalog
        result = solve(load(path), args.max_steps)
    except (Invalid, OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        print(json.dumps({'status': 'invalid', 'error': str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return {'resolved': 0, 'unsatisfiable': 1, 'inconclusive': 3}[result['status']]


if __name__ == '__main__':
    sys.exit(main())
