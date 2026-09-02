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
import os
import platform
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
    "neovim",
    "zellij",
    "k9s",
    "helm",
    "minikube",
    "oh-my-posh",
    "linecast",
    "zsh-autosuggestions",
    "tmux",
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
    "wget",
    "ca-certificates",
    "gnupg",
    "tmux",
    "unzip",
    "build-essential",
    "fontconfig",
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

    # Neovim (AppImage or apt)
    if not which("nvim"):
        if is_debian_like():
            run(["sudo", "apt-get", "install", "-y", "neovim"], check=False)
        if not which("nvim"):
            log("Installing Neovim AppImage")
            appimage = LOCAL_BIN / "nvim.appimage"
            download(
                "https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.appimage",
                appimage,
            )
            if not DRY_RUN:
                appimage.chmod(appimage.stat().st_mode | stat.S_IEXEC)
                symlink(appimage, LOCAL_BIN / "nvim")

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

    # Docker
    if not which("docker"):
        if is_debian_like():
            log("Installing Docker via get.docker.com")
            run("curl -fsSL https://get.docker.com | sudo sh", shell=True)
            run(["sudo", "usermod", "-aG", "docker", os.getlogin()], check=False)
        else:
            log("Install Docker manually for this distro", "warn")

    # linecast (pip)
    if not which("linecast"):
        pip = which("pip3") or which("pip")
        if pip:
            run([pip, "install", "--user", "linecast"], check=False)
        else:
            log("pip not found — install linecast manually: pip install linecast", "warn")

    # zsh-autosuggestions
    if is_debian_like():
        run(["sudo", "apt-get", "install", "-y", "zsh-autosuggestions"], check=False)

    # Kitty (optional on Linux)
    if not which("kitty") and is_debian_like():
        run(["sudo", "apt-get", "install", "-y", "kitty"], check=False)

    # Nerd Font
    install_nerd_font_linux()


def install_github_release_binary(repo: str, binary: str, asset_contains: str) -> None:
    """Download the latest release asset and extract `binary` into ~/.local/bin."""
    import json

    api = f"https://api.github.com/repos/{repo}/releases/latest"
    log(f"Fetching latest release for {repo}")
    if DRY_RUN:
        log(f"[dry-run] install {binary} from {repo}", "warn")
        return
    with urllib.request.urlopen(api) as resp:
        data = json.load(resp)

    arch = platform.machine().lower()
    if arch in ("x86_64", "amd64"):
        arch_hints = ["x86_64", "amd64"]
    elif arch in ("aarch64", "arm64"):
        arch_hints = ["arm64", "aarch64"]
    else:
        arch_hints = [arch]

    candidates = []
    for a in data.get("assets", []):
        name = a["name"]
        lower = name.lower()
        if asset_contains.lower() not in lower:
            continue
        if not any(h in lower for h in arch_hints):
            continue
        if lower.endswith((".tar.gz", ".tgz", ".zip")) or name == binary:
            candidates.append(a)

    if not candidates:
        log(f"Could not find release asset for {repo} ({binary}, {asset_contains}, {arch})", "warn")
        return

    asset = candidates[0]
    url = asset["browser_download_url"]
    ensure_dir(LOCAL_BIN)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / asset["name"]
        download(url, archive)
        if archive.name.endswith(".zip"):
            run(["unzip", "-o", str(archive), "-d", str(tmp_path)])
        elif archive.name.endswith((".tar.gz", ".tgz")):
            run(["tar", "-xzf", str(archive), "-C", str(tmp_path)])
        else:
            dest = LOCAL_BIN / binary
            shutil.copy2(archive, dest)
            dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
            log(f"installed {dest}", "ok")
            return
        found = list(tmp_path.rglob(binary))
        if not found:
            log(f"Binary {binary} not found in archive", "err")
            return
        dest = LOCAL_BIN / binary
        shutil.copy2(found[0], dest)
        dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
        log(f"installed {dest}", "ok")


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


def link_configs() -> None:
    log("Linking configuration files")
    ensure_dir(LOCAL_BIN)
    ensure_dir(CONFIG_HOME)

    mappings = [
        (REPO_ROOT / "config" / "zsh" / ".zshrc", HOME / ".zshrc"),
        (REPO_ROOT / "config" / "zellij" / "config.kdl", CONFIG_HOME / "zellij" / "config.kdl"),
        (REPO_ROOT / "config" / "zellij" / "themes", CONFIG_HOME / "zellij" / "themes"),
        (REPO_ROOT / "config" / "nvim", CONFIG_HOME / "nvim"),
        (REPO_ROOT / "config" / "kitty", CONFIG_HOME / "kitty"),
        (REPO_ROOT / "config" / "oh-my-posh", CONFIG_HOME / "oh-my-posh"),
        (REPO_ROOT / "config" / "tmux" / "tmux.conf", CONFIG_HOME / "tmux" / "tmux.conf"),
        (REPO_ROOT / "bin" / "weather.sh", LOCAL_BIN / "weather.sh"),
    ]

    for src, dest in mappings:
        if not src.exists():
            log(f"missing source {src}", "warn")
            continue
        symlink(src, dest)

    # k9s skin (keep skins dir; don't replace whole k9s config)
    skin_src = REPO_ROOT / "config" / "k9s" / "skins" / "catppuccin-mocha.yaml"
    skin_dest = CONFIG_HOME / "k9s" / "skins" / "catppuccin-mocha.yaml"
    symlink(skin_src, skin_dest)

    if not DRY_RUN:
        weather = LOCAL_BIN / "weather.sh"
        if weather.exists():
            weather.chmod(weather.stat().st_mode | stat.S_IEXEC)


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
