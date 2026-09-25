#!/usr/bin/env bash
set -e

apt-get update -qq
apt-get install -y -qq wireguard nftables python3

sysctl -w net.ipv4.ip_forward=1

ip link add dev wg-mesh type wireguard || true
ip address add 10.200.0.1/24 dev wg-mesh || true
ip link set up dev wg-mesh || true
