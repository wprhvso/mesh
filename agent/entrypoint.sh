#!/usr/bin/env bash
set -e

sudo apt-get update -qq && sudo apt-get install -y -qq wireguard iptables curl

IP_OCTET=$((NODE_ID + 10))
TUN_IP="10.200.0.${IP_OCTET}"

PRIVATE_KEY=$(wg genkey)
PUBLIC_KEY=$(echo "${PRIVATE_KEY}" | wg pubkey)

echo "Node ${NODE_ID} online with IP ${TUN_IP}"

sudo sysctl -w net.ipv4.ip_forward=1
DEFAULT_IFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
sudo iptables -t nat -A POSTROUTING -o "${DEFAULT_IFACE}" -j MASQUERADE

SLEEP_DURATION=$((18000 + (NODE_ID * 60)))
echo "Heartbeat loop initialized for ${SLEEP_DURATION}s"

sleep "${SLEEP_DURATION}"
