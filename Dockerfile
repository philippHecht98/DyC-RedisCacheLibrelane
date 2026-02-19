
FROM ghcr.io/hm-aemy/librelane-base-image:latest

WORKDIR /work

# Install development dependencies
RUN apt-get update 
RUN apt-get install -y --no-install-recommends git help2man perl python3 python3-pip make autoconf g++ flex bison ccache
RUN apt-get install -y --no-install-recommends libgoogle-perftools-dev numactl perl-doc
RUN apt-get install -y --no-install-recommends libfl2 libfl-dev iverilog 

# Install Python 3.11

RUN apt-get install -y python3
# RUN apt-get install -y --no-install-recommends software-properties-common \
#     && add-apt-repository ppa:deadsnakes/ppa \
#     && apt-get update \
#     && apt-get install -y --no-install-recommends python3.11 python3.11-venv python3.11-dev \
#     && rm -rf /var/lib/apt/lists/*


# Build and install Verilator v5.036
RUN git clone https://github.com/verilator/verilator /tmp/verilator \
    && cd /tmp/verilator \
    && git checkout v5.036 \
    && autoconf \
    && ./configure \
    && make -j$(nproc) \
    && make install \
    && cd / \
    && rm -rf /tmp/verilator

# Copy requirements and install Python dependencies

COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN python3 -m pip install --break-system-packages -r /tmp/requirements-dev.txt

COPY .gitmodules .gitmodules
COPY .git/ .git/

RUN git submodule update --init --recursive

# Source Nix and verify the environment is ready
RUN . /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh && \
    nix-shell librelane --run "echo 'Nix environment initialized'"


COPY src src
COPY test test
COPY Makefile Makefile