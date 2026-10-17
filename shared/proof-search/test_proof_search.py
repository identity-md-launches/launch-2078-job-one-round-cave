import copy
import json
from pathlib import Path
import tempfile
import unittest
import proof_search as p

class Integration(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch'); scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = Path(p.__file__).with_name('zto-pool-mainnet.json')
        self.slot = p.witness.hex0(p.witness.keccak256(p.witness.hex_data(p.witness.ZTO_POOL_ID,32)+(6).to_bytes(32,'big')))
    def prepare(self, bundle=None):
        return p.prepare(bundle or self.bundle,p.witness.DEMO_ROOT,p.witness.POOL_MANAGER,[self.slot],self.root/'out')
    def test_real_receipt_search_and_stale_detection(self):
        self.assertTrue(self.prepare()['verified'])
        out=self.root/'out'
        index=p.search.load_index(out/'index.json')
        hit=p.search.search(index,'Slot Value',out)['hits'][0]
        self.assertIn(self.slot, hit['text'])
        self.assertTrue(hit['source_verified'])
        with self.assertRaises(FileExistsError): self.prepare()
        (out/'receipt.md').write_text('Slot Value forged\n')
        with self.assertRaises(p.search.SearchError): p.search.search(index,'Slot Value',out)
    def test_bad_proof_writes_nothing(self):
        bundle=json.loads(self.bundle.read_text())
        bundle['proof']['storageProof'][0]['value']='0x1'
        path=self.root/'bad.json'; path.write_text(json.dumps(bundle))
        with self.assertRaises(p.witness.Invalid): self.prepare(path)
        self.assertFalse((self.root/'out').exists())
    def test_unverified_metadata_excluded(self):
        bundle=json.loads(self.bundle.read_text())
        bundle['block']={'number':'invented block'}
        bundle['label']='invented label'
        path=self.root/'labels.json'; path.write_text(json.dumps(bundle))
        self.prepare(path)
        self.assertNotIn('invented',(self.root/'out'/'receipt.md').read_text())
    def test_wrong_slot_and_root_rejected(self):
        bundle=p.witness.load_bundle(self.bundle)
        for root, slots in [(p.witness.DEMO_ROOT,[]),('0x'+'11'*32,[self.slot])]:
            with self.assertRaises(p.witness.Invalid): p.witness.verify(bundle['proof'],root,p.witness.POOL_MANAGER,slots)

if __name__=='__main__': unittest.main()
