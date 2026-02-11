
FROM ghcr.io/hm-aemy/librelane-base-image:latest

WORKDIR /work
COPY . .
RUN git submodule update --init --recursive

ENTRYPOINT ["nix-shell", "librelane", "--run"]