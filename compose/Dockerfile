FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-toml \
    python3-requests \
    python3-poetry \
    gnupg \
    bzip2 \
    tini \
    curl \
    wait-for-it \
    entr \
    gnutls-bin \
    nettle-dev \
    gcc \
    llvm-dev \
    libclang-dev \
    build-essential \
    pkg-config \
    gettext \
    git \
    procps \
    psmisc \
    vim-tiny \
    cargo \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean \
 && apt-get autoclean \
 && rm -rf /var/lib/apt/archives/* \
 && rm -rf /var/cache/apt/*
ADD setup /setup
RUN /setup/setup
ADD run /setup/run
ADD pdbrc.py /root/.pdbrc.py
WORKDIR /source
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash", "/setup/run"]