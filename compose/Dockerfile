FROM bitnami/minideb:bookworm

RUN install_packages \
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
    git \
    make \
    rpm \
    golang
ENV PATH="${PATH}:/root/go/bin"
ADD setup /setup
RUN /setup/setup
ADD run /setup/run
ADD pdbrc.py /root/.pdbrc.py
RUN git config --global --add safe.directory /source
WORKDIR /source
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash", "/setup/run"]
