# Path to Oh My Zsh
export ZSH="${ZSH:-$HOME/.oh-my-zsh}"

# Theme is handled by Oh My Posh — keep OMZ theme blank/minimal
ZSH_THEME=""

# Plugins (oh-my-zsh + custom)
plugins=(git zsh-autosuggestions)

source "$ZSH/oh-my-zsh.sh"

# --- User configuration -------------------------------------------------------

export EDITOR="${EDITOR:-nvim}"
export VISUAL="$EDITOR"
export K9S_SKIN="catppuccin-mocha"
export PATH="$HOME/.local/bin:$PATH"

# Oh My Posh — same theme as the previous ~/.zshrc (catppuccin.omp.json)
if command -v oh-my-posh >/dev/null 2>&1; then
  _omp_cfg="${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-posh/catppuccin.omp.json"
  if [[ -f "$_omp_cfg" ]]; then
    eval "$(oh-my-posh init zsh --config "$_omp_cfg")"
  else
    eval "$(oh-my-posh init zsh --config https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/catppuccin.omp.json)"
  fi
  unset _omp_cfg
fi

# fzf — shell keybindings/completion; also powers zoxide interactive (`cdi`)
if command -v fzf >/dev/null 2>&1; then
  eval "$(fzf --zsh)"
fi

# zoxide — try as `cd` (remove --cmd cd later if you want stock cd back)
# With fzf installed, `cdi` opens an interactive directory picker
if command -v zoxide >/dev/null 2>&1; then
  eval "$(zoxide init zsh --cmd cd)"
fi

# Aliases
alias weather='bash "$HOME/.local/bin/weather.sh"'
alias vim='nvim'
alias k='kubectl'
alias zj='zellij'

# eza — try as `ls` (use `\ls` for the real binary)
if command -v eza >/dev/null 2>&1; then
  alias ls='eza --icons --group-directories-first'
  alias ll='eza -l --icons --group-directories-first'
  alias la='eza -la --icons --group-directories-first'
  alias tree='eza --tree --icons'
fi

# fastfetch — `ff` clears the screen/scrollback and waits for a key so the prompt stays hidden
if command -v fastfetch >/dev/null 2>&1; then
  ff() {
    printf '\033[H\033[2J\033[3J'
    printf '\033[?25l'
    command fastfetch "$@"
    read -sk 1
    printf '\033[?25h'
  }
fi
