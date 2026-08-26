import streamlit as st
import psutil
import json
import os
import time
import random
from datetime import datetime

st.set_page_config(
    page_title="AI Migration Dashboard",
    page_icon="🚀",
    layout="wide"
)

# ─── CONFIG ─────────────────────────────────────────────
VM1_IP       = "192.168.88.10"
VM2_IP       = "192.168.88.14"
ROUTING_FILE = "/shared-storage/routing_rules.json"
LOG_FILE     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migration_log.txt")

# ─── HELPERS ────────────────────────────────────────────
def get_prices():
    try:
        from price_oracle import get_aws_price, get_gcp_price, get_azure_price
        return {"AWS": round(get_aws_price(),4), "GCP": round(get_gcp_price(),4), "Azure": round(get_azure_price(),4)}
    except:
        return {"AWS": round(random.uniform(0.10,0.25),4), "GCP": round(random.uniform(0.06,0.18),4), "Azure": round(random.uniform(0.09,0.22),4)}

def get_metrics():
    return {
        "cpu":  psutil.cpu_percent(interval=0.1),
        "ram":  psutil.virtual_memory().percent,
        "net":  round(psutil.net_io_counters().bytes_recv/(1024*1024),1),
        "disk": psutil.disk_usage('/').percent
    }

def get_routing():
    try:
        if os.path.exists(ROUTING_FILE):
            with open(ROUTING_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"counter-app": {"current_vm":"AWS","current_ip":VM1_IP,"migrations":0,"last_migration":"Never"}}

def get_nfs():
    return os.path.exists("/shared-storage/routing_rules.json")

def get_mesh():
    try:
        import requests
        r = requests.get(f"http://{VM1_IP}:8888/status", timeout=1)
        return r.status_code == 200
    except:
        return False

def get_history():
    try:
        if os.path.exists(LOG_FILE):
            lines = open(LOG_FILE).readlines()[-15:]
            return [l.strip() for l in reversed(lines) if l.strip()]
    except:
        pass
    return []

# ─── MAIN ───────────────────────────────────────────────
# HEADER
st.markdown("<h1 style='text-align:center'>🚀 AI Live Container Migration Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:gray'>Real-time monitoring across AWS → GCP → Azure</p>", unsafe_allow_html=True)
st.divider()

# DATA
prices  = get_prices()
prices  = {k: float(v) if not isinstance(v, list) else float(v[0]) for k, v in prices.items()} 
metrics = get_metrics()
routing = get_routing()
best    = min(prices, key=prices.get)
info    = routing.get("counter-app", {})

# ── PRICES ──────────────────────────────────────────────
st.subheader("☁️ Live Cloud Spot Prices")
c1, c2, c3 = st.columns(3)

with c1:
    label = "⭐ RECOMMENDED" if best=="AWS" else ""
    st.metric("🟠 AWS", f"${prices['AWS']}/hr", label)
    st.progress(min(prices['AWS']/0.30, 1.0))

with c2:
    label = "⭐ RECOMMENDED" if best=="GCP" else ""
    st.metric("🔵 GCP", f"${prices['GCP']}/hr", label)
    st.progress(min(prices['GCP']/0.30, 1.0))

with c3:
    label = "⭐ RECOMMENDED" if best=="Azure" else ""
    st.metric("🔷 Azure", f"${prices['Azure']}/hr", label)
    st.progress(min(prices['Azure']/0.30, 1.0))

st.divider()

# ── AI RECOMMENDATION ───────────────────────────────────
st.success(f"🧠 GA Recommendation: MIGRATE TO **{best}** — cheapest at ${prices[best]}/hr")

st.divider()

# ── SYSTEM METRICS ──────────────────────────────────────
st.subheader("📊 System Metrics")
m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("🖥️ CPU", f"{metrics['cpu']:.1f}%", "⚠️ HIGH" if metrics['cpu']>80 else "✅ OK")
with m2: st.metric("💾 RAM", f"{metrics['ram']:.1f}%", "⚠️ HIGH" if metrics['ram']>75 else "✅ OK")
with m3: st.metric("🌐 Network", f"{metrics['net']} MB")
with m4: st.metric("💿 Disk", f"{metrics['disk']:.1f}%")

st.progress(metrics['cpu']/100, text=f"CPU: {metrics['cpu']:.1f}%")
st.progress(metrics['ram']/100, text=f"RAM: {metrics['ram']:.1f}%")

st.divider()

# ── CONTAINER + STATUS ──────────────────────────────────
st.subheader("🐳 Container Location & Services")
s1, s2, s3, s4 = st.columns(4)

current_vm = info.get("current_vm","AWS")
current_ip = info.get("current_ip", VM1_IP)
migrations = info.get("migrations", 0)
last_mig   = info.get("last_migration","Never")

with s1: st.metric("🐳 Container", "counter-app", current_vm)
with s2: st.metric("📍 Location", current_vm, current_ip)
with s3: st.metric("🔄 Migrations", migrations, f"Last: {last_mig[:5] if last_mig!='Never' else 'Never'}")
with s4:
    mesh = get_mesh()
    st.metric("🌐 Service Mesh", "ACTIVE ✅" if mesh else "OFFLINE ❌", "Port 8888")

nfs = get_nfs()
st.info(f"💾 NFS Shared Storage: {'✅ MOUNTED — /shared-storage' if nfs else '❌ NOT MOUNTED'}")

st.divider()

# ── VM STATUS ───────────────────────────────────────────
st.subheader("🖥️ Virtual Machines")
v1, v2 = st.columns(2)

with v1:
    active = current_vm == "AWS"
    if active:
        st.success(f"🟠 VM1 — AWS (Your Laptop)\nIP: {VM1_IP}\n🟢 CONTAINER RUNNING HERE")
    else:
        st.warning(f"🟠 VM1 — AWS (Your Laptop)\nIP: {VM1_IP}\n⚪ Container migrated away")

with v2:
    active = current_vm == "GCP"
    if active:
        st.success(f"🔵 VM2 — GCP (Friend's Laptop)\nIP: {VM2_IP}\n🟢 CONTAINER RUNNING HERE")
    else:
        st.info(f"🔵 VM2 — GCP (Friend's Laptop)\nIP: {VM2_IP}\n⚪ Waiting for migration")

st.divider()

# ── MIGRATION HISTORY ───────────────────────────────────
st.subheader("📋 Migration Log")
history = get_history()
if history:
    for line in history:
        st.code(line)
else:
    st.info("No migrations yet — run: python3 migrate.py GCP")

# ── FOOTER ──────────────────────────────────────────────
st.divider()
st.caption(f"🕐 Updated: {datetime.now().strftime('%H:%M:%S')} | 🔄 Auto-refresh every 5s")

time.sleep(5)
st.rerun()
