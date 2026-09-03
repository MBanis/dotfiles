#!/usr/bin/env python3
"""Unit tests for GitHub release asset selection helpers.

Strategy:
- Unit-test pure helpers in install.py (asset filtering, scoring, binary lookup).
- Integration/e2e: Debian Docker smoke test via test/smoke-test.sh.
- Coverage target: at least 80% for the helpers under test.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import install


class SelectReleaseAssetTests(unittest.TestCase):
    def test_prefers_non_polyfilled_tarball(self) -> None:
        assets = [
            {"name": "fastfetch-linux-aarch64-polyfilled.tar.gz"},
            {"name": "fastfetch-linux-aarch64.tar.gz"},
            {"name": "fastfetch-linux-aarch64.deb"},
        ]
        chosen = install.select_release_asset(
            assets,
            binary="fastfetch",
            asset_contains="linux",
            machine="aarch64",
        )
        assert chosen is not None
        self.assertEqual(chosen["name"], "fastfetch-linux-aarch64.tar.gz")

    def test_accepts_bare_fx_binary(self) -> None:
        assets = [
            {"name": "fx_linux_arm64"},
            {"name": "fx_linux_amd64"},
            {"name": "fx_darwin_arm64"},
        ]
        chosen = install.select_release_asset(
            assets,
            binary="fx",
            asset_contains="linux",
            machine="aarch64",
        )
        assert chosen is not None
        self.assertEqual(chosen["name"], "fx_linux_arm64")

    def test_skips_checksum_and_package_files(self) -> None:
        assets = [
            {"name": "tool_linux_amd64.sha256"},
            {"name": "tool_linux_amd64.deb"},
            {"name": "tool_linux_amd64.tar.gz"},
        ]
        chosen = install.select_release_asset(
            assets,
            binary="tool",
            asset_contains="linux",
            machine="x86_64",
        )
        assert chosen is not None
        self.assertEqual(chosen["name"], "tool_linux_amd64.tar.gz")


class FindBinaryTests(unittest.TestCase):
    def test_ignores_directory_named_like_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            share = root / "usr" / "share" / "fastfetch"
            share.mkdir(parents=True)
            (share / "presets").mkdir()
            binary = root / "usr" / "bin" / "fastfetch"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\n")
            found = install.find_binary_in_extract_dir(root, "fastfetch")
            self.assertEqual(found, binary)

    def test_returns_none_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(install.find_binary_in_extract_dir(Path(tmp), "missing"))


class ArchHintsTests(unittest.TestCase):
    def test_arm_and_x86_aliases(self) -> None:
        self.assertEqual(install.arch_hints_for("aarch64"), ["arm64", "aarch64"])
        self.assertEqual(install.arch_hints_for("x86_64"), ["x86_64", "amd64"])


if __name__ == "__main__":
    unittest.main()
