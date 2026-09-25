# Distributed Mesh & Ephemeral Action Runner Pool

A distributed egress mesh and compute architecture using a persistent Master Gateway (Server 1) orchestrating a dynamic pool of 20 ephemeral GitHub Actions runners.

## Architecture

- **Control Plane**: Master Gateway with SmartDNS, Failover Routing, and Auto-healing daemon.
- **Data Plane**: 20 GitHub Actions runners (matrix `1..20`) providing Microsoft Azure egress IPs.
- **Network**: Reverse WireGuard tunneling with sub-second failover.

## Installation

Install the entire stack (AmneziaWG, SmartDNS, nftables, and Policy-Based Routing) with a single command:

```bash
sudo ./install.sh
```

Or directly via curl:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/wprhvso/mesh/main/install.sh)"
```

The script performs the following setup:
1. Configures kernel packet forwarding (`net.ipv4.ip_forward = 1`).
2. Installs AmneziaWG via official PPA (`ppa:amnezia/ppa`).
3. Generates cryptographic keys and obfuscated parameters (`Jc`, `Jmin`, `Jmax`, `S1`, `S2`, `H1`-`H4`).
4. Generates client configuration at `/etc/amnezia/amneziawg/client.conf`.
5. Installs and configures SmartDNS with dual groups (`domestic` for RU, `oversea` via DoH).
6. Configures dynamic `nftables` sets with 1-hour TTL and Android Private DNS rejection (port 853).
7. Sets up persistent Policy-Based Routing systemd service.

## Structure

- `install.sh`: Self-contained setup script for Master Gateway.
- `.github/workflows/mesh.yml`: Matrix runner definitions and lifecycle orchestrator.
- `agent/`: Ephemeral node onboarding, tunneling, and NAT masquerade.
- `server/`: Controller daemon for node health monitoring and auto-dispatching.
