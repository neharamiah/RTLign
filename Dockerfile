FROM ubuntu:22.04

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    tar \
    ca-certificates \
    python3 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Download and extract YosysHQ OSS CAD Suite (provides OpenROAD, iverilog, vvp, etc.)
RUN URL=$(curl -s https://api.github.com/repos/YosysHQ/oss-cad-suite-build/releases/latest | grep -o 'https://[^"]*linux-x64[^"]*\.tgz' | head -n 1) && \
    wget "$URL" -O /tmp/oss-cad-suite.tgz && \
    mkdir -p /opt && \
    tar -xzf /tmp/oss-cad-suite.tgz -C /opt && \
    rm /tmp/oss-cad-suite.tgz

# Add OSS CAD Suite tools to PATH
ENV PATH="/opt/oss-cad-suite/bin:${PATH}"

WORKDIR /workspace

# Install Python dependencies
COPY requirements.txt /workspace/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["/bin/bash"]
