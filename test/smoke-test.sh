#!/usr/bin/env bash
# Build and run the dotfiles installer inside a Debian container.
#
# Usage:
#   ./test/smoke-test.sh              # headless dry-run
#   ./test/smoke-test.sh --interactive # drop into a shell for manual checks
#   ./test/smoke-test.sh --full       # run the real installer (installs packages)
#
# Important: do not bind-mount the macOS repo into the container.
# Docker Desktop + Apple compressed files (com.apple.decmpfs) cause Errno 5
# when tools read through the mount. Each run rebuilds the image so COPY
# embeds a clean copy of the repo.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="dotfiles-test"

echo "▸ Building image from Debian bookworm (embeds current repo)…"
docker build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Dockerfile" "$REPO_DIR"

MODE="${1:---dry-run}"

case "$MODE" in
    --interactive|-i)
        echo "▸ Starting interactive container. Run 'python3 install.py' then 'exec zsh'."
        exec docker run -it --rm \
            --hostname dotfiles-test \
            "$IMAGE_NAME" \
            bash
        ;;
    --full)
        echo "▸ Running full installer inside container…"
        docker run --rm \
            --hostname dotfiles-test \
            "$IMAGE_NAME" \
            python3 install.py
        ;;
    --dry-run|-d|*)
        echo "▸ Running installer in dry-run mode…"
        docker run --rm \
            --hostname dotfiles-test \
            "$IMAGE_NAME" \
            python3 install.py --dry-run
        ;;
esac
