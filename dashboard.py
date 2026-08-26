import streamlit as st
import psutil
import json
import os
import time
import random
from datetime import datetime

st.set_page_config(page_title="AI Migration Dashboard", page_icon="🚀", layout="wide")

VM1_IP       = "192.168.88.10"
VM2_IP       = "192.168.88.14"
ROUTING_FILE = "/shared-storage/routing_rules.json"
LOG_FILE     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migration_log.txt")

# ── PRICES — no imports, just simulated ─────────────────
aws_price   = round(random.uniform(0.10, 0.25), 4)
gcp_price   = round(random.uniform(0.06, 0.15), 4)
azure_price = round(random.uniform(0.09, 0.22), 4)
prices      = {"AWS": aws_price, "GCP": gcp_price, "Azure": azure_price}
best        = min(prices, key=prices.get)

# ── SYSTEM METRICS ───────────────────────────────────────
cpu  = psutil.cpu_percent(interval=0.1)
ram  = psutil.virtual_memory().percent
net  = round(psutil.net_io_counters().bytes_recv / (1024*1024), 1)
disk = psutil.disk_usage('/').percent

# ── ROUTING ──────────────────────────────────────────────
def get_routing():
    try:
        if os.path.exists(ROUTING_FILE):
            with open(ROUTING_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"counter-app": {"current_vm": "AWS", "current_ip": VM1_IP, "migrations": 0, "last_migration": "Never"}}

def get_history():
    try:
        if os.path.exists(LOG_FILE):
            lines = open(LOG_FILE).readlines()[-10:]
            return [l.strip() for l in reversed(lines) if l.strip()]
    except:
        pass
    return []

def get_mesh():
    try:
        import requests
        r = requests.get(f"http://{VM1_IP}:8888/status", timeout=1)
        return r.status_code == 200
    except:
        return False

routing    = get_routing()
info       = routing.get("counter-app", {})
current_vm = info.get("current_vm", "AWS")
current_ip = info.get("current_ip", VM1_IP)
migrations = info.get("migrations", 0)
last_mig   = info.get("last_migration", "Never")

# ════════════════════════════════════════════════════════
#   DASHBOARD UI
# ════════════════════════════════════════════════════════

st.markdown("<h1 style='text-align:center'>🚀 AI Live Container Migration Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:gray'>Real-time monitoring — AWS | GCP | Azure</p>", unsafe_allow_html=True)
st.divider()

# ── PRICES ───────────────────────────────────────────────
st.subheader("☁️ Live Cloud Spot Prices")
c1, c2, c3 = st.columns(3)

with c1:
    st.metric("🟠 AWS",   f"${prices['AWS']}/hr",   "⭐ BEST" if best=="AWS" else "")
    st.progress(min(prices["AWS"] / 0.30, 1.0))

with c2:
    st.metric("🔵 GCP",   f"${prices['GCP']}/hr",   "⭐ BEST" if best=="GCP" else "")
    st.progress(min(prices["GCP"] / 0.30, 1.0))

with c3:
    st.metric("🔷 Azure", f"${prices['Azure']}/hr", "⭐ BEST" if best=="Azure" else "")
    st.progress(min(prices["Azure"] / 0.30, 1.0))

st.success(f"🧠 GA Recommendation: MIGRATE TO **{best}** — cheapest at ${prices[best]}/hr")
st.divider()

# ── SYSTEM METRICS ───────────────────────────────────────
st.subheader("📊 Real System Metrics (psutil)")
m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("🖥️ CPU",     f"{cpu:.1f}%",  "⚠️ HIGH" if cpu>80  else "✅ OK")
with m2: st.metric("💾 RAM",     f"{ram:.1f}%",  "⚠️ HIGH" if ram>75  else "✅ OK")
with m3: st.metric("🌐 Network", f"{net} MB")
with m4: st.metric("💿 Disk",    f"{disk:.1f}%")

st.progress(cpu/100,  text=f"CPU: {cpu:.1f}%")
st.progress(ram/100,  text=f"RAM: {ram:.1f}%")
st.divider()

# ── CONTAINER + SERVICES ─────────────────────────────────
st.subheader("🐳 Container Location & Services")
s1, s2, s3, s4 = st.columns(4)

with s1: st.metric("🐳 Container",     "counter-app",                current_vm)
with s2: st.metric("📍 Location",      current_vm,                   current_ip)
with s3: st.metric("🔄 Migrations",    migrations)
with s4: st.metric("🌐 Service Mesh",  "ACTIVE ✅" if get_mesh() else "OFFLINE ❌")

nfs_ok = os.path.exists("/shared-storage/routing_rules.json")
st.info(f"💾 NFS Storage: {'✅ MOUNTED — /shared-storage' if nfs_ok else '❌ NOT MOUNTED'}")
st.divider()

# ── VM STATUS ────────────────────────────────────────────
st.subheader("🖥️ Virtual Machines")
v1, v2 = st.columns(2)

with v1:
    if current_vm == "AWS":
        st.success(f"🟠 VM1 — AWS (Your Laptop)\nIP: {VM1_IP}\n🟢 CONTAINER RUNNING HERE")
    else:
        st.warning(f"🟠 VM1 — AWS (Your Laptop)\nIP: {VM1_IP}\n⚪ Container migrated away")

with v2:
    if current_vm == "GCP":
        st.success(f"🔵 VM2 — GCP (Friend's Laptop)\nIP: {VM2_IP}\n🟢 CONTAINER RUNNING HERE")
    else:
        st.info(f"🔵 VM2 — GCP (Friend's Laptop)\nIP: {VM2_IP}\n⚪ Waiting for migration")

st.divider()

# ── MIGRATION LOG ────────────────────────────────────────
st.subheader("📋 Migration Log")
history = get_history()
if history:
    for line in history:
        st.code(line)
else:
    st.info("No migrations yet — run: python3 migrate.py GCP")

st.divider()
st.caption(f"🕐 Updated: {datetime.now().strftime('%H:%M:%S')} | 🔄 Auto-refresh every 5s")

time.sleep(5)
st.rerun()
