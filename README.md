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
| **zellij** | Multiplexer — Catppuccin Mocha + `zjstatus` + `zextract` + `agent-activity` |
| **neovim** + LazyVim | Catppuccin Mocha + markdown preview (`<leader>mp`) + mermaid.nvim |
| **markdownlint-cli2** | Markdown linter used by LazyVim’s markdown extra |
| **kitty** | Terminal — Catppuccin Macchiato + JetBrainsMono Nerd Font Mono + Symbols Nerd Font Mono |
| **sshm** | [Gu1llaum-3/sshm](https://github.com/Gu1llaum-3/sshm) SSH TUI |
| **k9s** | Skin: `catppuccin-mocha` |
| **helm**, **docker**, **minikube** | Kubernetes / containers |
| **ripgrep** (`rg`) | Fast search |
| **jq** | JSON processor; required for Cursor → Zellij agent activity hooks |
| **delta** | Git diffs (via `~/.config/git/config`) |
| **glow** | Markdown in the terminal |
| **zoxide** | Smarter `cd` (aliased over `cd` to try); `cdi` interactive with fzf |
| **eza** | Modern `ls` (aliased over `ls` / `ll` / `la`) |
| **fzf** | Fuzzy finder (shell + zoxide `cdi`) |
| **fx** | Interactive JSON viewer |
| **fastfetch** | System splash (`ff` — clears screen, waits for a key before the prompt) |
| **btop** | Resource monitor — Catppuccin Mocha |
| **cbonsai** | ASCII bonsai tree |
| **Cursor user rules** | Symlinked to `~/.cursor/rules` (all projects) |
| **Cursor hooks** | Symlinked to `~/.cursor/hooks.json` for global `agent-activity` wiring |
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
    ├── cursor/hooks.json   # global Cursor hooks → ~/.cursor/hooks.json
    ├── cursor/hooks/       # hook scripts → ~/.cursor/hooks/
    ├── cursor/rules/       # user rules → ~/.cursor/rules
    ├── zellij/
    ├── nvim/               # LazyVim + catppuccin + markdown-preview
    ├── kitty/              # includes fonts.conf (JetBrainsMono Nerd Font Mono)
    ├── oh-my-posh/
    ├── btop/               # Catppuccin Mocha theme + btop.conf
    ├── k9s/skins/
    └── tmux/
```

Configs are **symlinked** into `~` / `~/.config`. Existing files are backed up as `*.bak.<timestamp>`.

## Cursor user rules

`config/cursor/rules/*.mdc` is linked to `~/.cursor/rules/` so Cursor applies them in **every project** for this account (not only this repo). Restart Cursor after install. On WSL, the installer also links `%USERPROFILE%\.cursor\rules` when `USERPROFILE` is set.

## Cursor hooks

`config/cursor/hooks.json` is linked to `~/.cursor/hooks.json`, and `config/cursor/hooks/*` is linked into `~/.cursor/hooks/`.

This wires Cursor Agent / CLI events into the Zellij `agent-activity` plugin through `zellij pipe`. The hook uses `jq`, `bash`, and `zellij`.

## Zellij plugins

- `zjstatus` replaces the default bottom status bar
- `zextract` opens on `Alt-x`
- `zellij-agent-activity` prefixes tab names with the active agent state

The installer downloads the plugin `.wasm` files into `~/.config/zellij/plugins/`.

## Weather dashboard

```bash
weather
```

Requires `zellij` and `linecast` ≥ 2.2. Location defaults to Washington, DC (`38.9072,-77.0369`).

## Platform notes

- **macOS**: Homebrew installs formulae/casks (including Docker Desktop).
- **Linux / WSL**: `apt`/`dnf` for basics; GitHub releases / official scripts for zellij, k9s, helm, minikube, oh-my-posh; Docker via get.docker.com.
- **WSL**: GUI apps like Kitty may need WSLg; Docker often works best with Docker Desktop’s WSL integration.
