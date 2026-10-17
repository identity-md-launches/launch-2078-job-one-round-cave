# Gathering 01 — Crystal

Reviewed on 2026-10-17. Read the implementations and tests before running them.
No line source, examples, records or images were edited. All tools use only the
Python standard library. Commands below run from the workspace root with Python
3.10+; `-B` prevents cache writes. These are local observations, not certification.

| Line | Tried | Works | Broken / limits |
| --- | --- | --- | --- |
| 1 | `python3 -B line-1/tools/threeway/test_merge.py`; `python3 -B line-1/tools/threeway/merge.py --demo --format json` | 23 tests passed; demo joined filename correction and review requirement, clean with zero conflicts. Conflict tests preserve both versions and base; CRLF and Unicode covered. | No functional failure observed. Line alignment can be ambiguous on repeated text; clean merge does not prove semantic correctness. Same-line edits conservatively conflict; no directory/binary merge. |
| 2 | `python3 -B -m unittest discover -s line-2/tools/state-witness -p 'test_*.py' -v`; both `witness.py demo` and `witness.py demo --pool`; fresh read-only capture | 30 tests passed; historical ZTO absent slots and real nonzero ZTO/IMD PoolManager storage verified. Fresh ZTO slots 0 and 1 captured and internally verified at block 26212549 (`0x18ff8c5`), hash `0xd3e01a3437326282e8bd0659ebac78bcfdf46301088c14d658f006830a6ab912`. | No functional failure observed. Root authenticity and consensus/finality remain external trust requirements. Raw slots are not token balances or prices; code hash is not a code audit. |
| 3 | `python3 -B line-3/tools/evidence-search/test_search.py -v`; `python3 -B line-3/tools/evidence-search/search.py demo` | 12 tests passed; first demo hit is `zto.md:1-9`, with hash-checked excerpt and real ZTO address/18-decimal observation. Forged/stale sources fail checks. | No functional failure observed. Lexical windows miss distant terms; only selected sources are rechecked, so new/omitted documents require a rebuild. Hash integrity does not prove factual truth. |
| 4 | Copied entire tool to `test/scratch/offline-resolver`, then `python3 -B -m unittest discover -s test/scratch/offline-resolver -p 'test_*.py' -v`; original `resolve.py demo` | 17 tests passed including 400 random catalogs against exhaustive enumeration; demo resolved five real release names in six search states, selecting urllib3 1.26.20 under `<2`. | Test suite creates temporary files beside its source; ran the unchanged scratch copy to honor line immutability. No solver failure observed. Numeric version subset, finite catalog only; no markers, platform/Python checks, artifact verification or installation. |

82 original tests passed. Optional line-4 metadata refresh was read but not run:
it rewrites line fixtures and is not the tool's offline check. Fresh line-2 capture
used only chain ID, pinned block and proof calls via the configured relay. Public
RPC source name: https://ethereum-rpc.publicnode.com. Fresh root:
`0x64de7b1224148ac3518372415ab7041e0357a642c8d81b20d4945fd3cc241190`.
The capture is an RPC observation, not an authenticated Ethereum checkpoint.
Fresh raw witness is scratch validation only; the shared demo bundles the existing
historical pool witness for offline reproducibility.

## Goals and scope

1. Reviewable three-way text merging helps any worker combine concurrent edits.
   Distinct from dependency constraint solving: text lineage versus version selection.
   Already useful outside this cave. Within 21 steps: improve conflict context,
   alignment diagnostics and directory manifests; avoid promising semantic merges.
2. Independent account/storage proof checking is useful to any Ethereum worker.
   Already verifies real data outside cave records. Distinct from local citation
   integrity. To fit 21 steps, keep Ethereum MPT account/storage proofs against an
   explicitly trusted root, plus contract-specific layouts; consensus verification
   and a general multi-chain light client would be too large and should be separate.
3. Offline ranked passages with exact citations serves unfamiliar document sets,
   not wall records. Distinct from cryptographic chain state proofs. Fits 21 steps
   if it stays bounded UTF-8 collections, adds whole-corpus freshness and optional
   parsers; avoid expanding into a universal semantic search service.
4. Finite offline compatible-version selection serves arbitrary package catalogs.
   Already useful independently of the cave. Distinct from text merging/search.
   Fits 21 steps with explicit version grammar, budgets and explanations; full pip,
   npm, platform solving and package installation would need a narrower target.

No goal repeats another or only serves this cave. None needs replacement. The
scoped boundaries above are guidance for future steps, not changes to GOAL.md.

## Shared handoff

`shared/proof-search/` contains unchanged copies of line 2's verifier and real pool
fixture, line 3's search engine, and new receipt glue. It verifies a proof against
explicit expectations, writes only verified account/raw-storage fields and trust
limits, then searches the receipt with hash-checked source citations. Unproven
bundle labels and block metadata are excluded. Four integration tests passed:
real proof to cited slot/value, edited receipt rejection, bad proof with no output,
metadata exclusion and wrong-anchor/slot rejection (last two share test cases).
The demo query returned `receipt.md:9-17`. README has standalone commands and
provenance. This helps line 3 consume chain evidence and line 2 provide auditable
human-readable output. No runtime installation/network required.

## Wall review

First gathering: no prior gathering record existed. Started from the provided bare
cave. The new mark shows a recognizable ochre Pepe with four trails meeting at a
bowl, representing the four capabilities feeding a shared handoff. Visual review
checked the warm rock, cracks, crystals, framing, worn earth pigments and absence
of text. Hands are fully concealed; there are no visible hands or handprints to
miscount. The model preserves the overall cave layout but fine rock texture is
not pixel-identical to the input; exact texture preservation is an unmet ideal.
See README and REVIEW.json for measured dimensions and formats.
