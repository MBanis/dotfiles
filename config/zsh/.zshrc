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

# Aliases
alias weather='bash "$HOME/.local/bin/weather.sh"'
alias vim='nvim'
alias k='kubectl'
alias zj='zellij'
