#!/usr/bin/env python3
"""Unit tests for config placement (always copy, never symlink).

Strategy:
- Unit-test place_config / copy_path behavior with a temporary home.
- Integration/e2e: Debian Docker smoke test via test/smoke-test.sh.
- Coverage target: at least 80% for place_config and copy_path paths under test.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import install


class PlaceConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.src = self.root / "repo" / "config.kdl"
        self.dest = self.root / "home" / ".config" / "zellij" / "config.kdl"
        self.src.parent.mkdir(parents=True)
        self.src.write_text('keybinds {}\n', encoding="utf-8")
        install.DRY_RUN = False

    def tearDown(self) -> None:
        install.DRY_RUN = False
        self._tmpdir.cleanup()

    def test_place_config_copies_file_not_symlink(self) -> None:
        install.place_config(self.src, self.dest)
        self.assertTrue(self.dest.is_file())
        self.assertFalse(self.dest.is_symlink())
        self.assertEqual(self.dest.read_text(encoding="utf-8"), 'keybinds {}\n')
        self.assertEqual(self.src.read_text(encoding="utf-8"), self.dest.read_text(encoding="utf-8"))

    def test_place_config_replaces_existing_symlink_with_copy(self) -> None:
        self.dest.parent.mkdir(parents=True)
        other = self.root / "other.kdl"
        other.write_text("old\n", encoding="utf-8")
        self.dest.symlink_to(other)

        install.place_config(self.src, self.dest)

        self.assertTrue(self.dest.is_file())
        self.assertFalse(self.dest.is_symlink())
        self.assertEqual(self.dest.read_text(encoding="utf-8"), 'keybinds {}\n')
        backups = list(self.dest.parent.glob("config.kdl.bak.*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].is_symlink())

    def test_place_config_copies_directory_tree(self) -> None:
        src_dir = self.root / "repo" / "themes"
        dest_dir = self.root / "home" / ".config" / "zellij" / "themes"
        (src_dir / "nested").mkdir(parents=True)
        (src_dir / "a.kdl").write_text("a\n", encoding="utf-8")
        (src_dir / "nested" / "b.kdl").write_text("b\n", encoding="utf-8")

        install.place_config(src_dir, dest_dir)

        self.assertTrue(dest_dir.is_dir())
        self.assertFalse(dest_dir.is_symlink())
        self.assertEqual((dest_dir / "a.kdl").read_text(encoding="utf-8"), "a\n")
        self.assertEqual((dest_dir / "nested" / "b.kdl").read_text(encoding="utf-8"), "b\n")

    def test_place_config_always_copies_even_outside_container(self) -> None:
        with mock.patch.object(install, "running_in_container", return_value=False):
            install.place_config(self.src, self.dest)
        self.assertTrue(self.dest.is_file())
        self.assertFalse(self.dest.is_symlink())

    def test_place_config_dry_run_does_not_write(self) -> None:
        install.DRY_RUN = True
        try:
            install.place_config(self.src, self.dest)
        finally:
            install.DRY_RUN = False
        self.assertFalse(self.dest.exists())


if __name__ == "__main__":
    unittest.main()
