# Dotfiles

Cross-platform bootstrap for **macOS**, **Linux**, and **WSL**, with a Catppuccin Mocha theme throughout.

## Quick start

```bash
cd ~/Documents/Projects/dotfiles
python3 install.py
```

Then open a new terminal (or run `exec zsh`). The first `nvim` launch installs LazyVim plugins.

### Options

| Flag | Meaning |
|------|---------|
| `--dry-run` | Print actions only |
| `--skip-pkgs` | Configs + shell plugins only (no package installs) |
| `--configs` | Symlink configs / `weather.sh` only |

## What gets installed

| Tool | Notes |
|------|--------|
| **zsh** + Oh My Zsh | Base shell |
| **Oh My Posh** | Prompt — Catppuccin Mocha |
| **zsh-autosuggestions** | Fish-like suggestions |
| **zsh-autocomplete** | Real-time completion (marlonrichert) |
| **zellij** | Multiplexer — Catppuccin Mocha |
| **neovim** + LazyVim | Catppuccin Mocha + markdown preview (`<leader>mp`) |
| **kitty** | Terminal — Catppuccin Mocha |
| **sshm** | [Gu1llaum-3/sshm](https://github.com/Gu1llaum-3/sshm) SSH TUI |
| **k9s** | Skin: `catppuccin-mocha` |
| **helm**, **docker**, **minikube** | Kubernetes / containers |
| **linecast** | Terminal weather / radar panes |
| **weather.sh** | DC weather Zellij layout → `~/.local/bin/weather.sh` |

## Layout

```
.
├── install.py              # single entrypoint
├── bin/weather.sh
└── config/
    ├── zsh/.zshrc
    ├── zellij/
    ├── nvim/               # LazyVim + catppuccin + markdown-preview
    ├── kitty/
    ├── oh-my-posh/
    ├── k9s/skins/
    └── tmux/
```

Configs are **symlinked** into `~` / `~/.config`. Existing files are backed up as `*.bak.<timestamp>`.

## Weather dashboard

```bash
weather
```

Requires `zellij` and `linecast` ≥ 2.2. Location defaults to Washington, DC (`38.9072,-77.0369`).

## Platform notes

- **macOS**: Homebrew installs formulae/casks (including Docker Desktop).
- **Linux / WSL**: `apt`/`dnf` for basics; GitHub releases / official scripts for zellij, k9s, helm, minikube, oh-my-posh; Docker via get.docker.com.
- **WSL**: GUI apps like Kitty may need WSLg; Docker often works best with Docker Desktop’s WSL integration.
