#!/usr/bin/env python3 
# ═══════════════════════════════════════════════════════ 
#   SERVICE_MESH.PY — Layer 3: The Bridge (Istio-style) 
#   Manages traffic routing between AWS and GCP VMs 
# ═══════════════════════════════════════════════════════ 
 
import http.server 
import json 
import subprocess 
import threading 
import time 
import os 
import socket 
from datetime import datetime 
 
# ─── CONFIG ───────────────────────────────────────────── 
MESH_PORT     = 8888 
VM1_IP        = "192.168.88.10"   # YOUR VM (AWS) 
VM2_IP        = "192.168.88.10"   # SAME VM (GCP target container)
ROUTING_FILE  = "/shared-storage/routing_rules.json" 
LOG_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mesh_log.txt") 
 
# ─── ROUTING TABLE ────────────────────────────────────── 
routing_table = { 
    "counter-app": { 
        "current_vm": "AWS", 
        "current_ip": VM1_IP, 
        "port": 8080, 
        "status": "running", 
        "migrations": 0, 
        "last_migration": None 
    } 
} 
 
# ─── HELPERS ──────────────────────────────────────────── 
def log(msg): 
    ts = datetime.now().strftime("%H:%M:%S") 
    line = f"[{ts}] {msg}" 
    print(line) 
    with open(LOG_FILE, "a") as f: 
        f.write(line + "\n") 
 
def save_routing_rules(): 
    """Save routing rules to shared NFS storage — visible to ALL VMs""" 
    try: 
        os.makedirs("/shared-storage", exist_ok=True) 
        with open(ROUTING_FILE, "w") as f: 
            json.dump(routing_table, f, indent=2) 
        log(f"Routing rules saved to shared storage") 
    except Exception as e: 
        log(f"Could not save to shared storage: {e}") 
 
def load_routing_rules(): 
    """Load routing rules from shared NFS storage""" 
    try: 
        if os.path.exists(ROUTING_FILE): 
            with open(ROUTING_FILE) as f: 
                return json.load(f) 
    except: 
        pass 
    return routing_table 
 
def get_my_ip(): 
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    try: 
        s.connect(("8.8.8.8", 80)) 
        return s.getsockname()[0] 
    except: 
        return "unknown" 
    finally: 
        s.close() 
 
# ─── SERVICE MESH HANDLER ─────────────────────────────── 
class MeshHandler(http.server.BaseHTTPRequestHandler): 
 
    def log_message(self, format, *args): 
        pass  # suppress default logs 
 
    def send_json(self, code, data): 
        self.send_response(code) 
        self.send_header("Content-Type", "application/json") 
        self.end_headers() 
        self.wfile.write(json.dumps(data, indent=2).encode()) 
 
    def do_GET(self): 
 
        # ── GET /status ────────────────────────────────── 
        if self.path == "/status": 
            my_ip = get_my_ip() 
            self.send_json(200, { 
                "service_mesh": "ACTIVE", 
                "my_ip": my_ip, 
                "routing_table": routing_table, 
                "timestamp": datetime.now().strftime("%H:%M:%S") 
            }) 
 
        # ── GET /route/{service} ───────────────────────── 
        elif self.path.startswith("/route/"): 
            service = self.path.split("/route/")[1] 
            if service in routing_table: 
                rule = routing_table[service] 
                log(f"Traffic request for '{service}' → routing to {rule['current_vm']} ({rule['current_ip']})") 
                self.send_json(200, { 
                    "service": service, 
                    "route_to": rule["current_ip"], 
                    "cloud": rule["current_vm"], 
                    "status": rule["status"], 
                    "message": f"Traffic routed to {rule['current_vm']}" 
                }) 
            else: 
                self.send_json(404, {"error": f"Service '{service}' not found"}) 
 
        # ── GET /rules ─────────────────────────────────── 
        elif self.path == "/rules": 
            self.send_json(200, load_routing_rules()) 
 
        else: 
            self.send_json(404, {"error": "Unknown endpoint"}) 
 
    def do_POST(self): 
 
        # ── POST /migrate ──────────────────────────────── 
        if self.path == "/migrate": 
            length = int(self.headers.get("Content-Length", 0)) 
            body = json.loads(self.rfile.read(length)) 
            service   = body.get("service", "counter-app") 
            target_vm = body.get("target_vm", "GCP") 
            target_ip = body.get("target_ip", VM2_IP) 
 
            old_vm = routing_table.get(service, {}).get("current_vm", "AWS") 
            log(f"MIGRATION EVENT: {service} → {old_vm} to {target_vm} ({target_ip})") 
 
            # Update routing rules 
            if service not in routing_table: 
                routing_table[service] = {} 
 
            routing_table[service].update({ 
                "current_vm": target_vm, 
                "current_ip": target_ip, 
                "status": "migrating", 
                "migrations": routing_table[service].get("migrations", 0) + 1, 
                "last_migration": datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
            }) 
 
            log(f"Routing rules updated: {service} now on {target_vm}") 
            time.sleep(0.5) 
            routing_table[service]["status"] = "running" 
 
            # Save to shared NFS storage 
            save_routing_rules() 
 
            self.send_json(200, { 
                "message": f"Traffic rerouted from {old_vm} to {target_vm}", 
                "service": service, 
                "new_ip": target_ip, 
                "routing_table": routing_table 
            }) 
 
        else: 
            self.send_json(404, {"error": "Unknown endpoint"}) 
 
# ─── MONITOR THREAD ───────────────────────────────────── 
def monitor_routing(): 
    """Continuously watch for routing changes in shared storage""" 
    last_rules = {} 
    while True: 
        try: 
            current_rules = load_routing_rules() 
            if current_rules != last_rules: 
                for service, rule in current_rules.items(): 
                    old_rule = last_rules.get(service, {}) 
                    if old_rule.get("current_vm") != rule.get("current_vm"): 
                        log(f"ROUTING CHANGE DETECTED: {service} → {rule['current_vm']} ({rule['current_ip']})") 
                last_rules = current_rules 
        except: 
            pass 
        time.sleep(2) 
 
# ─── MAIN ─────────────────────────────────────────────── 
def main(): 
    my_ip = get_my_ip() 
    print("=" * 55) 
    print(f"  SERVICE MESH — Layer 3: The Bridge (Istio-style)") 
    print(f"  Running on: {my_ip}:{MESH_PORT}") 
    print(f"  VM1 (AWS):  {VM1_IP}") 
    print(f"  VM2 (GCP):  {VM2_IP}") 
    print("=" * 55) 
 
    # Save initial routing rules 
    save_routing_rules() 
    log(f"Service mesh started on {my_ip}:{MESH_PORT}") 
    log(f"Initial routing: counter-app → AWS ({VM1_IP})") 
 
    # Start monitor thread 
    t = threading.Thread(target=monitor_routing, daemon=True) 
    t.start() 
 
    # Start HTTP server 
    print(f"\nEndpoints available:") 
    print(f"  GET  http://{my_ip}:{MESH_PORT}/status") 
    print(f"  GET  http://{my_ip}:{MESH_PORT}/route/counter-app") 
    print(f"  GET  http://{my_ip}:{MESH_PORT}/rules") 
    print(f"  POST http://{my_ip}:{MESH_PORT}/migrate") 
    print(f"\nWaiting for traffic...\n") 
 
    server = http.server.HTTPServer(("0.0.0.0", MESH_PORT), MeshHandler) 
    server.serve_forever() 
 
if __name__ == "__main__": 
    main()
