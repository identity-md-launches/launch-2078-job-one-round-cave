"""Behavioral tests; all temporary sources stay under test/scratch/."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("evidence_search", Path(__file__).with_name("search.py"))
search = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search)


class EvidenceSearchTests(unittest.TestCase):
    def setUp(self):
        scratch = Path.cwd() / "test" / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.docs = self.root / "docs"
        self.docs.mkdir()

    def write(self, name, text):
        path = self.docs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        return path

    def test_exact_citations_hash_and_crlf(self):
        raw = "# facts\r\n\r\nZTO has 18 decimals.\r\n"
        self.write("zto.md", raw)
        index = search.build_index(self.docs)
        result = search.search(index, "ZTO decimals", self.docs, require_all=True)
        hit = result["hits"][0]
        self.assertEqual(hit["citation"], "zto.md:1-3")
        self.assertEqual(hit["sha256"], search.digest(raw.encode()))
        self.assertEqual(hit["text"].splitlines(), ["# facts", "", "ZTO has 18 decimals."])
        self.assertTrue(hit["source_verified"])

    def test_ranked_specific_document_and_full_address(self):
        self.write("general.md", "Tokens have names and decimals.\n")
        address = "0xd782bdea4ef02a0bd391eb9089470c8080f0a68e"
        self.write("zto.md", f"ZTO token decimals are 18. Contract {address}.\n")
        index = search.build_index(self.docs)
        self.assertEqual(search.search(index, "ZTO decimals", self.docs)["hits"][0]["path"], "zto.md")
        self.assertEqual(search.search(index, address.upper(), self.docs)["hits"][0]["path"], "zto.md")

    def test_unicode_normalization_and_query_term_deduplication(self):
        self.write("unicode.txt", "Straße CAFÉ ＺＴＯ\n")
        index = search.build_index(self.docs)
        single = search.search(index, "STRASSE café zto", self.docs, require_all=True)
        repeated = search.search(index, "STRASSE STRASSE café zto", self.docs, require_all=True)
        self.assertEqual(single["hits"], repeated["hits"])
        self.assertEqual(len(single["hits"]), 1)

    def test_source_change_and_removal_fail_closed(self):
        path = self.write("facts.md", "ZTO has 18 decimals.\n")
        index = search.build_index(self.docs)
        path.write_text("ZTO has 6 decimals.\n")
        with self.assertRaisesRegex(search.SearchError, "stale source"):
            search.search(index, "ZTO", self.docs)
        path.unlink()
        with self.assertRaises(search.SearchError):
            search.search(index, "ZTO", self.docs)

    def test_forged_excerpt_and_matching_forged_hash_still_rejected(self):
        self.write("facts.md", "ZTO has 18 decimals.\n")
        index = search.build_index(self.docs)
        forged = copy.deepcopy(index)
        forged["documents"][0]["text"] = "ZTO has 6 decimals.\n"
        with self.assertRaisesRegex(search.SearchError, "SHA-256"):
            search.search(forged, "ZTO", self.docs)
        forged["documents"][0]["sha256"] = search.digest(b"ZTO has 6 decimals.\n")
        with self.assertRaisesRegex(search.SearchError, "stale source"):
            search.search(forged, "ZTO", self.docs)

    def test_symlinks_hidden_files_and_non_document_types_excluded(self):
        target = self.write("real.md", "ZTO real document\n")
        self.write(".hidden.md", "ZTO hidden document\n")
        self.write("ignored.py", "raise RuntimeError('must never execute')\n")
        (self.docs / "link.md").symlink_to(target)
        (self.docs / "loop").symlink_to(self.docs, target_is_directory=True)
        index = search.build_index(self.docs)
        self.assertEqual([doc["path"] for doc in index["documents"]], ["real.md"])
        target.unlink()
        target.symlink_to(self.root / "nonexistent.md")
        with self.assertRaisesRegex(search.SearchError, "symlink"):
            search.search(index, "ZTO", self.docs)

    def test_paths_and_hostile_index_names_rejected_without_reading(self):
        for path in ("../escape", "/outside-this-workspace"):
            with self.assertRaises(search.SearchError):
                search.workspace_path(path)
        for path in ("../a.md", "/a.md", "a/../a.md", "./a.md", "a//b.md", "a\\b.md", ".hidden/a.md"):
            with self.subTest(path=path):
                index = {"format": search.FORMAT, "documents": [
                    {"path": path, "sha256": search.digest(b"ZTO"), "text": "ZTO"}]}
                with self.assertRaises(search.SearchError):
                    search.validate_index(index)

    def test_duplicate_keys_invalid_hash_unknown_version_and_output_preserved(self):
        filename = self.root / "index.json"
        filename.write_text('{"format":"evidence-search/v1","format":"other","documents":[]}')
        with self.assertRaisesRegex(search.SearchError, "duplicate"):
            search.load_index(filename)
        before = filename.read_bytes()
        with self.assertRaisesRegex(search.SearchError, "already exists"):
            search.write_index(filename, {"format": search.FORMAT, "documents": []})
        self.assertEqual(before, filename.read_bytes())
        filename.write_text('{"format":"future","documents":[]}')
        with self.assertRaisesRegex(search.SearchError, "unsupported"):
            search.load_index(filename)

    def test_empty_and_missing_terms(self):
        self.assertEqual(search.search(search.build_index(self.docs), "ZTO", self.docs)["hits"], [])
        self.write("one.md", "ZTO token\n")
        index = search.build_index(self.docs)
        self.assertEqual(search.search(index, "IMD", self.docs)["hits"], [])
        self.assertEqual(search.search(index, "ZTO IMD", self.docs, require_all=True)["hits"], [])
        for query in ("", "!?#", "x" * 4097):
            with self.assertRaises(search.SearchError):
                search.search(index, query, self.docs)

    def test_overlap_suppression_and_deterministic_ties(self):
        self.write("a.md", "evidence ZTO\n" * 30)
        self.write("b.md", "evidence ZTO\n" * 30)
        index = search.build_index(self.docs)
        first = search.search(index, "ZTO", self.docs, limit=50)
        self.assertEqual(first, search.search(index, "ZTO", self.docs, limit=50))
        for n, hit in enumerate(first["hits"]):
            for other in first["hits"][n + 1:]:
                if hit["path"] == other["path"]:
                    self.assertTrue(hit["line_end"] < other["line_start"] or
                                    other["line_end"] < hit["line_start"])

    def test_resource_and_encoding_limits(self):
        self.write("too-big.txt", "X" * 100)
        with patch.object(search, "MAX_FILE_BYTES", 50):
            with self.assertRaises(search.SearchError):
                search.build_index(self.docs)
        (self.docs / "too-big.txt").write_bytes(b"\xff")
        with self.assertRaisesRegex(search.SearchError, "UTF-8"):
            search.build_index(self.docs)
        (self.docs / "too-big.txt").write_bytes(b"ZTO\x00")
        with self.assertRaisesRegex(search.SearchError, "invalid indexed text"):
            search.build_index(self.docs)

    def test_cli_build_query_and_no_match_status(self):
        self.write("facts.md", "ZTO is Zero To One.\n")
        filename = self.root / "index.json"
        with contextlib.redirect_stdout(io.StringIO()) as output:
            status = search.main(["build", str(self.docs), "--index", str(filename)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["documents"], 1)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            status = search.main(["query", str(self.docs), "ZTO", "--index", str(filename)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["hits"][0]["path"], "facts.md")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            status = search.main(["query", str(self.docs), "absent", "--index", str(filename)])
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue())["hits"], [])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as error:
            status = search.main(["query", str(self.docs), "ZTO", "--index", str(filename), "--limit", "0"])
        self.assertEqual(status, 2)
        self.assertIn("limit", json.loads(error.getvalue())["error"])


if __name__ == "__main__":
    unittest.main()
