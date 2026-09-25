#!/usr/bin/env bash
set -e

sudo apt-get update -qq && sudo apt-get install -y -qq wireguard-tools iptables curl jq
sudo modprobe ipip

PRIVATE_KEY=$(wg genkey)
PUBLIC_KEY=$(echo "${PRIVATE_KEY}" | wg pubkey)

REGISTER_PAYLOAD=$(printf '{"node_id": %d, "pubkey": "%s"}' "${NODE_ID}" "${PUBLIC_KEY}")

RESP=$(curl -s -S -f --connect-timeout 10 --max-time 15     -X POST "http://${SERVER_HOST}:${REG_PORT}/register"     -H "Authorization: Bearer ${AUTH_TOKEN}"     -H "Content-Type: application/json"     -d "${REGISTER_PAYLOAD}")

ASSIGNED_IP=$(echo "${RESP}" | jq -r .ip)
TUN_IP=$(echo "${RESP}" | jq -r .tun_ip)
TUN_PEER=$(echo "${RESP}" | jq -r .tun_peer)
SERVER_PUBKEY=$(echo "${RESP}" | jq -r .server_pubkey)
SERVER_PORT=$(echo "${RESP}" | jq -r .server_port)

if [ -z "${ASSIGNED_IP}" ] || [ "${ASSIGNED_IP}" = "null" ]; then
    echo "Failed to obtain IP from controller: ${RESP}" >&2
    exit 1
fi

sudo mkdir -p /etc/wireguard
cat << EOF | sudo tee /etc/wireguard/wg0.conf > /dev/null
[Interface]
Address = ${ASSIGNED_IP}/24
PrivateKey = ${PRIVATE_KEY}

[Peer]
PublicKey = ${SERVER_PUBKEY}
Endpoint = ${SERVER_HOST}:${SERVER_PORT}
AllowedIPs = 10.200.0.0/24
PersistentKeepalive = 15
EOF

sudo chmod 600 /etc/wireguard/wg0.conf
sudo wg-quick up wg0

sudo ip tunnel add tun0 mode ipip remote "${TUN_PEER}" local "${TUN_IP}" dev wg0
sudo ip addr add "${TUN_IP}/30" dev tun0
sudo ip link set tun0 mtu 1380 up

sudo sysctl -w net.ipv4.ip_forward=1 > /dev/null
DEFAULT_IFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
sudo iptables -t nat -A POSTROUTING -o "${DEFAULT_IFACE}" -j MASQUERADE
sudo iptables -A FORWARD -i tun0 -o "${DEFAULT_IFACE}" -j ACCEPT
sudo iptables -A FORWARD -i "${DEFAULT_IFACE}" -o tun0 -m state --state RELATED,ESTABLISHED -j ACCEPT

echo "Node ${NODE_ID} active on ${ASSIGNED_IP} (tunnel ${TUN_IP}), ready for traffic"

SLEEP_DURATION=$((18000 + (NODE_ID * 60)))
END_TIME=$((SECONDS + SLEEP_DURATION))

while [ "${SECONDS}" -lt "${END_TIME}" ]; do
    ping -c 1 -W 2 "${TUN_PEER}" > /dev/null 2>&1 || true
    sleep 10
done

sudo ip link set tun0 down || true
sudo wg-quick down wg0 || true
