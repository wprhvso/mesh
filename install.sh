#!/usr/bin/env bash
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root" >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq software-properties-common curl wget gnupg nftables iptables

cat << 'EOF' > /etc/sysctl.d/99-ipforward.conf
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
EOF
sysctl --system

add-apt-repository -y ppa:amnezia/ppa
apt-get update -qq
apt-get install -y -qq amneziawg amneziawg-tools

mkdir -p /etc/amnezia/amneziawg
chmod 700 /etc/amnezia/amneziawg

if [ ! -f /etc/amnezia/amneziawg/server_private.key ]; then
    awg genkey > /etc/amnezia/amneziawg/server_private.key
    chmod 600 /etc/amnezia/amneziawg/server_private.key
fi
SERVER_PRIV=$(cat /etc/amnezia/amneziawg/server_private.key)
SERVER_PUB=$(echo "${SERVER_PRIV}" | awg pubkey)

if [ ! -f /etc/amnezia/amneziawg/client_private.key ]; then
    awg genkey > /etc/amnezia/amneziawg/client_private.key
    chmod 600 /etc/amnezia/amneziawg/client_private.key
fi
CLIENT_PRIV=$(cat /etc/amnezia/amneziawg/client_private.key)
CLIENT_PUB=$(echo "${CLIENT_PRIV}" | awg pubkey)

PUBLIC_IP=$(curl -s4 https://api.ipify.org || curl -s4 https://ifconfig.me || hostname -I | awk '{print $1}')
DEFAULT_IFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
DEFAULT_GW=$(ip route | grep default | awk '{print $3}' | head -n1)

cat << EOF > /etc/amnezia/amneziawg/awg0.conf
[Interface]
Address = 10.10.1.1/24
ListenPort = 51820
PrivateKey = ${SERVER_PRIV}
Jc = 4
Jmin = 40
Jmax = 70
S1 = 15
S2 = 30
H1 = 123456789
H2 = 987654321
H3 = 135792468
H4 = 246813579

[Peer]
PublicKey = ${CLIENT_PUB}
AllowedIPs = 10.10.1.2/32
EOF
chmod 600 /etc/amnezia/amneziawg/awg0.conf

cat << EOF > /etc/amnezia/amneziawg/client.conf
[Interface]
Address = 10.10.1.2/32
PrivateKey = ${CLIENT_PRIV}
DNS = 10.10.1.1
Jc = 4
Jmin = 40
Jmax = 70
S1 = 15
S2 = 30
H1 = 123456789
H2 = 987654321
H3 = 135792468
H4 = 246813579

[Peer]
PublicKey = ${SERVER_PUB}
Endpoint = ${PUBLIC_IP}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
EOF
chmod 600 /etc/amnezia/amneziawg/client.conf

systemctl enable --now awg-quick@awg0

SMARTDNS_DEB=$(curl -sSL https://api.github.com/repos/pymumu/smartdns/releases/latest | grep "browser_download_url.*x86_64.*\.deb" | cut -d : -f 2,3 | tr -d \" | tr -d ' ')
wget -q "${SMARTDNS_DEB}" -O /tmp/smartdns.deb
dpkg -i /tmp/smartdns.deb || apt-get install -f -y

cat << 'EOF' > /etc/smartdns/smartdns.conf
bind 127.0.0.1:53
bind 10.10.1.1:53

cache-size 65536
cache-persist yes
cache-file /var/cache/smartdns.cache
rr-ttl-min 300
rr-ttl-max 86400
serve-expired yes
serve-expired-ttl 86400

speed-check-mode tcp:443,ping
force-AAAA-SOA yes

server 77.88.8.8 -group domestic -exclude-default-group
server 77.88.8.1 -group domestic -exclude-default-group
server 195.208.4.1 -group domestic -exclude-default-group

server-https https://cloudflare-dns.com/dns-query -group oversea
server-https https://dns.google/dns-query -group oversea
server-tls 1.1.1.1:853 -group oversea

nameserver /.ru/domestic
nameserver /.xn--p1ai/domestic
nameserver /.su/domestic
nameserver /.yandex.net/domestic
nameserver /.vk.com/domestic
nameserver /.dzen.ru/domestic
nameserver /.gosuslugi.ru/domestic

nftset /.ru/4#inet#filter#ru_domains
nftset /.xn--p1ai/4#inet#filter#ru_domains
nftset /.su/4#inet#filter#ru_domains
nftset /.yandex.net/4#inet#filter#ru_domains
nftset /.vk.com/4#inet#filter#ru_domains
nftset /.dzen.ru/4#inet#filter#ru_domains
nftset /.gosuslugi.ru/4#inet#filter#ru_domains
EOF

systemctl enable --now smartdns
systemctl restart smartdns

cat << EOF > /etc/nftables.conf
flush ruleset

table inet filter {
    set ru_domains {
        type ipv4_addr
        flags timeout
        timeout 1h
    }

    chain prerouting {
        type filter hook prerouting priority mangle; policy accept;
        iifname "awg0" tcp dport 853 reject with tcp reset
        iifname "awg0" ip daddr @ru_domains meta mark set 0x100
    }

    chain forward {
        type filter hook forward priority filter; policy accept;
        tcp flags syn tcp option maxseg size set rt mtu
    }

    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;
        meta mark 0x100 oifname "${DEFAULT_IFACE}" masquerade
        oifname "wg-mesh" masquerade
    }
}
EOF

systemctl enable --now nftables
systemctl restart nftables

cat << EOF > /etc/systemd/system/pbr-mesh.service
[Unit]
Description=Policy Based Routing for Mesh Split Tunnel
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'ip rule add fwmark 0x100 lookup 100 2>/dev/null || true; ip route replace default via ${DEFAULT_GW} dev ${DEFAULT_IFACE} table 100'
ExecStop=/bin/sh -c 'ip rule del fwmark 0x100 lookup 100 2>/dev/null || true'

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now pbr-mesh
systemctl restart pbr-mesh

echo "Setup completed successfully."
echo "Client configuration generated at: /etc/amnezia/amneziawg/client.conf"
