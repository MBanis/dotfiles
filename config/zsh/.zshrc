# Path to Oh My Zsh
export ZSH="${ZSH:-$HOME/.oh-my-zsh}"

# Theme is handled by Oh My Posh — keep OMZ theme blank/minimal
ZSH_THEME=""

# Plugins (oh-my-zsh + custom)
plugins=(git)

source "$ZSH/oh-my-zsh.sh"

# --- User configuration -------------------------------------------------------

export EDITOR="${EDITOR:-nvim}"
export VISUAL="$EDITOR"
export K9S_SKIN="catppuccin-mocha"
export PATH="$HOME/.local/bin:$PATH"

# Oh My Posh (Catppuccin Mocha)
if command -v oh-my-posh >/dev/null 2>&1; then
  _omp_cfg="${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-posh/catppuccin_mocha.omp.json"
  if [[ -f "$_omp_cfg" ]]; then
    eval "$(oh-my-posh init zsh --config "$_omp_cfg")"
  else
    eval "$(oh-my-posh init zsh --config https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/catppuccin_mocha.omp.json)"
  fi
  unset _omp_cfg
fi

# zsh-autosuggestions (Homebrew or Linux package path)
for _sug in \
  /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh \
  /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh \
  /usr/local/share/zsh-autosuggestions/zsh-autosuggestions.zsh
do
  [[ -f "$_sug" ]] && source "$_sug" && break
done
unset _sug

# zsh-autocomplete (cloned into OMZ custom plugins by installer)
if [[ -f "${ZSH_CUSTOM:-$ZSH/custom}/plugins/zsh-autocomplete/zsh-autocomplete.plugin.zsh" ]]; then
  source "${ZSH_CUSTOM:-$ZSH/custom}/plugins/zsh-autocomplete/zsh-autocomplete.plugin.zsh"
fi

# Aliases
alias weather='bash "$HOME/.local/bin/weather.sh"'
alias vim='nvim'
alias k='kubectl'
alias zj='zellij'
