# Offline Resolver

Resolve a finite package catalog into one compatible version per reachable package.
Uses Python 3.9+ and only the standard library. It does not install, import, download,
or execute packages. The resolver itself never accesses the network. All input is
explicit JSON inside the current working directory; external paths and symlinks
that resolve outside that directory are rejected.

From the repository root, see it work with real Requests release metadata:

```sh
python3 -B line-4/tools/offline-resolver/resolve.py demo
```

This succeeds offline. In this run it resolved Requests 2.32.5, urllib3 1.26.20,
idna 3.11, charset-normalizer 3.4.4, and certifi 2025.10.5 in six search states.
The root constraint `urllib3 <2` deliberately exercises a version choice.
These are compatibility results in this finite catalog, not recommended versions.

## Supply a catalog

```json
{
  "roots": {"app": ">=1,<3"},
  "packages": {
    "app": {
      "1": {"shared": "==1"},
      "2": {"shared": ">=2"}
    },
    "shared": {"1": {}, "2": {}}
  }
}
```

Save your catalog inside the workspace, then pass its path instead of `demo`.
Each release maps to its mandatory dependencies. Empty objects mean no dependencies.
A package with no matching release, including a missing package, causes a conflict
if a selected dependency or root requires it. Unreachable catalog packages have no
effect. Cycles are permitted and all selected edges are checked before success.
Package names are case-insensitive, with runs of `.`, `_`, and `-` equivalent.

Supported versions: one to four nonnegative decimal components, each at most eight
digits, with no leading zeros. Missing components compare as zeros (`2 == 2.0`).
Equivalent releases may not appear twice under one package. This is a deliberately
small numeric release grammar, **not full PEP 440, npm semver, or pip compatibility**.
Constraints are `*` or comma-separated `==`, `!=`, `>=`, `<=`, `>`, and `<` clauses.
No prereleases, epochs, local labels, wildcards, OR, caret, tilde, or environment
markers are accepted. Unsupported syntax is an error rather than a guess.

Search picks the unresolved package with the fewest viable releases, then its
highest release first; ties use canonical package names. The answer is deterministic
but not an optimization over all package versions. Backtracking fully discards an
abandoned release's dependencies.

## Results and limits

JSON goes to stdout, with these exit codes:

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `resolved` | Every root and reachable dependency has a compatible assignment. |
| 1 | `unsatisfiable` | Exhaustive search found no assignment **within this catalog**. |
| 2 | `invalid` | Unsupported input, invalid path, parse or file error. |
| 3 | `inconclusive` | Search decision or depth limit reached; no impossibility claim. |

A successful result lists selected versions, roots, and every dependency edge with
its constraint. A conflict gives the package, source requirements, available
versions, and one failed branch's assignments. It is a representative dead end,
not a minimal conflict or a proof that this particular branch was the only option.
The `unsatisfiable` label comes from exhausting every branch; the displayed branch
provides a concrete failure to investigate.

Default budget: 10,000 search states, configurable with `--max-steps` from 1 to
1,000,000. Depth is limited to 200 selected packages. Catalog reads are capped at
1,000,000 bytes, 1,000 package names, and 10,000 releases. Duplicate JSON keys,
canonical names, and equivalent releases are rejected. These bounds limit input
and branching; there is no wall-clock guarantee. Large hard catalogs may need a
higher budget or a later, more efficient solver. An intentionally low budget can
be tried with `demo --max-steps 1` (expected exit 3).

This is not an installable lockfile. It does not assess artifacts, hashes, Python
versions, operating systems, extras, licenses, vulnerabilities, availability, or
trust in package publishers. Unsatisfiable does not mean there is no solution on
PyPI; omitted versions may supply one. No dependency or network access is needed
to verify the included example.

## Real example provenance

`examples/requests.json` is a finite projection of ten public PyPI release metadata
responses. `examples/sources.json` records each URL, observed time, original
`requires_dist`, `requires_python`, and excluded conditional requirements.
For example: [Requests 2.32.5 metadata](https://pypi.org/pypi/requests/2.32.5/json).
All unmarked dependencies from the selected releases are represented; optional or
conditional requirements and interpreter constraints are explicitly out of scope.
The source responses were read as data; package code was never downloaded or run.

The optional refresh command below reads only the ten explicitly listed public
URLs, uses its own User-Agent, and rewrites only the two bundled example JSONs:

```sh
python3 -B line-4/tools/offline-resolver/build_example.py
```

Do not run refresh for offline verification; the committed snapshot is sufficient.

## Checks performed

```sh
python3 -B -m unittest discover -s line-4/tools/offline-resolver -p 'test_*.py' -v
```

Seventeen tests passed, including 400 seeded random cyclic catalogs compared to
an independent exhaustive enumerator, backtracking with abandoned dependencies,
satisfiable and conflicting cycles, missing packages, numeric boundaries,
canonical name collisions, duplicate JSON, bounded reads, external-path rejection,
deterministic output, immutability, budget exhaustion, and the real metadata demo.
