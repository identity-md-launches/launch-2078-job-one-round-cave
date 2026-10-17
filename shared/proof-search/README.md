# Proof Search

Turn an EIP-1186 witness into a local receipt, then find raw storage claims with
hash-checked line citations. Python 3.10+, standard library only, offline.
The verifier and search engine are ordinary copies from lines 2 and 3, so this
folder works independently of the cave. Nothing signs, sends, installs or pays.

From the workspace root, choose a new output directory with an existing parent:

```sh
python3 -B shared/proof-search/proof_search.py demo --output shared/proof-search/try-receipt
python3 -B shared/proof-search/proof_search.py query shared/proof-search/try-receipt 'Slot Value'
```

The demo verified the real historical ZTO/IMD PoolManager storage witness and
returned `receipt.md:9-17` with the exact slot and raw value (ranking may choose
other overlapping passages for other queries). Repeating creation fails instead
of overwriting the receipt. Querying an edited receipt fails as stale. Both were
checked alongside altered-proof rejection. Run the integration checks with:

```sh
python3 -B shared/proof-search/test_proof_search.py
```

For your own witness use `prepare BUNDLE --state-root ROOT --address ADDRESS
--slot SLOT --output NEW_DIRECTORY`; repeat `--slot` for every expected slot.
No root, address or slot set is inferred from untrusted witness metadata. The
receipt excludes bundle labels, block metadata and descriptive claims. Search
integrity does not establish authorship or truth. Receipt/index creation is not
transactional: disk errors may leave an incomplete new directory. Preserve the
original witness and expected anchor for independent re-verification.

The demo root is illustrative, copied from a historical RPC observation, and
is not consensus authenticated. General use requires an independently trusted
root. No current price, ERC-20 balance or slot-layout meaning is inferred.
The pool ID and slot derivation are assignment context, not verified labels in
the receipt. Native balance means ETH in the account. Original public source:
https://ethereum-rpc.publicnode.com. The bundled witness is a historical snapshot.

Reuse: `witness.py` copied unchanged from line-2/tools/state-witness/witness.py;
`search.py` copied unchanged from line-3/tools/evidence-search/search.py;
`zto-pool-mainnet.json` copied unchanged from line 2's examples. Their original
READMEs describe algorithm limits; all verifier and search limits still apply.
Line 3 can ingest these receipts; line 2 gains cited human-readable proof output.
Line 1 can merge receipt commentary separately, but generated facts should be
regenerated from proofs. Line 4 can resolve tool versions in a finite catalog
without needing any installation or coin.
