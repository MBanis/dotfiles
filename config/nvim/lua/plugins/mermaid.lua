return {
  {
    "nvim-treesitter/nvim-treesitter",
    opts = function(_, opts)
      opts.ensure_installed = opts.ensure_installed or {}
      vim.list_extend(opts.ensure_installed, { "mermaid" })
    end,
  },
  {
    "kevalin/mermaid.nvim",
    dependencies = { "nvim-treesitter/nvim-treesitter" },
    ft = { "mermaid" },
    keys = {
      { "<leader>mp", "<cmd>MermaidPreview<cr>", desc = "Mermaid Preview", ft = "mermaid" },
      { "<leader>mx", "<cmd>MermaidPreviewStop<cr>", desc = "Mermaid Stop Preview", ft = "mermaid" },
      { "<leader>mf", "<cmd>MermaidFormat<cr>", desc = "Mermaid Format", ft = "mermaid" },
      { "<leader>mr", "<cmd>MermaidRender<cr>", desc = "Mermaid Render", ft = "mermaid" },
      { "<leader>mc", "<cmd>MermaidCopyURL<cr>", desc = "Mermaid Copy URL", ft = "mermaid" },
    },
    opts = {
      lint = {
        enabled = true,
        command = "mmdc",
      },
      preview = {
        renderer = "beautiful-mermaid",
        theme = "catppuccin-mocha",
      },
    },
  },
}
