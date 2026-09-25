# Distributed Mesh & Control Plane

An intelligent egress mesh and distributed infrastructure platform orchestrating a persistent Master Gateway (Server 1) with an ephemeral cluster of 20 GitHub Actions runners in Microsoft Azure datacenters.

## Architecture

- **Client Ingress**: AmneziaWG obfuscated tunnel (`awg0` on UDP 51820) bypassing DPI/TSPU filters.
- **Smart Split-Routing**: SmartDNS and nftables dynamically route domestic traffic (.ru, .рф, banks) directly via the physical interface (`ens3`), while overseas traffic routes through the mesh pool.
- **Egress Mesh**: Multi-path ECMP load balancing over 20 Azure runners connected via IPIP-over-WireGuard overlay.
- **Control Plane**: Unified Web Panel on port 80 (`http://server.mesh` / `http://server1.mesh`) with Svelte SPA frontend, FastAPI backend, SQLite, Alembic migrations, and an asynchronous Reconciliation Loop.
- **Zero-Trust Identity**: Automatic RBAC authorization based on WireGuard client IP (`is_admin` flag) with dedicated User Portals for regular clients and full management for administrators.

## Installation

Install the entire stack with a single command on a clean Debian/Ubuntu server:

```bash
sudo ./install.sh
```

Or directly via curl:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/wprhvso/mesh/main/install.sh)"
```

## Web Control Plane

Once connected to the VPN tunnel, access the dashboard at:
- **`http://server.mesh/`**
- **`http://server1.mesh/`**

### Features:
- **Clients Management**: Issue new client configurations, QR codes, toggle `is_admin`, disable/enable peers.
- **Runners Fleet**: Live matrix of 20 Azure runners with real-time ping, status, and egress IPs.
- **GitHub Donors**: Add PAT tokens to scale and auto-dispatch runner workflows.
- **SSH Keys**: Manage authorized public keys automatically deployed across Server 1 and all 20 runners.
- **DNS Zone**: Dynamic `.mesh` zone management reconciled every 5 seconds.
