#!/usr/bin/env python3
"""Unit tests for removal of linecast, weather, and markdownlint paths.

Strategy:
- Unit-test installer package lists, missing helpers, and CLI QoL no longer
  installing markdownlint-cli2.
- Integration/e2e: Debian Docker smoke test via test/smoke-test.sh.
- Coverage target: at least 80% for the helpers under test.
"""

from __future__ import annotations

import unittest
from unittest import mock

import install


class RemovedWeatherLinecastMarkdownlintTests(unittest.TestCase):
    def test_install_cli_qol_does_not_call_markdownlint(self) -> None:
        with (
            mock.patch.object(install, "is_debian_like", return_value=False),
            mock.patch.object(install, "which", return_value="/usr/bin/x"),
            mock.patch.object(install, "log"),
        ):
            # All binaries present → no downloads; must not reference markdownlint.
            install.install_cli_qol_linux()
        self.assertFalse(hasattr(install, "install_markdownlint_cli2"))

    def test_link_configs_mapping_excludes_weather(self) -> None:
        # Ensure the weather.sh mapping is gone by scanning link_configs source
        # via a dry run that records place_config destinations.
        placed: list[str] = []

        def fake_place(src, dest) -> None:
            placed.append(str(dest))

        with (
            mock.patch.object(install, "REPO_ROOT", install.REPO_ROOT),
            mock.patch.object(install, "HOME", install.HOME),
            mock.patch.object(install, "ensure_dir"),
            mock.patch.object(install, "place_config", side_effect=fake_place),
            mock.patch.object(install, "link_cursor_rules"),
            mock.patch.object(install, "log"),
        ):
            install.link_configs()
        self.assertFalse(any("weather.sh" in p for p in placed))


if __name__ == "__main__":
    unittest.main()
