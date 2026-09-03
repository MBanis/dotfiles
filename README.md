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
| **Oh My Posh** | Prompt — `catppuccin.omp.json` (same as prior zshrc) |
| **zsh-autosuggestions** | Fish-like suggestions |
| **zellij** | Multiplexer — Catppuccin Mocha |
| **neovim** + LazyVim | Catppuccin Mocha + markdown preview (`<leader>mp`) + mermaid.nvim |
| **kitty** | Terminal — Catppuccin Macchiato + JetBrainsMono Nerd Font Mono + Symbols Nerd Font Mono |
| **sshm** | [Gu1llaum-3/sshm](https://github.com/Gu1llaum-3/sshm) SSH TUI |
| **k9s** | Skin: `catppuccin-mocha` |
| **helm**, **docker**, **minikube** | Kubernetes / containers |
| **ripgrep** (`rg`) | Fast search |
| **delta** | Git diffs (via `~/.config/git/config`) |
| **glow** | Markdown in the terminal |
| **zoxide** | Smarter `cd` (aliased over `cd` to try); `cdi` interactive with fzf |
| **eza** | Modern `ls` (aliased over `ls` / `ll` / `la`) |
| **fzf** | Fuzzy finder (shell + zoxide `cdi`) |
| **fx** | Interactive JSON viewer |
| **fastfetch** | System splash (`ff` — clears screen, waits for a key before the prompt) |
| **cbonsai** | ASCII bonsai tree |
| **linecast** | Terminal weather / radar panes |
| **weather.sh** | DC weather Zellij layout → `~/.local/bin/weather.sh` |

## Layout

```
.
├── install.py              # single entrypoint
├── bin/weather.sh
└── config/
    ├── zsh/.zshrc
    ├── git/config          # delta as git pager (XDG; keeps ~/.gitconfig identity)
    ├── zellij/
    ├── nvim/               # LazyVim + catppuccin + markdown-preview
    ├── kitty/              # includes fonts.conf (JetBrainsMono Nerd Font Mono)
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
