
FROM ghcr.io/hm-aemy/librelane-base-image:latest

WORKDIR /work

COPY .gitmodules .gitmodules
COPY .git/ .git/
COPY librelane/ librelane/
COPY pdk/ pdk/

RUN git submodule update --init --recursive

# Source Nix and verify the environment is ready
RUN . /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh && \
    nix-shell librelane --run "echo 'Nix environment initialized'"
