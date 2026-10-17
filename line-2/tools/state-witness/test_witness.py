"""Offline adversarial checks, including an actual mainnet ZTO witness."""
import copy
import importlib.util
import json
from pathlib import Path
import random
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('witness', Path(__file__).with_name('witness.py'))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def hp(path, leaf=True):
    digits = [2 * leaf + len(path) % 2] + ([] if len(path) % 2 else [0]) + path
    return bytes(16 * digits[i] + digits[i+1] for i in range(0, len(digits), 2))


def encoded_int(value):
    return value.to_bytes((value.bit_length()+7)//8, 'big')


def single(key, value):
    raw = w.rlp_encode([hp(w.nibbles(key)), value])
    return w.keccak256(raw), [w.hex0(raw)]


class KeccakAndRLP(unittest.TestCase):
    def test_independent_ethereum_hash_vectors(self):
        vectors = {
            b'': 'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470',
            b'abc': '4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45',
            bytes.fromhex('80'): '56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421',
        }
        for data, digest in vectors.items():
            self.assertEqual(w.keccak256(data).hex(), digest)

    def test_erc20_selector(self):
        self.assertEqual(w.keccak256(b'transfer(address,uint256)')[:4].hex(), 'a9059cbb')

    def test_official_rlp_examples(self):
        cases = [(b'', '80'), ([], 'c0'), (b'dog', '83646f67'),
                 ([b'cat', b'dog'], 'c88363617483646f67'),
                 ([[], [[]], [[], [[]]]], 'c7c0c1c0c3c0c1c0')]
        for value, encoded in cases:
            self.assertEqual(w.rlp_encode(value).hex(), encoded)
            self.assertEqual(w.rlp_decode(bytes.fromhex(encoded)), value)

    def test_rlp_length_boundaries(self):
        rng = random.Random(1186)
        for length in (0, 1, 55, 56, 135, 136, 137, 255, 256, 1024):
            raw = bytes(rng.randrange(256) for _ in range(length))
            for value in (raw, [raw], [[], [raw, b'']]):
                self.assertEqual(w.rlp_decode(w.rlp_encode(value)), value)

    def test_noncanonical_truncated_and_trailing_rlp(self):
        for raw in ('', '8101', 'b80101', 'b90038', 'f800', 'c201', '83646f', '8080', 'b83801'):
            with self.subTest(raw=raw), self.assertRaises(w.Invalid):
                w.rlp_decode(bytes.fromhex(raw))

    def test_nesting_limit(self):
        value = b'x'
        for _ in range(90):
            value = [value]
        with self.assertRaises(w.Invalid):
            w.rlp_decode(w.rlp_encode(value))

    def test_canonical_integer_and_hex(self):
        for value in ('0x00', '-1', '0X1', '0x', '0x-1', '0x'+'f'*65):
            with self.assertRaises(w.Invalid):
                w.quantity(value)
        for value in (b'\0', b'\0\x01'):
            with self.assertRaises(w.Invalid):
                w.rlp_integer(value, 'test')
        self.assertEqual(w.quantity('0x0'), 0)
        self.assertEqual(w.rlp_integer(b'', 'test'), 0)
        self.assertEqual(w.slot_number('0x'+'0'*63+'1'), 1)


class PatriciaTrie(unittest.TestCase):
    def test_leaf_inclusion_and_divergent_leaf_absence(self):
        root, proof = single(b'abc', b'value')
        self.assertEqual(w.trie_value(root, b'abc', proof), b'value')
        self.assertIsNone(w.trie_value(root, b'abd', proof))
        self.assertIsNone(w.trie_value(root, b'ab', proof))
        self.assertIsNone(w.trie_value(root, b'abcd', proof))

    def test_empty_trie_absence(self):
        self.assertIsNone(w.trie_value(w.EMPTY_TRIE, b'any', []))

    def test_inline_child_and_empty_branch_absence(self):
        # Exact short child structure: lists embedded in RLP, not byte strings.
        branch = [b''] * 17
        branch[1] = [bytes.fromhex('32'), b'v']
        raw = w.rlp_encode(branch)
        root, proof = w.keccak256(raw), [w.hex0(raw)]
        self.assertEqual(w.trie_value(root, bytes.fromhex('12'), proof), b'v')
        self.assertIsNone(w.trie_value(root, bytes.fromhex('22'), proof))

    def test_extension_to_hashed_branch_and_branch_value(self):
        branch = [b''] * 16 + [b'x'*40]
        raw_branch = w.rlp_encode(branch)
        raw_extension = w.rlp_encode([bytes.fromhex('0012'), w.keccak256(raw_branch)])
        proof = [w.hex0(raw_extension), w.hex0(raw_branch)]
        root = w.keccak256(raw_extension)
        self.assertEqual(w.trie_value(root, bytes.fromhex('12'), proof), b'x'*40)
        self.assertIsNone(w.trie_value(root, bytes.fromhex('13'), proof))
        self.assertEqual(w.trie_value(root, bytes.fromhex('12'), list(reversed(proof))), b'x'*40)

    def test_missing_root_and_missing_child_rejected(self):
        root, proof = single(b'abc', b'value')
        with self.assertRaises(w.Invalid):
            w.trie_value(root, b'abc', [])
        extension = w.rlp_encode([bytes.fromhex('0012'), root])
        with self.assertRaises(w.Invalid):
            w.trie_value(w.keccak256(extension), bytes.fromhex('12'), [w.hex0(extension)])

    def test_invalid_compact_paths(self):
        for encoded in (b'', b'\x40', b'\x21'):
            with self.assertRaises(w.Invalid):
                w.compact_path(encoded)

    def test_noncanonical_hash_and_inline_child_references(self):
        branch = [b'']*17
        child = w.rlp_encode([bytes.fromhex('32'), b'v'])
        for reference, extra in ((child, []), (w.keccak256(child), [w.hex0(child)]),
                                 ([b'\x32', b'x'*40], [])):
            branch[1] = reference
            raw = w.rlp_encode(branch)
            with self.subTest(reference=reference), self.assertRaises(w.Invalid):
                w.trie_value(w.keccak256(raw), b'\x12', [w.hex0(raw)] + extra)

    def test_invalid_node_and_empty_extension(self):
        for node in ([b'one'], [b'\0', b'x'*32], [b'\x20', b'']):
            raw = w.rlp_encode(node)
            with self.assertRaises(w.Invalid):
                w.trie_value(w.keccak256(raw), b'', [w.hex0(raw)])

    def test_resource_bounds(self):
        with self.assertRaises(w.Invalid):
            w.trie_value(w.EMPTY_TRIE, b'a', ['0xc0']*129)
        with self.assertRaises(w.Invalid):
            w.rlp_decode(b'x'*32769)


class EIP1186(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads((Path(__file__).parent/'examples'/'zto-mainnet.json').read_text())
        self.proof = self.bundle['proof']
        self.root = w.DEMO_ROOT

    def verify(self, proof=None, root=None, address=None, slots=None):
        return w.verify(self.proof if proof is None else proof, self.root if root is None else root,
                        w.ZTO if address is None else address, ['0x0','0x1'] if slots is None else slots)

    def test_real_zto_mainnet(self):
        report = self.verify()
        self.assertTrue(report['verified'])
        self.assertTrue(report['accountExists'])
        self.assertEqual(report['nonce'], '0x1')
        self.assertEqual(len(report['storage']), 2)
        self.assertFalse(report['storage'][0]['exists'])

    def test_real_zto_pool_nonzero_storage_inclusion(self):
        bundle = json.loads((Path(__file__).parent/'examples'/'zto-pool-mainnet.json').read_text())
        slot = w.hex0(w.keccak256(w.hex_data(w.ZTO_POOL_ID,32)+(6).to_bytes(32,'big')))
        self.assertEqual(slot, '0x85763e16f60121d4266264cb693cca4d6bdb9e98ff9cc3d698d892d90342971b')
        report = w.verify(bundle['proof'], w.DEMO_ROOT, w.POOL_MANAGER, [slot])
        self.assertTrue(report['storage'][0]['exists'])
        self.assertNotEqual(report['storage'][0]['value'], '0x0')
        proof = copy.deepcopy(bundle['proof'])
        proof['storageProof'][0]['value'] = '0x0'
        with self.assertRaises(w.Invalid):
            w.verify(proof, w.DEMO_ROOT, w.POOL_MANAGER, [slot])

    def test_tampered_all_claims(self):
        for key, value in {'nonce':'0x2', 'balance':'0x1', 'storageHash':'0x'+'11'*32,
                           'codeHash':'0x'+'11'*32, 'address':'0x'+'11'*20}.items():
            proof = copy.deepcopy(self.proof)
            proof[key] = value
            with self.subTest(key=key), self.assertRaises(w.Invalid):
                self.verify(proof)

    def test_wrong_root_wrong_expected_address(self):
        with self.assertRaises(w.Invalid):
            self.verify(root='0x'+'11'*32)
        with self.assertRaises(w.Invalid):
            self.verify(address='0x'+'11'*20)

    def test_missing_or_altered_account_nodes(self):
        for mode in ('missing', 'altered'):
            proof = copy.deepcopy(self.proof)
            if mode == 'missing':
                proof['accountProof'].pop(0)
            else:
                node = bytearray.fromhex(proof['accountProof'][0][2:])
                node[-1] ^= 1
                proof['accountProof'][0] = w.hex0(node)
            with self.subTest(mode=mode), self.assertRaises(w.Invalid):
                self.verify(proof)

    def test_storage_value_tampering(self):
        proof = copy.deepcopy(self.proof)
        proof['storageProof'][0]['value'] = '0x1'
        with self.assertRaises(w.Invalid):
            self.verify(proof)

    def test_storage_slot_set_binding_and_duplicates(self):
        for slots in ([], ['0x0'], ['0x0','0x2'], ['0x0','0x0']):
            with self.subTest(slots=slots), self.assertRaises(w.Invalid):
                self.verify(slots=slots)
        proof = copy.deepcopy(self.proof)
        proof['storageProof'][1] = proof['storageProof'][0]
        with self.assertRaises(w.Invalid):
            self.verify(proof)

    def test_nonzero_storage_inclusion(self):
        storage_root, storage_proof = single(w.keccak256((7).to_bytes(32,'big')), w.rlp_encode(encoded_int(123456)))
        account = w.rlp_encode([b'\x01', b'', storage_root, w.EMPTY_CODE])
        root, account_proof = single(w.keccak256(bytes.fromhex(w.ZTO[2:])), account)
        proof = {'address':w.ZTO, 'nonce':'0x1', 'balance':'0x0', 'storageHash':w.hex0(storage_root),
                 'codeHash':w.hex0(w.EMPTY_CODE), 'accountProof':account_proof,
                 'storageProof':[{'key':'0x7','value':hex(123456),'proof':storage_proof}]}
        report = w.verify(proof, w.hex0(root), w.ZTO, ['0x7'])
        self.assertEqual(report['storage'][0]['value'], hex(123456))
        self.assertTrue(report['storage'][0]['exists'])

    def test_nonexistent_account_and_storage(self):
        proof = {'address':w.ZTO, 'nonce':'0x0', 'balance':'0x0', 'storageHash':w.hex0(w.EMPTY_TRIE),
                 'codeHash':w.hex0(w.EMPTY_CODE), 'accountProof':[],
                 'storageProof':[{'key':'0x0','value':'0x0','proof':[]}]}
        result = w.verify(proof, w.hex0(w.EMPTY_TRIE), w.ZTO, ['0x0'])
        self.assertFalse(result['accountExists'])
        self.assertFalse(result['storage'][0]['exists'])

    def test_invalid_zero_leaf_rejected(self):
        storage_root, storage_proof = single(w.keccak256((0).to_bytes(32,'big')), w.rlp_encode(b''))
        raw_account = w.rlp_encode([b'', b'', storage_root, w.EMPTY_CODE])
        root, account_proof = single(w.keccak256(bytes.fromhex(w.ZTO[2:])), raw_account)
        proof = {'address':w.ZTO,'nonce':'0x0','balance':'0x0','storageHash':w.hex0(storage_root),
                 'codeHash':w.hex0(w.EMPTY_CODE),'accountProof':account_proof,
                 'storageProof':[{'key':'0x0','value':'0x0','proof':storage_proof}]}
        with self.assertRaises(w.Invalid):
            w.verify(proof,w.hex0(root),w.ZTO,['0x0'])

    def test_duplicate_json_key_and_nan_rejected(self):
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(w.Invalid):
                w.parse_json(text)

    def test_rpc_methods_allowlist_and_redirects(self):
        with self.assertRaises(w.Invalid):
            w.rpc('https://example.invalid','eth_sendRawTransaction',[])
        with self.assertRaises(w.Invalid):
            w.NoRedirect().redirect_request(None,None,302,'Found',{},'https://example.invalid')
        for url in ('file:///x','https://user:pass@example.invalid','https://example.invalid/?key=a'):
            with self.assertRaises(w.Invalid):
                w.rpc(url,'eth_chainId',[])

    def test_capture_rejects_other_chain(self):
        with mock.patch.object(w, 'rpc', return_value='0x2'):
            with self.assertRaises(w.Invalid):
                w.capture('https://example.invalid', w.ZTO, [], 'finalized')

    def test_capture_pins_numeric_block_and_rechecks_proof(self):
        calls = []
        def fake(endpoint, method, params):
            calls.append((method, params))
            return {'eth_chainId':'0x1', 'eth_getBlockByNumber':self.bundle['block'],
                    'eth_getProof':self.proof}[method]
        with mock.patch.object(w,'rpc',side_effect=fake):
            result=w.capture('https://example.invalid', w.ZTO,['0x0','0x1'],'finalized')
        self.assertEqual(calls[2][1][2], self.bundle['block']['number'])
        self.assertEqual(len(calls[2][1][1][0]),66)
        self.assertEqual(result['proof'],self.proof)


if __name__ == '__main__':
    unittest.main()
