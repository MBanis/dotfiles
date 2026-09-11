#!/usr/bin/env python3
"""Unit tests for markdownlint-cli2 install helpers.

Strategy:
- Unit-test ensure_npm / install_markdownlint_cli2 with mocks (no network).
- Integration/e2e: Debian Docker smoke test via test/smoke-test.sh.
- Coverage target: at least 80% for these helpers under test.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

import install


class EnsureNpmTests(unittest.TestCase):
    def test_returns_true_when_npm_present(self) -> None:
        with mock.patch.object(install, "which", side_effect=lambda n: "/usr/bin/npm" if n == "npm" else None):
            self.assertTrue(install.ensure_npm())

    def test_installs_nodejs_npm_on_debian_when_missing(self) -> None:
        calls: list[list[str]] = []

        def fake_which(name: str) -> str | None:
            # After apt install, pretend npm appears.
            if name == "npm" and calls:
                return "/usr/bin/npm"
            return None

        with (
            mock.patch.object(install, "which", side_effect=fake_which),
            mock.patch.object(install, "is_debian_like", return_value=True),
            mock.patch.object(install, "apt_install_if_available", side_effect=lambda pkgs: calls.append(list(pkgs))),
        ):
            self.assertTrue(install.ensure_npm())
        self.assertEqual(calls, [["nodejs", "npm"]])

    def test_returns_false_when_npm_unavailable(self) -> None:
        with (
            mock.patch.object(install, "which", return_value=None),
            mock.patch.object(install, "is_debian_like", return_value=False),
        ):
            self.assertFalse(install.ensure_npm())


class InstallMarkdownlintCli2Tests(unittest.TestCase):
    def test_skips_when_already_on_path(self) -> None:
        with (
            mock.patch.object(install, "which", return_value="/usr/bin/markdownlint-cli2"),
            mock.patch.object(install, "run") as run_mock,
        ):
            install.install_markdownlint_cli2()
            run_mock.assert_not_called()

    def test_npm_installs_into_local_prefix(self) -> None:
        which_map = {"npm": "/usr/bin/npm"}

        def fake_which(name: str) -> str | None:
            return which_map.get(name)

        run_calls: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            run_calls.append(cmd if isinstance(cmd, list) else [cmd])
            which_map["markdownlint-cli2"] = str(install.LOCAL_BIN / "markdownlint-cli2")
            return 0

        with (
            mock.patch.object(install, "which", side_effect=fake_which),
            mock.patch.object(install, "ensure_npm", return_value=True),
            mock.patch.object(install, "ensure_dir"),
            mock.patch.object(install, "run", side_effect=fake_run),
            mock.patch.object(Path, "exists", return_value=False),
        ):
            install.install_markdownlint_cli2()

        self.assertTrue(run_calls)
        self.assertEqual(
            run_calls[0],
            ["npm", "install", "-g", "--prefix", str(install.HOME / ".local"), "markdownlint-cli2"],
        )


if __name__ == "__main__":
    unittest.main()
