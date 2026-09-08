# Dotfiles

Cross-platform bootstrap for **macOS**, **Linux**, and **WSL**.
Theme: Catppuccin Mocha throughout.

## Quick start

```bash
cd ~/Documents/Projects/dotfiles
python3 install.py
```

Then open a new terminal (or run `exec zsh`).
The first `nvim` launch installs LazyVim plugins.

### Options

| Flag | Meaning |
| --- | --- |
| `--dry-run` | Print actions only |
| `--skip-pkgs` | Configs + shell plugins only (no packages) |
| `--configs` | Symlink configs / `weather.sh` only |

## Tools and usage

The installer sets up these tools.
Aliases and key bindings come from `config/zsh/.zshrc` unless noted.

### Shell and terminal

- **zsh** + Oh My Zsh — Default interactive shell.
  Plugins: `git`, `zsh-autosuggestions`.
- **Oh My Posh** — Prompt theme from
  `~/.config/oh-my-posh/catppuccin.omp.json`.
- **zsh-autosuggestions** — Ghost text from history.
  Accept with → or End.
- **kitty** — GUI terminal (Catppuccin Macchiato).
  Font: JetBrainsMono Nerd Font Mono.
- **Nerd Fonts** — JetBrainsMono + Symbols Only
  (icons in kitty, nvim, eza, prompt).
- **tmux** — Alternate multiplexer.
  Catppuccin plugin under `~/.tmux`.
- **zellij** — Primary multiplexer (`zj`).
  Plugins: `zjstatus`, `zextract` (`Alt-x`), `agent-activity`.

### Editor

- **neovim** + LazyVim — Editor (`nvim`, also `vim`).
  First launch installs plugins.
- **markdownlint-cli2** — Markdown lint for LazyVim.
  Run: `markdownlint-cli2 file.md`.
- **mermaid.nvim** — Mermaid in nvim:
  `<leader>mp` preview, `<leader>mx` stop.

### Search and navigation

- **ripgrep** (`rg`) — Fast recursive search:
  `rg pattern [path]`.
- **The Silver Searcher** (`ag`) — Code search like ack:
  `ag pattern [path]`.
- **fzf** — Fuzzy finder.
  Ctrl-R history; Ctrl-T files; powers `cdi`.
- **zoxide** — Smarter `cd` (replaces `cd`).
  Interactive pick: `cdi`.
- **eza** — Modern `ls` (`ls` / `ll` / `la` / `tree`).
  Use `\ls` for stock ls.

### Git and data

- **git** — Version control.
  Pager uses delta via `~/.config/git/config`.
- **delta** — Side-by-side git diffs with line numbers
  (`git diff`, `git show`).
- **jq** — JSON on the CLI: `jq . file.json`.
  Also used by Cursor → Zellij hooks.
- **fx** — Interactive JSON viewer:
  `fx file.json` or `curl … | fx`.
- **glow** — Render Markdown in the terminal:
  `glow README.md`.

### Kubernetes and containers

- **docker** — Containers.
  macOS: Docker Desktop cask. Linux: get.docker.com.
- **helm** — Kubernetes packages:
  `helm list`, `helm install …`.
- **minikube** — Local cluster: `minikube start`.
- **k9s** — Cluster TUI (`k9s`).
  Skin: `catppuccin-mocha`. Alias: `k` → `kubectl`.
- **sshm** — SSH host TUI
  ([Gu1llaum-3/sshm](https://github.com/Gu1llaum-3/sshm)):
  `sshm`.

### System and fun

- **fastfetch** — System info splash.
  Alias `ff` clears the screen and waits for a key.
- **btop** — Resource monitor (`btop`).
  Theme: Catppuccin Mocha.
- **cbonsai** — ASCII bonsai: `cbonsai -l`.

### Cursor integration

- **Cursor user rules** — Linked to `~/.cursor/rules`
  for every project on this account.
- **Cursor hooks** — Linked to `~/.cursor/hooks.json`.
  Sends agent events to Zellij `agent-activity`.

### Weather

- **linecast** — Terminal weather / radar panes
  (`linecast weather`, `linecast radar`, …).
- **weather.sh** — DC dashboard in Zellij.
  Run: `weather` (needs linecast ≥ 2.2).
  Layout: `config/zellij/layouts/dc-weather.kdl`
  (radar, temperature, sunshine, moon, tides).

## Layout

```text
.
├── install.py              # single entrypoint
├── bin/weather.sh
└── config/
    ├── zsh/.zshrc
    ├── git/config          # delta as git pager (XDG)
    ├── cursor/hooks.json   # → ~/.cursor/hooks.json
    ├── cursor/hooks/       # → ~/.cursor/hooks/
    ├── cursor/rules/       # → ~/.cursor/rules
    ├── zellij/
    │   └── layouts/
    │       ├── default.kdl
    │       └── dc-weather.kdl   # weather dashboard
    ├── nvim/               # LazyVim + catppuccin
    ├── kitty/              # fonts.conf (Nerd Font)
    ├── oh-my-posh/
    ├── btop/               # Catppuccin Mocha + btop.conf
    ├── k9s/skins/
    └── tmux/
```

Configs are **symlinked** into `~` / `~/.config`.
Existing files are backed up as `*.bak.<timestamp>`.

## Cursor user rules

`config/cursor/rules/*.mdc` links to `~/.cursor/rules/`.
Cursor applies them in every project for this account.
Restart Cursor after install.
On WSL, the installer also links `%USERPROFILE%\.cursor\rules`
when `USERPROFILE` is set.

## Cursor hooks

`config/cursor/hooks.json` links to `~/.cursor/hooks.json`.
`config/cursor/hooks/*` links into `~/.cursor/hooks/`.

This wires Cursor Agent / CLI events into the Zellij
`agent-activity` plugin through `zellij pipe`.
The hook uses `jq`, `bash`, and `zellij`.

## Zellij plugins

- `zjstatus` replaces the default bottom status bar
- `zextract` opens on `Alt-x`
- `zellij-agent-activity` prefixes tab names with agent state

The installer downloads plugin `.wasm` files into
`~/.config/zellij/plugins/`.

## Weather dashboard

```bash
weather
```

Requires `zellij` and `linecast` ≥ 2.2.
Uses the linked layout `dc-weather.kdl`.
Location defaults to Washington, DC (`38.9072,-77.0369`).

## Platform notes

- **macOS**: Homebrew formulae/casks (including Docker Desktop).
- **Linux / WSL**: `apt`/`dnf` for basics; GitHub releases or
  official scripts for zellij, k9s, helm, minikube, oh-my-posh;
  Docker via get.docker.com.
- **WSL**: GUI apps like Kitty may need WSLg.
  Docker often works best with Docker Desktop WSL integration.
