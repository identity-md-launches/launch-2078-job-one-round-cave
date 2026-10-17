#!/usr/bin/env python3
"""Optional read-only refresh of the explicitly listed public PyPI metadata.

Run from the repository root. This does not install or execute any package.
"""
import concurrent.futures
import datetime
import json
import re
import urllib.request
from pathlib import Path

RELEASES = [('requests', '2.31.0'), ('requests', '2.32.5'),
            ('idna', '3.10'), ('idna', '3.11'),
            ('urllib3', '1.26.20'), ('urllib3', '2.5.0'),
            ('charset-normalizer', '3.4.3'), ('charset-normalizer', '3.4.4'),
            ('certifi', '2025.8.3'), ('certifi', '2025.10.5')]


def fetch(item):
    package, release = item
    url = f'https://pypi.org/pypi/{package}/{release}/json'
    request = urllib.request.Request(url, headers={'User-Agent': 'Crystal-Line4-OfflineResolver/1.0'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=25) as response:
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError('metadata response exceeds bound')
    info = json.loads(raw)['info']
    if info['version'] != release:
        raise ValueError('unexpected metadata release')
    original = info.get('requires_dist') or []
    dependencies, excluded = {}, []
    for requirement in original:
        if ';' in requirement:
            # Explicitly omit optional/conditional metadata; never infer an environment.
            excluded.append(requirement)
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)\s*(.*)', requirement)
        if not match:
            raise ValueError('unsupported requirement: ' + requirement)
        name, spec = match.groups()
        dependencies[name.replace('_', '-').lower()] = spec.strip(' ()') or '*'
    return package, release, dependencies, {
        'url': url, 'package': info['name'], 'version': release,
        'requires_python': info.get('requires_python'),
        'requires_dist': original, 'excluded_conditional_requirements': excluded}


def main():
    destination = Path('line-4/tools/offline-resolver/examples')
    packages, sources = {}, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for p, v, deps, source in pool.map(fetch, RELEASES):
            packages.setdefault(p, {})[v] = deps
            sources.append(source)
    catalog = {'roots': {'requests': '==2.32.5', 'urllib3': '<2'}, 'packages': packages}
    # Validate using exactly the grammar the resolver actually supports.
    from resolve import validate
    validate(catalog)
    provenance = {'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'sources': sources,
                  'scope': 'Finite package-version compatibility only. Conditional dependencies, '
                           'extras, Python constraints, artifacts and platform compatibility '
                           'are excluded; this is not an installable lockfile.'}
    destination.mkdir(parents=True, exist_ok=True)
    for filename, value in [('requests.json', catalog), ('sources.json', provenance)]:
        text = json.dumps(value, indent=2, sort_keys=True) + '\n'
        if len(text.encode()) > 100_000:
            raise ValueError('example exceeds deliverable file limit')
        (destination / filename).write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
