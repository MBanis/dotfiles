#!/usr/bin/env python3
"""
dotfiles installer — bootstrap a new macOS, Linux, or WSL machine.

Usage:
  python3 install.py              # full install
  python3 install.py --dry-run    # print actions only
  python3 install.py --skip-pkgs  # configs + shell only
  python3 install.py --configs    # symlink configs only
"""

from __future__ import annotations

import argparse
import getpass
import os
import platform
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent
HOME = Path.home()
CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))
LOCAL_BIN = HOME / ".local" / "bin"
OH_MY_ZSH = HOME / ".oh-my-zsh"

DRY_RUN = False
SKIP_PKGS = False


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

class C:
    OK = "\033[32m"
    WARN = "\033[33m"
    ERR = "\033[31m"
    INFO = "\033[36m"
    DIM = "\033[2m"
    RST = "\033[0m"


def log(msg: str, kind: str = "info") -> None:
    colors = {"info": C.INFO, "ok": C.OK, "warn": C.WARN, "err": C.ERR}
    prefix = {"info": "==>", "ok": "✓", "warn": "!", "err": "✗"}[kind]
    print(f"{colors.get(kind, C.INFO)}{prefix}{C.RST} {msg}")


def run(cmd: list[str] | str, *, check: bool = True, shell: bool = False, env: dict | None = None) -> int:
    display = cmd if isinstance(cmd, str) else " ".join(cmd)
    if DRY_RUN:
        log(f"[dry-run] {display}", "warn")
        return 0
    log(f"{C.DIM}$ {display}{C.RST}")
    result = subprocess.run(cmd, shell=shell, check=False, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {display}")
    return result.returncode


def which(name: str) -> str | None:
    return shutil.which(name)


def current_user() -> str:
    """Resolve the login name without requiring a controlling TTY."""
    for candidate in (
        os.environ.get("USER"),
        os.environ.get("LOGNAME"),
        os.environ.get("USERNAME"),
    ):
        if candidate:
            return candidate
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        return getpass.getuser()


def running_in_container() -> bool:
    return Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()


def ensure_dir(path: Path) -> None:
    if DRY_RUN:
        log(f"[dry-run] mkdir -p {path}", "warn")
        return
    path.mkdir(parents=True, exist_ok=True)


def backup_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    stamp = __import__("datetime").datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(f"{path.name}.bak.{stamp}")
    if DRY_RUN:
        log(f"[dry-run] backup {path} -> {dest}", "warn")
        return
    path.rename(dest)
    log(f"backed up {path} -> {dest}", "warn")


def symlink(src: Path, dest: Path) -> None:
    src = src.resolve()
    dest = dest.expanduser()
    if dest.is_symlink() and dest.resolve() == src:
        log(f"already linked {dest}", "ok")
        return
    ensure_dir(dest.parent)
    if dest.exists() or dest.is_symlink():
        backup_path(dest)
    if DRY_RUN:
        log(f"[dry-run] ln -s {src} {dest}", "warn")
        return
    dest.symlink_to(src)
    log(f"linked {dest} -> {src}", "ok")


def copy_path(src: Path, dest: Path) -> None:
    """Copy a file or directory into place (used in containers to avoid bind-mount EIO)."""
    src = src.resolve()
    dest = dest.expanduser()
    ensure_dir(dest.parent)
    if dest.exists() or dest.is_symlink():
        backup_path(dest)
    if DRY_RUN:
        log(f"[dry-run] cp -a {src} {dest}", "warn")
        return
    if src.is_dir():
        _copytree_resilient(src, dest)
    else:
        _copyfile_resilient(src, dest)
    log(f"copied {dest} <- {src}", "ok")


def _copyfile_resilient(src: Path, dest: Path) -> None:
    """Copy one file. Retry once on transient I/O errors (Docker Desktop / macOS mounts)."""
    last_exc: OSError | None = None
    for _ in range(2):
        try:
            # Read into memory first — avoids some virtiofs EIO cases on macOS bind mounts.
            data = src.read_bytes()
            dest.write_bytes(data)
            shutil.copystat(src, dest, follow_symlinks=True)
            return
        except OSError as exc:
            last_exc = exc
    assert last_exc is not None
    raise last_exc


def _copytree_resilient(src: Path, dest: Path) -> None:
    """Copy a directory tree, skipping files that keep failing with I/O errors."""
    dest.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    for root, dirs, files in os.walk(src):
        root_path = Path(root)
        rel = root_path.relative_to(src)
        target_root = dest / rel
        target_root.mkdir(parents=True, exist_ok=True)
        for name in dirs:
            (target_root / name).mkdir(parents=True, exist_ok=True)
        for name in files:
            s = root_path / name
            d = target_root / name
            try:
                _copyfile_resilient(s, d)
            except OSError as exc:
                failures.append(f"{s}: {exc}")
                log(f"skip copy (I/O error): {s}", "warn")
    if failures and len(failures) == sum(1 for _ in src.rglob("*") if _.is_file()):
        raise OSError(f"Failed to copy any files from {src}")


def place_config(src: Path, dest: Path) -> None:
    """Symlink on hosts; copy inside containers (Docker bind mounts break some readers)."""
    if running_in_container() or os.environ.get("DOTFILES_COPY_CONFIGS") == "1":
        copy_path(src, dest)
    else:
        symlink(src, dest)


def ensure_executable(path: Path) -> None:
    """Set the executable bit when possible. Skip read-only targets quietly."""
    if DRY_RUN or not path.exists():
        return
    try:
        mode = path.stat().st_mode
        if mode & stat.S_IXUSR:
            return
        path.chmod(mode | stat.S_IEXEC)
    except OSError as exc:
        log(f"could not set executable bit on {path}: {exc}", "warn")


def download(url: str, dest: Path) -> None:
    if DRY_RUN:
        log(f"[dry-run] download {url} -> {dest}", "warn")
        return
    ensure_dir(dest.parent)
    log(f"download {url}")
    urllib.request.urlretrieve(url, dest)


def detect_os() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "linux":
        if "microsoft" in platform.release().lower() or Path("/proc/version").exists() and "microsoft" in Path("/proc/version").read_text(errors="ignore").lower():
            return "wsl"
        return "linux"
    raise SystemExit(f"Unsupported OS: {system}")


def is_debian_like() -> bool:
    return Path("/etc/debian_version").exists() or which("apt-get") is not None


def is_fedora_like() -> bool:
    return Path("/etc/fedora-release").exists() or which("dnf") is not None


# ---------------------------------------------------------------------------
# package managers / packages
# ---------------------------------------------------------------------------

BREW_FORMULAE = [
    "zsh",
    "git",
    "curl",
    "jq",
    "neovim",
    "zellij",
    "k9s",
    "helm",
    "minikube",
    "oh-my-posh",
    "linecast",
    "zsh-autosuggestions",
    "tmux",
    "ripgrep",
    "git-delta",
    "glow",
    "zoxide",
    "eza",
    "fzf",
    "fx",
    "fastfetch",
    "cbonsai",
    "btop",
    "markdownlint-cli2",
]

BREW_CASKS = [
    "kitty",
    "docker",  # Docker Desktop on macOS
    "font-jetbrains-mono-nerd-font",
    "font-symbols-only-nerd-font",  # Kitty symbol_map / Neovim icons
]

APT_PACKAGES = [
    "zsh",
    "git",
    "curl",
    "jq",
    "wget",
    "ca-certificates",
    "gnupg",
    "tmux",
    "unzip",
    "build-essential",
    "fontconfig",
    "ripgrep",
    "python3-pip",
    "python3-venv",
]


def ensure_homebrew() -> None:
    if which("brew"):
        log("Homebrew already installed", "ok")
        return
    log("Installing Homebrew")
    install_url = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
    run(f'NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL {install_url})"', shell=True)
    # Apple Silicon path
    for prefix in (Path("/opt/homebrew"), Path("/usr/local")):
        brew = prefix / "bin" / "brew"
        if brew.exists():
            os.environ["PATH"] = f"{brew.parent}:{os.environ.get('PATH', '')}"
            # Persist for this process
            shellenv = subprocess.check_output([str(brew), "shellenv"], text=True)
            for line in shellenv.splitlines():
                if line.startswith("export "):
                    key, _, val = line[len("export "):].partition("=")
                    os.environ[key] = val.strip().strip('"')
            break


def brew_install(pkgs: Iterable[str], *, cask: bool = False) -> None:
    ensure_homebrew()
    brew = which("brew")
    if not brew:
        raise RuntimeError("brew not found after install")
    for pkg in pkgs:
        check_cmd = [brew, "list", "--cask" if cask else "--formula", pkg]
        if subprocess.run(check_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            log(f"brew: {pkg} already installed", "ok")
            continue
        cmd = [brew, "install"]
        if cask:
            cmd.append("--cask")
        cmd.append(pkg)
        rc = run(cmd, check=False)
        if rc != 0:
            log(f"brew install failed for {pkg} (continuing)", "warn")


def apt_install(pkgs: Iterable[str]) -> None:
    run(["sudo", "apt-get", "update"])
    run(["sudo", "apt-get", "install", "-y", *pkgs])


def install_linux_binaries() -> None:
    """Install tools on Linux/WSL via official installers or GitHub releases."""
    # Oh My Posh
    if not which("oh-my-posh"):
        log("Installing oh-my-posh")
        run(
            'curl -s https://ohmyposh.dev/install.sh | bash -s -- -d "$HOME/.local/bin"',
            shell=True,
        )

    # Neovim — Debian/Ubuntu apt is often too old for LazyVim (needs >= 0.8).
    # Prefer the official release tarball into ~/.local over apt / AppImage.
    install_neovim_linux()

    # Zellij
    if not which("zellij"):
        install_github_release_binary("zellij-org/zellij", "zellij", asset_contains="linux")

    # k9s
    if not which("k9s"):
        install_github_release_binary("derailed/k9s", "k9s", asset_contains="Linux")

    # Helm
    if not which("helm"):
        run("curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash", shell=True)

    # Minikube
    if not which("minikube"):
        dest = LOCAL_BIN / "minikube"
        download(
            "https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64",
            dest,
        )
        if not DRY_RUN:
            dest.chmod(dest.stat().st_mode | stat.S_IEXEC)

    # Docker (skip when already inside a container — nested Docker is optional)
    if which("docker"):
        pass
    elif running_in_container():
        log("Skipping Docker install inside a container", "warn")
    elif is_debian_like():
        log("Installing Docker via get.docker.com")
        run("curl -fsSL https://get.docker.com | sudo sh", shell=True)
        run(["sudo", "usermod", "-aG", "docker", current_user()], check=False)
    else:
        log("Install Docker manually for this distro", "warn")

    # linecast — Debian blocks bare pip installs (PEP 668); use a user venv
    install_linecast()

    # zsh-autosuggestions
    if is_debian_like():
        run(["sudo", "apt-get", "install", "-y", "zsh-autosuggestions"], check=False)

    # Kitty (optional on Linux)
    if not which("kitty") and is_debian_like():
        run(["sudo", "apt-get", "install", "-y", "kitty"], check=False)

    # CLI QoL tools (macOS gets these via Homebrew formulae)
    install_cli_qol_linux()

    # Nerd Font
    install_nerd_font_linux()


def install_cli_qol_linux() -> None:
    """Install ripgrep/delta/glow/zoxide/eza on Linux when missing."""
    if is_debian_like():
        # Best-effort apt names; missing packages fall back to GitHub releases.
        apt_bins = {
            "ripgrep": "rg",
            "eza": "eza",
            "zoxide": "zoxide",
            "glow": "glow",
            "git-delta": "delta",
            "fzf": "fzf",
            "fx": "fx",
            "fastfetch": "fastfetch",
            "cbonsai": "cbonsai",
            "btop": "btop",
            "markdownlint-cli2": "markdownlint-cli2",
        }
        needed = [pkg for pkg, binary in apt_bins.items() if not which(binary)]
        if needed:
            apt_install_if_available(needed)

    if not which("zoxide"):
        run('curl -sS https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | bash', shell=True, check=False)

    if not which("eza"):
        install_github_release_binary("eza-community/eza", "eza", asset_contains="linux")

    if not which("delta"):
        install_github_release_binary("dandavison/delta", "delta", asset_contains="unknown-linux")

    if not which("glow"):
        install_github_release_binary("charmbracelet/glow", "glow", asset_contains="Linux")

    if not which("rg"):
        install_github_release_binary("BurntSushi/ripgrep", "rg", asset_contains="unknown-linux")

    if not which("fzf"):
        install_github_release_binary("junegunn/fzf", "fzf", asset_contains="linux")

    if not which("fx"):
        install_github_release_binary("antonmedv/fx", "fx", asset_contains="linux")

    if not which("fastfetch"):
        install_github_release_binary("fastfetch-cli/fastfetch", "fastfetch", asset_contains="linux")

    if not which("btop"):
        install_github_release_binary("aristocratos/btop", "btop", asset_contains="linux")

    if not which("cbonsai"):
        log("cbonsai not found — install from https://gitlab.com/jallbrit/cbonsai", "warn")

    if not which("markdownlint-cli2"):
        if which("npm"):
            run(["npm", "install", "-g", "markdownlint-cli2"], check=False)
        if not which("markdownlint-cli2"):
            log("markdownlint-cli2 not found — LazyVim markdown lint needs it (brew/npm)", "warn")

def apt_package_available(pkg: str) -> bool:
    """Return True when apt-cache knows about a package."""
    if DRY_RUN:
        return True
    if not which("apt-cache"):
        return False
    result = subprocess.run(
        ["apt-cache", "show", pkg],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def apt_install_if_available(pkgs: Iterable[str]) -> None:
    available = [pkg for pkg in pkgs if apt_package_available(pkg)]
    missing = [pkg for pkg in pkgs if pkg not in available]
    for pkg in missing:
        log(f"apt package not available: {pkg} (will try other sources)", "warn")
    if available:
        run(["sudo", "apt-get", "install", "-y", *available], check=False)


def _pip_available() -> bool:
    """True when `python3 -m pip` works."""
    if DRY_RUN:
        return True
    result = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def python_version_tuple() -> tuple[int, int]:
    return sys.version_info.major, sys.version_info.minor


def install_linecast() -> None:
    """Install linecast into a user venv and expose ~/.local/bin/linecast."""
    if which("linecast") or (LOCAL_BIN / "linecast").exists():
        log("linecast already installed", "ok")
        return

    if python_version_tuple() < (3, 10):
        log(
            f"linecast needs Python >= 3.10 (found {sys.version.split()[0]}); skipping",
            "warn",
        )
        return

    if is_debian_like():
        apt_install_if_available(["python3-pip", "python3-venv"])

    if DRY_RUN:
        log("[dry-run] python3 -m venv + pip install linecast", "warn")
        return

    venv_dir = HOME / ".local" / "share" / "linecast-venv"
    venv_python = venv_dir / "bin" / "python"
    venv_linecast = venv_dir / "bin" / "linecast"

    ensure_dir(venv_dir.parent)
    if not venv_python.exists():
        log(f"Creating linecast venv at {venv_dir}")
        rc = run([sys.executable, "-m", "venv", str(venv_dir)], check=False)
        if rc != 0 or not venv_python.exists():
            log("Failed to create linecast venv (is python3-venv installed?)", "err")
            return

    log("Installing linecast into user venv")
    rc = run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "linecast"], check=False)
    if rc != 0 or not venv_linecast.exists():
        log("linecast pip install failed", "err")
        return

    ensure_dir(LOCAL_BIN)
    dest = LOCAL_BIN / "linecast"
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    dest.symlink_to(venv_linecast)
    ensure_executable(dest)
    os.environ["PATH"] = f"{LOCAL_BIN}:{os.environ.get('PATH', '')}"
    log(f"installed {dest} -> {venv_linecast}", "ok")


ARCHIVE_SUFFIXES = (".tar.gz", ".tgz", ".tar.xz", ".txz", ".zip")
SKIP_ASSET_SUFFIXES = (
    ".deb",
    ".rpm",
    ".apk",
    ".exe",
    ".msi",
    ".dmg",
    ".pkg",
    ".sha256",
    ".sha512",
    ".sig",
    ".asc",
    ".txt",
    ".md",
    ".json",
)


def arch_hints_for(machine: str | None = None) -> list[str]:
    arch = (machine or platform.machine()).lower()
    if arch in ("x86_64", "amd64"):
        return ["x86_64", "amd64"]
    if arch in ("aarch64", "arm64"):
        return ["arm64", "aarch64"]
    return [arch]


def is_usable_release_asset(name: str, binary: str) -> bool:
    lower = name.lower()
    if any(lower.endswith(ext) for ext in SKIP_ASSET_SUFFIXES):
        return False
    if any(lower.endswith(ext) for ext in ARCHIVE_SUFFIXES):
        return True
    if name == binary:
        return True
    # Bare binaries such as fx_linux_arm64
    stem = Path(name).name
    return stem.startswith(f"{binary}_") or stem.startswith(f"{binary}-")


def score_release_asset(name: str) -> tuple[int, int, str]:
    """Lower score is better. Prefer plain archives over polyfilled/musl builds."""
    lower = name.lower()
    penalty = 0
    if "polyfilled" in lower:
        penalty += 20
    if "musl" in lower:
        penalty += 10
    if lower.endswith(".zip"):
        penalty += 2
    if lower.endswith((".tar.xz", ".txz")):
        penalty += 1
    if not any(lower.endswith(ext) for ext in ARCHIVE_SUFFIXES):
        # Prefer archives when both exist; bare binaries are fine when alone.
        penalty += 0
    return (penalty, len(name), name)


def select_release_asset(
    assets: list[dict],
    binary: str,
    asset_contains: str,
    machine: str | None = None,
) -> dict | None:
    arch_hints = arch_hints_for(machine)
    candidates = []
    for asset in assets:
        name = asset.get("name", "")
        lower = name.lower()
        if asset_contains.lower() not in lower:
            continue
        if not any(hint in lower for hint in arch_hints):
            continue
        if not is_usable_release_asset(name, binary):
            continue
        candidates.append(asset)
    if not candidates:
        return None
    candidates.sort(key=lambda a: score_release_asset(a["name"]))
    return candidates[0]


def find_binary_in_extract_dir(root: Path, binary: str) -> Path | None:
    matches = [path for path in root.rglob(binary) if path.is_file()]
    if not matches:
        return None
    # Prefer .../bin/<binary> when the archive ships a full prefix tree.
    matches.sort(key=lambda p: (0 if p.parent.name == "bin" else 1, len(p.parts), str(p)))
    return matches[0]


def install_github_release_binary(repo: str, binary: str, asset_contains: str) -> None:
    """Download the latest release asset and extract `binary` into ~/.local/bin."""
    import json

    api = f"https://api.github.com/repos/{repo}/releases/latest"
    log(f"Fetching latest release for {repo}")
    if DRY_RUN:
        log(f"[dry-run] install {binary} from {repo}", "warn")
        return
    try:
        with urllib.request.urlopen(api) as resp:
            data = json.load(resp)
    except Exception as exc:
        log(f"Failed to query releases for {repo}: {exc}", "err")
        return

    asset = select_release_asset(
        data.get("assets", []),
        binary=binary,
        asset_contains=asset_contains,
    )
    if asset is None:
        arch = platform.machine().lower()
        log(f"Could not find release asset for {repo} ({binary}, {asset_contains}, {arch})", "warn")
        return

    url = asset["browser_download_url"]
    ensure_dir(LOCAL_BIN)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / asset["name"]
            download(url, archive)
            lower_name = archive.name.lower()
            if lower_name.endswith(".zip"):
                run(["unzip", "-o", str(archive), "-d", str(tmp_path)])
                source = find_binary_in_extract_dir(tmp_path, binary)
            elif lower_name.endswith((".tar.gz", ".tgz")):
                run(["tar", "-xzf", str(archive), "-C", str(tmp_path)])
                source = find_binary_in_extract_dir(tmp_path, binary)
            elif lower_name.endswith((".tar.xz", ".txz")):
                run(["tar", "-xJf", str(archive), "-C", str(tmp_path)])
                source = find_binary_in_extract_dir(tmp_path, binary)
            else:
                source = archive

            if source is None:
                log(f"Binary {binary} not found in archive", "err")
                return

            dest = LOCAL_BIN / binary
            shutil.copy2(source, dest)
            dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
            log(f"installed {dest}", "ok")
    except Exception as exc:
        log(f"Failed to install {binary} from {repo}: {exc}", "err")


def nvim_version_tuple() -> tuple[int, int, int] | None:
    """Return (major, minor, patch) for the first nvim on PATH, or None."""
    nvim = which("nvim")
    if not nvim:
        return None
    try:
        out = subprocess.check_output([nvim, "--version"], text=True, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        return None
    # First line looks like: NVIM v0.10.2
    first = out.splitlines()[0] if out else ""
    import re

    match = re.search(r"v?(\d+)\.(\d+)\.(\d+)", first)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def nvim_meets_minimum(minimum: tuple[int, int, int] = (0, 9, 0)) -> bool:
    current = nvim_version_tuple()
    return current is not None and current >= minimum


def install_neovim_linux() -> None:
    """Install a LazyVim-capable Neovim from the official release tarball."""
    minimum = (0, 9, 0)
    if nvim_meets_minimum(minimum):
        ver = ".".join(str(p) for p in nvim_version_tuple() or ())
        log(f"Neovim {ver} already meets minimum {'.'.join(map(str, minimum))}", "ok")
        return

    current = nvim_version_tuple()
    if current:
        log(
            f"Neovim {'.'.join(map(str, current))} is too old for LazyVim; installing upstream release",
            "warn",
        )
    else:
        log("Installing Neovim from upstream release")

    if DRY_RUN:
        log("[dry-run] install neovim release tarball into ~/.local", "warn")
        return

    arch = platform.machine().lower()
    if arch in ("x86_64", "amd64"):
        asset = "nvim-linux-x86_64.tar.gz"
        folder = "nvim-linux-x86_64"
    elif arch in ("aarch64", "arm64"):
        asset = "nvim-linux-arm64.tar.gz"
        folder = "nvim-linux-arm64"
    else:
        log(f"Unsupported arch for Neovim release tarball: {arch}", "err")
        return

    url = f"https://github.com/neovim/neovim/releases/latest/download/{asset}"
    ensure_dir(LOCAL_BIN)
    local_root = HOME / ".local"
    ensure_dir(local_root)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / asset
        download(url, archive)
        run(["tar", "-xzf", str(archive), "-C", str(tmp_path)])
        extracted = tmp_path / folder
        if not extracted.is_dir():
            # Fallback: find the extracted top-level directory
            dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
            if not dirs:
                log("Neovim archive did not contain an install directory", "err")
                return
            extracted = dirs[0]

        # Merge bin/lib/share into ~/.local so ~/.local/bin/nvim is on PATH
        for sub in ("bin", "lib", "share"):
            src = extracted / sub
            if not src.exists():
                continue
            dest = local_root / sub
            ensure_dir(dest)
            for item in src.iterdir():
                target = dest / item.name
                if target.exists() or target.is_symlink():
                    if target.is_dir() and not target.is_symlink():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                if item.is_dir():
                    shutil.copytree(item, target, symlinks=True)
                else:
                    shutil.copy2(item, target)

    nvim_bin = LOCAL_BIN / "nvim"
    ensure_executable(nvim_bin)
    os.environ["PATH"] = f"{LOCAL_BIN}:{os.environ.get('PATH', '')}"
    if nvim_meets_minimum(minimum):
        ver = ".".join(str(p) for p in nvim_version_tuple() or ())
        log(f"installed Neovim {ver} -> {nvim_bin}", "ok")
    else:
        log("Neovim install finished but version check still failed", "err")


def install_sshm() -> None:
    """Install Gu1llaum-3/sshm SSH manager TUI."""
    if which("sshm"):
        log("sshm already installed", "ok")
        return
    if which("go"):
        env = os.environ.copy()
        env["GOBIN"] = str(LOCAL_BIN)
        run(["go", "install", "github.com/Gu1llaum-3/sshm@latest"], check=False, env=env)
        if which("sshm") or (LOCAL_BIN / "sshm").exists():
            log("sshm installed via go", "ok")
            return
    # Release assets look like sshm_Darwin_arm64.tar.gz / sshm_Linux_x86_64.tar.gz
    os_name = detect_os()
    needle = "Darwin" if os_name == "macos" else "Linux"
    install_github_release_binary("Gu1llaum-3/sshm", "sshm", asset_contains=needle)


def install_nerd_font_linux() -> None:
    fonts_dir = HOME / ".local" / "share" / "fonts"
    markers = [
        fonts_dir / "JetBrainsMonoNerdFontMono-Regular.ttf",
        fonts_dir / "JetBrainsMonoNerdFont-Regular.ttf",
        fonts_dir / "SymbolsNerdFontMono-Regular.ttf",
    ]
    if all(
        (fonts_dir / name).exists()
        for name in (
            "JetBrainsMonoNerdFontMono-Regular.ttf",
            "SymbolsNerdFontMono-Regular.ttf",
        )
    ) or (
        (fonts_dir / "JetBrainsMonoNerdFont-Regular.ttf").exists()
        and (fonts_dir / "SymbolsNerdFontMono-Regular.ttf").exists()
    ):
        log("JetBrainsMono + Symbols Nerd Fonts already present", "ok")
        return
    log("Installing JetBrainsMono + Symbols Nerd Fonts")
    if DRY_RUN:
        return
    ensure_dir(fonts_dir)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for url, name in (
            (
                "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip",
                "JetBrainsMono.zip",
            ),
            (
                "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip",
                "NerdFontsSymbolsOnly.zip",
            ),
        ):
            zip_path = tmp_path / name
            download(url, zip_path)
            run(["unzip", "-o", str(zip_path), "-d", str(fonts_dir)], check=False)
    if which("fc-cache"):
        run(["fc-cache", "-f"], check=False)


# ---------------------------------------------------------------------------
# shell / plugins / configs
# ---------------------------------------------------------------------------

def install_oh_my_zsh() -> None:
    if OH_MY_ZSH.exists():
        log("Oh My Zsh already installed", "ok")
    else:
        log("Installing Oh My Zsh")
        env = os.environ.copy()
        env["RUNZSH"] = "no"
        env["CHSH"] = "no"
        run(
            'sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"',
            shell=True,
            env=env,
        )

    # OMZ custom plugin (required for plugins=(... zsh-autosuggestions))
    zsh_custom = Path(os.environ.get("ZSH_CUSTOM", OH_MY_ZSH / "custom"))
    autosuggest = zsh_custom / "plugins" / "zsh-autosuggestions"
    if autosuggest.exists():
        log("zsh-autosuggestions plugin already present", "ok")
        if not DRY_RUN:
            run(["git", "-C", str(autosuggest), "pull", "--ff-only"], check=False)
    else:
        ensure_dir(autosuggest.parent)
        run(
            [
                "git",
                "clone",
                "--depth=1",
                "https://github.com/zsh-users/zsh-autosuggestions",
                str(autosuggest),
            ]
        )

    # Make zsh default when possible
    zsh = which("zsh")
    if zsh and os.environ.get("SHELL") != zsh:
        log(f"Default shell is {os.environ.get('SHELL')}; to switch: chsh -s {zsh}", "warn")


def install_tmux_catppuccin() -> None:
    plugin = CONFIG_HOME / "tmux" / "plugins" / "catppuccin"
    if plugin.exists():
        log("tmux catppuccin already present", "ok")
        return
    ensure_dir(plugin.parent)
    run(
        [
            "git",
            "clone",
            "--depth=1",
            "https://github.com/catppuccin/tmux.git",
            str(plugin),
        ]
    )


def install_zellij_plugins() -> None:
    plugin_dir = CONFIG_HOME / "zellij" / "plugins"
    ensure_dir(plugin_dir)

    plugins = {
        "zjstatus.wasm": "https://github.com/dj95/zjstatus/releases/latest/download/zjstatus.wasm",
        "zextract.wasm": "https://github.com/codingfragments/zellij-zextract/releases/latest/download/zextract.wasm",
        "zellij-agent-activity.wasm": "https://github.com/vmaerten/zellij-agent-activity/releases/latest/download/zellij-agent-activity.wasm",
    }

    for name, url in plugins.items():
        dest = plugin_dir / name
        if dest.exists():
            log(f"zellij plugin already present: {name}", "ok")
            continue
        download(url, dest)


def link_configs() -> None:
    mode = "copying" if (running_in_container() or os.environ.get("DOTFILES_COPY_CONFIGS") == "1") else "linking"
    log(f"{mode.capitalize()} configuration files")
    ensure_dir(LOCAL_BIN)
    ensure_dir(CONFIG_HOME)

    mappings = [
        (REPO_ROOT / "config" / "zsh" / ".zshrc", HOME / ".zshrc"),
        (REPO_ROOT / "config" / "git" / "config", CONFIG_HOME / "git" / "config"),
        (REPO_ROOT / "config" / "zellij" / "config.kdl", CONFIG_HOME / "zellij" / "config.kdl"),
        (REPO_ROOT / "config" / "zellij" / "themes", CONFIG_HOME / "zellij" / "themes"),
        (REPO_ROOT / "config" / "zellij" / "layouts", CONFIG_HOME / "zellij" / "layouts"),
        (REPO_ROOT / "config" / "nvim", CONFIG_HOME / "nvim"),
        (REPO_ROOT / "config" / "kitty", CONFIG_HOME / "kitty"),
        (REPO_ROOT / "config" / "oh-my-posh", CONFIG_HOME / "oh-my-posh"),
        (REPO_ROOT / "config" / "btop", CONFIG_HOME / "btop"),
        (REPO_ROOT / "config" / "tmux" / "tmux.conf", CONFIG_HOME / "tmux" / "tmux.conf"),
        (REPO_ROOT / "bin" / "weather.sh", LOCAL_BIN / "weather.sh"),
    ]

    for src, dest in mappings:
        if not src.exists():
            log(f"missing source {src}", "warn")
            continue
        place_config(src, dest)

    # k9s skin (keep skins dir; don't replace whole k9s config)
    skin_src = REPO_ROOT / "config" / "k9s" / "skins" / "catppuccin-mocha.yaml"
    skin_dest = CONFIG_HOME / "k9s" / "skins" / "catppuccin-mocha.yaml"
    place_config(skin_src, skin_dest)

    if not DRY_RUN:
        ensure_executable(LOCAL_BIN / "weather.sh")

    link_cursor_rules()
    link_cursor_hooks()


def cursor_rule_dest_dirs() -> list[Path]:
    """User-level Cursor rules dirs (apply across all projects for this account)."""
    dests = [HOME / ".cursor" / "rules"]
    # WSL: Windows Cursor reads %USERPROFILE%\.cursor\rules
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        dests.append(Path(userprofile) / ".cursor" / "rules")
    return dests


def link_cursor_rules() -> None:
    src_dir = REPO_ROOT / "config" / "cursor" / "rules"
    if not src_dir.is_dir():
        log(f"missing Cursor rules dir {src_dir}", "warn")
        return
    log("Placing Cursor user rules (~/.cursor/rules)")
    for dest_dir in cursor_rule_dest_dirs():
        ensure_dir(dest_dir)
        for src in sorted(src_dir.glob("*.mdc")):
            place_config(src, dest_dir / src.name)


def link_cursor_hooks() -> None:
    cursor_home = HOME / ".cursor"
    hooks_dir = cursor_home / "hooks"
    ensure_dir(cursor_home)
    ensure_dir(hooks_dir)

    place_config(REPO_ROOT / "config" / "cursor" / "hooks.json", cursor_home / "hooks.json")
    place_config(
        REPO_ROOT / "config" / "cursor" / "hooks" / "zellij-agent-activity-cursor.sh",
        hooks_dir / "zellij-agent-activity-cursor.sh",
    )

    if not DRY_RUN:
        ensure_executable(hooks_dir / "zellij-agent-activity-cursor.sh")


def install_packages(os_name: str) -> None:
    if SKIP_PKGS:
        log("Skipping package installs (--skip-pkgs)", "warn")
        return

    log(f"Installing packages for {os_name}")
    ensure_dir(LOCAL_BIN)

    if os_name == "macos":
        ensure_homebrew()
        brew_install(BREW_FORMULAE)
        brew_install(BREW_CASKS, cask=True)
    else:
        if is_debian_like():
            apt_install(APT_PACKAGES)
        elif is_fedora_like():
            run(["sudo", "dnf", "install", "-y", "zsh", "git", "curl", "tmux", "neovim"], check=False)
        else:
            log("Unknown Linux distro — installing binaries only", "warn")
        install_linux_binaries()

    install_sshm()
    install_oh_my_zsh()
    install_tmux_catppuccin()
    install_zellij_plugins()


def print_summary(os_name: str) -> None:
    tools = [
        "zsh",
        "nvim",
        "zellij",
        "oh-my-posh",
        "k9s",
        "helm",
        "docker",
        "minikube",
        "linecast",
        "sshm",
        "kitty",
        "rg",
        "jq",
        "delta",
        "glow",
        "zoxide",
        "eza",
        "fzf",
        "fx",
        "fastfetch",
        "btop",
        "cbonsai",
        "markdownlint-cli2",
    ]
    print()
    log("Install summary")
    for t in tools:
        path = which(t)
        status = f"{C.OK}found{C.RST} ({path})" if path else f"{C.WARN}missing{C.RST}"
        print(f"  {t:12} {status}")
    weather = LOCAL_BIN / "weather.sh"
    print(f"  {'weather':12} {C.OK + 'linked' + C.RST if weather.exists() or DRY_RUN else C.WARN + 'missing' + C.RST}")
    print()
    log(f"OS: {os_name} | repo: {REPO_ROOT}")
    log("Open a new terminal (or `exec zsh`) to load the new shell config.", "ok")
    log("First `nvim` launch will install LazyVim plugins (needs network).", "ok")
    if os_name in ("linux", "wsl") and which("docker"):
        log("You may need to log out/in for Docker group membership.", "warn")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bootstrap dotfiles on macOS / Linux / WSL")
    p.add_argument("--dry-run", action="store_true", help="Print actions without changing the system")
    p.add_argument("--skip-pkgs", action="store_true", help="Skip package installs")
    p.add_argument("--configs", action="store_true", help="Only symlink configs / scripts")
    return p.parse_args()


def main() -> int:
    global DRY_RUN, SKIP_PKGS
    args = parse_args()
    DRY_RUN = args.dry_run
    SKIP_PKGS = args.skip_pkgs

    # Prefer user-local binaries for subsequent which() checks
    os.environ["PATH"] = f"{LOCAL_BIN}:{os.environ.get('PATH', '')}"

    os_name = detect_os()
    log(f"dotfiles bootstrap ({os_name})")
    log(f"repo: {REPO_ROOT}")

    try:
        if args.configs:
            link_configs()
        else:
            install_packages(os_name)
            link_configs()
        print_summary(os_name)
    except KeyboardInterrupt:
        log("Interrupted", "warn")
        return 130
    except Exception as exc:
        log(str(exc), "err")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
