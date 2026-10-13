#!/usr/bin/env python3
"""Verify archive preservation independently from Android tooling."""
from pathlib import Path
import tempfile
import unittest

from archive_version import save_archive


class ArchiveTest(unittest.TestCase):
    def test_repeat_is_read_only_and_different_build_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="terminal-archive-test-") as directory:
            root = Path(directory)
            source = root / "artifact.apk"
            source.write_bytes(b"test build")
            target = root / "versions/0.3.0"
            arguments = (target, {"face.apk": source}, "0.3.0", 3, "dev.test")
            self.assertTrue(save_archive(*arguments))
            manifest = (target / "manifest.json").read_bytes()
            self.assertFalse(save_archive(*arguments))
            self.assertEqual((target / "manifest.json").read_bytes(), manifest)
            source.write_bytes(b"different build")
            with self.assertRaises(ValueError):
                save_archive(*arguments)
            self.assertEqual((target / "face.apk").read_bytes(), b"test build")

    def test_archive_corruption_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="terminal-archive-test-") as directory:
            root = Path(directory)
            source = root / "artifact.apk"
            source.write_bytes(b"test build")
            target = root / "versions/0.3.0"
            arguments = (target, {"face.apk": source}, "0.3.0", 3, "dev.test")
            save_archive(*arguments)
            (target / "face.apk").write_bytes(b"corrupted")
            with self.assertRaises(ValueError):
                save_archive(*arguments)


if __name__ == "__main__":
    unittest.main(verbosity=2)
