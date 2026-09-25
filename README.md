# Distributed Mesh & Ephemeral Action Runner Pool

A distributed egress mesh and compute architecture using a persistent Master Gateway (Server 1) orchestrating a dynamic pool of 20 ephemeral GitHub Actions runners.

## Architecture

- Control Plane: Master Gateway with SmartDNS, Failover Routing, and Auto-healing daemon.
- Data Plane: 20 GitHub Actions runners (matrix 1..20) providing Microsoft Azure egress IPs.
- Network: Reverse WireGuard tunneling with sub-second failover.

## Structure

- `.github/workflows/mesh.yml`: Matrix runner definitions and lifecycle orchestrator.
- `agent/`: Ephemeral node onboarding, tunneling, and NAT masquerade.
- `server/`: Controller daemon for node health monitoring and auto-dispatching.
- `ansible/`: Minimalist Ansible automation configuring AmneziaWG, SmartDNS, and nftables routing.

## Deployment

```bash
cd ansible
ansible-playbook playbook.yml
```
