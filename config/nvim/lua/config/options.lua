-- Options are automatically loaded before lazy.nvim startup
-- Defaults: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
vim.g.markdown_fenced_languages = { "bash", "python", "lua", "json", "yaml", "go", "rust" }

-- Icons assume a Nerd Font in the host terminal (Kitty fonts.conf + Symbols Nerd Font Mono).
-- GUI clients (Neovide, etc.) get an explicit face; TUI Neovim inherits Kitty.
vim.opt.guifont = "JetBrainsMono Nerd Font Mono,Symbols Nerd Font Mono:h12"
