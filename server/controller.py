import json
import os
import subprocess
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request

AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "sec_7d4874b68cc6ff2ff55d81ce6a69f29f6912eb7d")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "wprhvso/mesh")
PORT = int(os.environ.get("PORT", "51822"))
WG_IFACE = "wg-mesh"
DEFAULT_GW = os.environ.get("DEFAULT_GW", "91.230.210.1")
DEFAULT_IFACE = os.environ.get("DEFAULT_IFACE", "ens3")

nodes_lock = threading.Lock()
nodes = {}

subprocess.run(["modprobe", "ipip"], check=False)

def get_server_pubkey():
    try:
        with open("/etc/wireguard/mesh_public.key") as f:
            return f.read().strip()
    except Exception:
        res = subprocess.run(["wg", "show", WG_IFACE, "public-key"], capture_output=True, text=True)
        return res.stdout.strip()

SERVER_PUBKEY = get_server_pubkey()

class MeshHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        if self.path == "/register":
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {AUTH_TOKEN}":
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"error": "unauthorized"}')
                return

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                node_id = int(data["node_id"])
                pubkey = str(data["pubkey"]).strip()
            except Exception:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "invalid payload"}')
                return

            ip = f"10.200.0.{node_id + 10}"
            tun_name = f"tun{node_id}"
            tun_client_ip = f"10.254.{node_id}.2"
            tun_server_ip = f"10.254.{node_id}.1"

            subprocess.run([
                "wg", "set", WG_IFACE,
                "peer", pubkey,
                "allowed-ips", f"{ip}/32",
                "persistent-keepalive", "15"
            ], check=False)

            subprocess.run(["ip", "tunnel", "del", tun_name], stderr=subprocess.DEVNULL)
            subprocess.run([
                "ip", "tunnel", "add", tun_name, "mode", "ipip",
                "remote", ip, "local", "10.200.0.1", "dev", WG_IFACE
            ], check=False)
            subprocess.run(["ip", "addr", "add", f"{tun_server_ip}/30", "dev", tun_name], check=False)
            subprocess.run(["ip", "link", "set", tun_name, "mtu", "1380", "up"], check=False)

            with nodes_lock:
                nodes[node_id] = {
                    "ip": ip,
                    "tun": tun_name,
                    "tun_client_ip": tun_client_ip,
                    "tun_server_ip": tun_server_ip,
                    "pubkey": pubkey,
                    "registered_at": time.time(),
                    "healthy": False
                }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "status": "ok",
                "ip": ip,
                "tun_server_ip": tun_server_ip,
                "tun_client_ip": tun_client_ip,
                "server_pubkey": SERVER_PUBKEY,
                "server_port": 51821
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/status":
            with nodes_lock:
                snapshot = dict(nodes)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"nodes": snapshot}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def update_routing():
    last_healthy = []
    last_dispatch = 0

    while True:
        with nodes_lock:
            current_nodes = list(nodes.items())

        healthy_tuns = []
        for nid, info in current_nodes:
            client_ip = info["tun_client_ip"]
            res = subprocess.run(["ping", "-c", "1", "-W", "1", client_ip], stdout=subprocess.DEVNULL)
            is_healthy = (res.returncode == 0)
            with nodes_lock:
                if nid in nodes:
                    nodes[nid]["healthy"] = is_healthy
            if is_healthy:
                healthy_tuns.append((info["tun"], client_ip))

        if healthy_tuns != last_healthy:
            if healthy_tuns:
                nexthops = []
                for tun, client_ip in healthy_tuns:
                    nexthops.extend(["nexthop", "via", client_ip, "dev", tun, "weight", "1"])
                cmd = ["ip", "route", "replace", "default", "scope", "global", "table", "200"] + nexthops
                subprocess.run(cmd, check=False)
            else:
                subprocess.run([
                    "ip", "route", "replace", "default", "via", DEFAULT_GW,
                    "dev", DEFAULT_IFACE, "table", "200"
                ], check=False)
            last_healthy = list(healthy_tuns)

        if GITHUB_TOKEN and (time.time() - last_dispatch > 300) and (len(healthy_tuns) < 15):
            try:
                url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/mesh.yml/dispatches"
                req = urllib.request.Request(url, data=json.dumps({"ref": "main"}).encode(), headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json"
                })
                urllib.request.urlopen(req, timeout=10)
                last_dispatch = time.time()
            except Exception:
                pass

        time.sleep(5)

def main():
    threading.Thread(target=update_routing, daemon=True).start()
    server = HTTPServer(("0.0.0.0", PORT), MeshHandler)
    server.serve_forever()

if __name__ == "__main__":
    main()
