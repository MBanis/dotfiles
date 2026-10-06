#!/usr/bin/env python3
"""Unit tests for removal of obscure package install paths.

Strategy:
- Unit-test install_zellij_plugins and link_configs after sshm / zextract /
  agent-activity / Cursor-hooks removal (mocked filesystem + download).
- Assert install_sshm and link_cursor_hooks are gone from the installer API.
- Integration/e2e: Debian Docker smoke test via test/smoke-test.sh.
- Coverage target: at least 80% for the helpers under test.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import install


class InstallerApiRemovalTests(unittest.TestCase):
    def test_install_sshm_removed(self) -> None:
        self.assertFalse(hasattr(install, "install_sshm"))

    def test_link_cursor_hooks_removed(self) -> None:
        self.assertFalse(hasattr(install, "link_cursor_hooks"))

    def test_linecast_and_markdownlint_helpers_removed(self) -> None:
        for name in (
            "install_linecast",
            "install_markdownlint_cli2",
            "ensure_npm",
            "_pip_available",
            "python_version_tuple",
        ):
            self.assertFalse(hasattr(install, name), name)

    def test_brew_and_apt_lists_drop_removed_packages(self) -> None:
        self.assertNotIn("linecast", install.BREW_FORMULAE)
        self.assertNotIn("markdownlint-cli2", install.BREW_FORMULAE)
        self.assertNotIn("nodejs", install.APT_PACKAGES)
        self.assertNotIn("npm", install.APT_PACKAGES)
        self.assertNotIn("python3-pip", install.APT_PACKAGES)
        self.assertNotIn("python3-venv", install.APT_PACKAGES)

    def test_summary_tools_drop_linecast_and_markdownlint(self) -> None:
        # print_summary builds its list inline; assert via a dry run of the list
        # by inspecting the source constants that feed package installs.
        self.assertNotIn("linecast", install.BREW_FORMULAE)
        with mock.patch.object(install, "which", return_value=None), mock.patch(
            "builtins.print"
        ) as print_mock:
            install.print_summary("linux")
        printed = " ".join(str(c.args[0]) if c.args else "" for c in print_mock.call_args_list)
        self.assertNotIn("linecast", printed)
        self.assertNotIn("markdownlint", printed)
        self.assertNotIn("weather", printed)


class InstallZellijPluginsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.plugin_dir = self.root / ".config" / "zellij" / "plugins"
        install.DRY_RUN = False

    def tearDown(self) -> None:
        install.DRY_RUN = False
        self._tmpdir.cleanup()

    def test_downloads_only_zjstatus(self) -> None:
        downloaded: list[tuple[str, Path]] = []

        def fake_download(url: str, dest: Path) -> None:
            downloaded.append((url, dest))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"wasm")

        with (
            mock.patch.object(install, "CONFIG_HOME", self.root / ".config"),
            mock.patch.object(install, "download", side_effect=fake_download),
        ):
            install.install_zellij_plugins()

        self.assertEqual(len(downloaded), 1)
        url, dest = downloaded[0]
        self.assertIn("dj95/zjstatus", url)
        self.assertEqual(dest.name, "zjstatus.wasm")
        self.assertTrue((self.plugin_dir / "zjstatus.wasm").is_file())
        self.assertFalse((self.plugin_dir / "zextract.wasm").exists())
        self.assertFalse((self.plugin_dir / "zellij-agent-activity.wasm").exists())

    def test_skips_download_when_zjstatus_present(self) -> None:
        self.plugin_dir.mkdir(parents=True)
        existing = self.plugin_dir / "zjstatus.wasm"
        existing.write_bytes(b"existing")
        with (
            mock.patch.object(install, "CONFIG_HOME", self.root / ".config"),
            mock.patch.object(install, "download") as download_mock,
        ):
            install.install_zellij_plugins()
        download_mock.assert_not_called()
        self.assertEqual(existing.read_bytes(), b"existing")


class LinkConfigsNoHooksTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        # Minimal tree so link_configs can run without missing-source noise for
        # the paths we assert on; other sources may warn and continue.
        (self.repo / "config" / "cursor" / "rules").mkdir(parents=True)
        (self.repo / "config" / "cursor" / "rules" / "example.mdc").write_text(
            "---\ndescription: test\n---\n",
            encoding="utf-8",
        )
        install.DRY_RUN = False

    def tearDown(self) -> None:
        install.DRY_RUN = False
        self._tmpdir.cleanup()

    def test_link_configs_places_rules_not_hooks(self) -> None:
        placed: list[tuple[Path, Path]] = []

        def fake_place(src: Path, dest: Path) -> None:
            placed.append((src, dest))

        env = {k: v for k, v in install.os.environ.items() if k != "USERPROFILE"}
        with (
            mock.patch.object(install, "REPO_ROOT", self.repo),
            mock.patch.object(install, "HOME", self.home),
            mock.patch.object(install, "CONFIG_HOME", self.home / ".config"),
            mock.patch.object(install, "LOCAL_BIN", self.home / ".local" / "bin"),
            mock.patch.object(install, "place_config", side_effect=fake_place),
            mock.patch.object(install, "ensure_executable"),
            mock.patch.object(install.os, "environ", env),
        ):
            install.link_configs()

        dest_names = {str(dest) for _, dest in placed}
        self.assertTrue(any(str(dest).endswith(".cursor/rules/example.mdc") for _, dest in placed))
        self.assertFalse(any("hooks.json" in name for name in dest_names))
        self.assertFalse(any("zellij-agent-activity-cursor.sh" in name for name in dest_names))
        self.assertFalse(any("weather.sh" in name for name in dest_names))


class InstallPackagesNoSshmTests(unittest.TestCase):
    def test_install_packages_skip_pkgs_does_not_require_sshm(self) -> None:
        install.SKIP_PKGS = True
        try:
            with mock.patch.object(install, "log") as log_mock:
                install.install_packages("linux")
            messages = [call.args[0] for call in log_mock.call_args_list if call.args]
            self.assertTrue(any("Skipping package installs" in msg for msg in messages))
        finally:
            install.SKIP_PKGS = False

    def test_install_packages_macos_does_not_call_sshm(self) -> None:
        """When packages run, sshm must not be invoked (function removed)."""
        install.SKIP_PKGS = False
        called: list[str] = []

        def track(name: str):
            def _inner(*_a, **_k):
                called.append(name)

            return _inner

        with (
            mock.patch.object(install, "ensure_dir"),
            mock.patch.object(install, "ensure_homebrew", side_effect=track("brew")),
            mock.patch.object(install, "brew_install", side_effect=track("brew_install")),
            mock.patch.object(install, "install_oh_my_zsh", side_effect=track("omz")),
            mock.patch.object(install, "install_tmux_catppuccin", side_effect=track("tmux")),
            mock.patch.object(install, "install_zellij_plugins", side_effect=track("zellij")),
        ):
            install.install_packages("macos")

        self.assertIn("zellij", called)
        self.assertNotIn("sshm", called)
        self.assertFalse(hasattr(install, "install_sshm"))


class LinkCursorRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        install.DRY_RUN = False

    def tearDown(self) -> None:
        install.DRY_RUN = False
        self._tmpdir.cleanup()

    def test_warns_when_rules_dir_missing(self) -> None:
        with (
            mock.patch.object(install, "REPO_ROOT", self.repo),
            mock.patch.object(install, "log") as log_mock,
        ):
            install.link_cursor_rules()
        messages = [c.args[0] for c in log_mock.call_args_list if c.args]
        self.assertTrue(any("missing Cursor rules dir" in m for m in messages))

    def test_copies_rules_to_wsl_userprofile(self) -> None:
        rules = self.repo / "config" / "cursor" / "rules"
        rules.mkdir(parents=True)
        (rules / "a.mdc").write_text("x\n", encoding="utf-8")
        win_home = self.root / "winprofile"
        placed: list[Path] = []

        def fake_place(src: Path, dest: Path) -> None:
            placed.append(dest)

        env = dict(install.os.environ)
        env["USERPROFILE"] = str(win_home)
        with (
            mock.patch.object(install, "REPO_ROOT", self.repo),
            mock.patch.object(install, "HOME", self.home),
            mock.patch.object(install, "place_config", side_effect=fake_place),
            mock.patch.object(install, "ensure_dir"),
            mock.patch.object(install.os, "environ", env),
        ):
            install.link_cursor_rules()

        self.assertTrue(any(p == self.home / ".cursor" / "rules" / "a.mdc" for p in placed))
        self.assertTrue(any(p == win_home / ".cursor" / "rules" / "a.mdc" for p in placed))


class InstallPackagesLinuxTests(unittest.TestCase):
    def test_linux_debian_path_skips_sshm(self) -> None:
        install.SKIP_PKGS = False
        called: list[str] = []

        def track(name: str):
            def _inner(*_a, **_k):
                called.append(name)

            return _inner

        with (
            mock.patch.object(install, "ensure_dir"),
            mock.patch.object(install, "is_debian_like", return_value=True),
            mock.patch.object(install, "is_fedora_like", return_value=False),
            mock.patch.object(install, "apt_install", side_effect=track("apt")),
            mock.patch.object(install, "install_linux_binaries", side_effect=track("linux_bins")),
            mock.patch.object(install, "install_oh_my_zsh", side_effect=track("omz")),
            mock.patch.object(install, "install_tmux_catppuccin", side_effect=track("tmux")),
            mock.patch.object(install, "install_zellij_plugins", side_effect=track("zellij")),
        ):
            install.install_packages("linux")

        self.assertEqual(called, ["apt", "linux_bins", "omz", "tmux", "zellij"])
        self.assertNotIn("sshm", called)


if __name__ == "__main__":
    unittest.main()
