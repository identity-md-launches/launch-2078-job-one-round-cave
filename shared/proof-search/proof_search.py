#!/usr/bin/env python3
"""Create a searchable receipt only after verifying an Ethereum state proof."""
import argparse
import json
from pathlib import Path
import sys
import witness
import search


def receipt(report):
    # Only verifier output enters the document; unproven bundle labels are omitted.
    lines = ['# Ethereum state proof receipt',
             'Trust: ' + report['trust'],
             'Expected state root: ' + report['stateRoot'],
             'Expected account address: ' + report['address'],
             'Account exists: ' + str(report['accountExists']).lower(),
             'Nonce: ' + report['nonce'],
             'Native ETH balance wei: ' + report['nativeBalanceWei'],
             'Code hash: ' + report['codeHash'],
             'Storage root: ' + report['storageRoot']]
    for item in report['storage']:
        lines.extend(['', '# Raw storage claim',
                      'Expected state root: ' + report['stateRoot'],
                      'Expected account address: ' + report['address'],
                      'Slot: ' + item['slot'], 'Value: ' + item['value'],
                      'Exists: ' + str(item['exists']).lower(),
                      'Trust: ' + report['trust']])
    return '\n'.join(lines) + '\n'


def prepare(bundle_path, root, address, slots, destination):
    bundle = witness.load_bundle(bundle_path)
    report = witness.verify(bundle['proof'], root, address, slots)
    text = receipt(report)
    target = search.workspace_path(destination)
    # Fail before writes on invalid proofs, symlinks, or existing destinations.
    target.mkdir()  # parent must already exist; never replace user files
    (target / 'receipt.md').write_text(text, encoding='utf-8')
    search.write_index(target / 'index.json', search.build_index(target))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('demo', help='historical ZTO/IMD pool proof; illustrative root')
    demo.add_argument('--output', required=True)
    make = sub.add_parser('prepare')
    make.add_argument('bundle')
    make.add_argument('--state-root', required=True)
    make.add_argument('--address', required=True)
    make.add_argument('--slot', action='append', default=[])
    make.add_argument('--output', required=True)
    query = sub.add_parser('query')
    query.add_argument('directory')
    query.add_argument('text')
    args = parser.parse_args(argv)
    try:
        if args.command == 'query':
            root = search.workspace_path(args.directory)
            result = search.search(search.load_index(root / 'index.json'), args.text, root)
            print(json.dumps(result, indent=2))
            return 0 if result['hits'] else 1
        if args.command == 'demo':
            bundle = Path(__file__).with_name('zto-pool-mainnet.json')
            slots = [witness.hex0(witness.keccak256(witness.hex_data(witness.ZTO_POOL_ID, 32) + (6).to_bytes(32, 'big')))]
            report = prepare(bundle, witness.DEMO_ROOT, witness.POOL_MANAGER, slots, args.output)
        else:
            report = prepare(args.bundle, args.state_root, args.address, args.slot, args.output)
        print(json.dumps({'verified': report['verified'], 'output': args.output,
                          'trust': report['trust']}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RecursionError):
        print(json.dumps({'error': 'Invalid proof, input, destination, or stale receipt.'}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
