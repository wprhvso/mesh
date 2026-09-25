#!/usr/bin/env bash
set -e

LOG_FILE="/var/log/mesh-install.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

C_RESET='\033[0m'
C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[0;33m'
C_BLUE='\033[0;34m'
C_CYAN='\033[0;36m'

log_info() {
    printf "${C_BLUE}[INFO]${C_RESET} [%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

log_step() {
    printf "${C_CYAN}[STEP]${C_RESET} [%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

log_success() {
    printf "${C_GREEN}[SUCCESS]${C_RESET} [%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

log_warn() {
    printf "${C_YELLOW}[WARN]${C_RESET} [%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

log_error() {
    printf "${C_RED}[ERROR]${C_RESET} [%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

log_info "Starting Mesh Gateway installation script"
log_info "All logs are being written to ${LOG_FILE}"

if [ "$(id -u)" -ne 0 ]; then
    log_error "This script must be run as root (or with sudo)"
    exit 1
fi
log_success "Root privileges verified"

log_step "Detecting network topology and public interface"
DEFAULT_IFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
DEFAULT_GW=$(ip route | grep default | awk '{print $3}' | head -n1)

if [ -z "${DEFAULT_IFACE}" ] || [ -z "${DEFAULT_GW}" ]; then
    log_error "Failed to detect default network interface or gateway"
    exit 1
fi
log_info "Default network interface: ${DEFAULT_IFACE}"
log_info "Default gateway: ${DEFAULT_GW}"

log_step "Detecting public IPv4 address"
PUBLIC_IP=$(curl -s4 https://api.ipify.org || curl -s4 https://ifconfig.me || hostname -I | awk '{print $1}')
if [ -z "${PUBLIC_IP}" ]; then
    log_warn "Failed to detect public IP via external APIs, falling back to local address"
    PUBLIC_IP=$(hostname -I | awk '{print $1}')
fi
log_info "Detected public IP: ${PUBLIC_IP}"

export DEBIAN_FRONTEND=noninteractive

log_step "Configuring kernel packet forwarding (sysctl)"
cat << 'EOF' > /etc/sysctl.d/99-ipforward.conf
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
EOF
sysctl --system > /dev/null
log_success "Kernel packet forwarding enabled"

log_step "Updating package repositories and installing base prerequisites"
apt-get update -qq
apt-get install -y -qq curl wget gnupg nftables iptables qrencode
log_success "Base dependencies installed"

log_step "Configuring Amnezia PPA repository and GPG signing key"
mkdir -p /etc/apt/keyrings

cat << 'EOF' | gpg --dearmor --yes -o /etc/apt/keyrings/amnezia.gpg
-----BEGIN PGP PUBLIC KEY BLOCK-----
Comment: Hostname: 
Version: Hockeypuck 2.2

xsFNBGV0UhsBEAC33rMndHSN/k+u7gcZbh9/FjgYfGltQAtVe2QDxzn7UV+k/ChX
OrYRw6Izw/DrhaapkNCThK2jwJE64e0NjboLH7UrrmSJLXMfOlDFbyGJVRA+1sTB
lo7kKHY0xiZ1CHDzjKNV3czbesu80A9nuTZYyWHEn9ax6wsqKG3N8SvzQkUrIOVD
2wZjh0p273CCEGkBnax1ghAV3MF8OrsPU6FRJ+ZakzKbu54g68xoV+2813YECme0
JKsWfUUe/1uEJOXCvuACURSxnYr0sihJd8QI/jHSGlfeq72e5MflFEOrnu5xaDSJ
r2W5lvUetG7EGSxtNKd7Jm/KhUV04g7arA0qydRjRToW3QqyzG7VB2nXKz3AOBYN
earWAuBcTkfPvRVchxbjiYonKZA5tIlVrpawMZsdxKvYwl6LVnpBcccFWPhpudfy
4TpCqCxRoAanOCvSirI3/y7TcZMBw643SaxXi1ifGeg6eyMzrLtP3CeonKBHGzrt
1eeKGtEw/PFN4RmwpBePxi+uj0CoTD6zjCQa3c8EeB4Qz7tt6PnpibxdtZE8sBdd
51wSA/fPGi2tFph8IVAsws7oxcQxZYl8CyncKDLcoR4dxVHYdFEDDf1GjRjoQ3Ai
nD7fxD5qYzExe50DBVpuUbWcAiGICNxfvzQtUSRRtMoSHDcvzsy03KC6VwARAQAB
zR5MYXVuY2hwYWQgUFBBIGZvciBJdXJpaSBFZ29yb3bCwY4EEwEKADgWIQR1yd1y
x5mHDjEFQuJBZvLCVykIKAUCZXRSGwIbAwULCQgHAgYVCgkICwIEFgIDAQIeAQIX
gAAKCRBBZvLCVykIKBu5D/9akmHCHlUqm2RTTBeTMbLNGc0l6YugpPaCM6vz0O9k
BFP5PfRaNSRzyF7wHFHNY3JUHcor28my1fD8AE4+C3PwXz8tVYLh57UUsp4wjqHY
+MTl/1ngDViPGD3PRjB8ZlO+19yerfplZv1Jaw7FZZv2BZOAXb+ddqUG4EmlzOnC
EhcSDdFrzEBB3RGthjIb3QkKWKGbELDiMfogmsO9BE139Raiw23blagDrbnWsG4j
ReZeu3atjG6AW8eL7m+i7bKKshD2CYVMznI5cYGLMKo9w7sb33uylPj1Vx9O7joP
2GFf2rTpCY8wgzk7i1RqsipJ80u1/DY91Xdizv3f2BBe6UY7qHKoK00O11J0y8yU
is2Asycy33Wy51pf6rCFUBLQu+c1fEypHF6jqANmQwaH7pPBliy4gGWvrVggzV4m
xv7SnRiMi4PFyVwjKWm8dmuMxi/B9s++VG/ed+5aYgJYL58MohG3MUI/L58eitSC
DDcQ1iAnBmawnGMKPqzMgRFB3OU3wDwfh7LNVvQqWpQ4q7pr4Cq1CvZvGoggXWDo
1/vylPsRmiiuNetfsoVYmrkgtj1om07m5Xp1v4SyXJH11c3dc/xfMmn/4RlMWIpq
86IsOjpr3avsw3FVUNCgD5Wf5+rHG+7gNmM6Cm/F8MDfAnnRmsw4h6hgvcJNQT5D
ig==
=OY2W
-----END PGP PUBLIC KEY BLOCK-----
EOF
chmod 644 /etc/apt/keyrings/amnezia.gpg

OS_CODENAME="noble"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_CODENAME="${VERSION_CODENAME:-${UBUNTU_CODENAME:-noble}}"
fi

echo "deb [signed-by=/etc/apt/keyrings/amnezia.gpg] https://ppa.launchpadcontent.net/amnezia/ppa/ubuntu ${OS_CODENAME} main" > /etc/apt/sources.list.d/amnezia.list
apt-get update -qq
apt-get install -y -qq amneziawg amneziawg-tools
log_success "AmneziaWG and tools installed"

log_step "Setting up AmneziaWG directory and keys"
mkdir -p /etc/amnezia/amneziawg
chmod 700 /etc/amnezia/amneziawg

if [ ! -f /etc/amnezia/amneziawg/server_private.key ]; then
    log_info "Generating new server private key"
    awg genkey > /etc/amnezia/amneziawg/server_private.key
    chmod 600 /etc/amnezia/amneziawg/server_private.key
else
    log_info "Existing server private key found"
fi
SERVER_PRIV=$(cat /etc/amnezia/amneziawg/server_private.key)
SERVER_PUB=$(echo "${SERVER_PRIV}" | awg pubkey)
log_info "Server public key: ${SERVER_PUB}"

if [ ! -f /etc/amnezia/amneziawg/client_private.key ]; then
    log_info "Generating new client private key"
    awg genkey > /etc/amnezia/amneziawg/client_private.key
    chmod 600 /etc/amnezia/amneziawg/client_private.key
else
    log_info "Existing client private key found"
fi
CLIENT_PRIV=$(cat /etc/amnezia/amneziawg/client_private.key)
CLIENT_PUB=$(echo "${CLIENT_PRIV}" | awg pubkey)
log_info "Client public key: ${CLIENT_PUB}"

log_step "Generating server configuration (/etc/amnezia/amneziawg/awg0.conf)"
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
log_success "Server configuration created"

log_step "Generating client configuration (/etc/amnezia/amneziawg/client.conf)"
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
log_success "Client configuration created"

log_step "Starting and enabling awg-quick@awg0 service"
systemctl enable --now awg-quick@awg0
log_success "AmneziaWG awg0 service is active"

log_step "Fetching and installing SmartDNS"
SMARTDNS_DEB=$(curl -sSL https://api.github.com/repos/pymumu/smartdns/releases/latest | grep "browser_download_url.*x86_64.*\.deb" | cut -d : -f 2,3 | tr -d \" | tr -d ' ')
log_info "Downloading SmartDNS from: ${SMARTDNS_DEB}"
wget -q "${SMARTDNS_DEB}" -O /tmp/smartdns.deb
dpkg -i /tmp/smartdns.deb || apt-get install -f -y
rm -f /tmp/smartdns.deb
log_success "SmartDNS package installed"

log_step "Writing SmartDNS configuration (/etc/smartdns/smartdns.conf)"
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
log_success "SmartDNS service configured and running"

log_step "Writing nftables configuration (/etc/nftables.conf)"
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
log_success "nftables rules applied and service enabled"

log_step "Configuring Policy-Based Routing systemd service"
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
log_success "Policy-Based Routing service configured and active"

log_success "Installation completed successfully"
printf "\n"
printf "${C_GREEN}================================================================${C_RESET}\n"
printf "${C_GREEN}                      SETUP COMPLETE                            ${C_RESET}\n"
printf "${C_GREEN}================================================================${C_RESET}\n"
printf "Client configuration saved to: %s\n" "/etc/amnezia/amneziawg/client.conf"
printf "Full installation log saved to: %s\n" "${LOG_FILE}"
printf "\n"
if command -v qrencode >/dev/null 2>&1; then
    printf "${C_CYAN}Client Configuration QR Code:${C_RESET}\n"
    qrencode -t ansiutf8 < /etc/amnezia/amneziawg/client.conf
    printf "\n"
fi
