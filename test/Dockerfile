FROM debian:bookworm

# Avoid interactive prompts during package installation.
ENV DEBIAN_FRONTEND=noninteractive

# Base packages the installer expects to find or will install.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    ca-certificates \
    gnupg \
    sudo \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Generate a UTF-8 locale (many CLI tools expect it).
RUN sed -i 's/# en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# Create a non-root user so configs install into a real home directory.
RUN useradd -m -s /bin/bash dotfiles \
    && echo "dotfiles ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER dotfiles
WORKDIR /home/dotfiles/dotfiles

# Copy the repo in (use .dockerignore to keep the image small).
COPY --chown=dotfiles:dotfiles . .

# Default: drop into an interactive shell.
# Override with `docker run ... python3 install.py` for a headless smoke test.
CMD ["bash"]
