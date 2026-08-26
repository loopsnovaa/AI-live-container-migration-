# ═══════════════════════════════════════════════════════
#   DASHBOARD.PY — AI Live Container Migration Dashboard
#   Layer: Visualization & Monitoring
# ═══════════════════════════════════════════════════════

import streamlit as st
import psutil
import json
import os
import time
import requests
import random
from datetime import datetime

# ─── PAGE CONFIG ────────────────────────────────────────
st.set_page_config(
    page_title="AI Migration Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── CONFIG ─────────────────────────────────────────────
VM1_IP         = "192.168.88.10"
VM2_IP         = "192.168.88.14"
MESH_URL       = f"http://{VM1_IP}:8888"
ROUTING_FILE   = "/shared-storage/routing_rules.json"
LOG_FILE       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migration_log.txt")
REFRESH_SEC    = 5

# ─── CSS STYLING ────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: #1e2130;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        border: 1px solid #2d3250;
    }
    .cloud-aws  { border-left: 4px solid #ff9900; }
    .cloud-gcp  { border-left: 4px solid #4285f4; }
    .cloud-az   { border-left: 4px solid #00a4ef; }
    .recommend  { border-left: 4px solid #00ff88; }
    .status-ok  { color: #00ff88; font-weight: bold; }
    .status-bad { color: #ff4444; font-weight: bold; }
    .big-title  { font-size: 2.5rem; font-weight: 800; text-align: center; }
</style>
""", unsafe_allow_html=True)

# ─── HELPERS ────────────────────────────────────────────
def get_prices():
    """Get real or simulated cloud prices"""
    try:
        from price_oracle import get_aws_price, get_gcp_price, get_azure_price
        return {
            "AWS":   round(get_aws_price(), 4),
            "GCP":   round(get_gcp_price(), 4),
            "Azure": round(get_azure_price(), 4)
        }
    except:
        return {
            "AWS":   round(random.uniform(0.08, 0.25), 4),
            "GCP":   round(random.uniform(0.06, 0.20), 4),
            "Azure": round(random.uniform(0.09, 0.27), 4)
        }

def get_recommendation():
    """Get GA recommendation"""
    try:
        from predictor import collect_prices, get_system_metrics, run_ga, CLOUDS
        prices = collect_prices()
        metrics = get_system_metrics()
        best = run_ga(prices, metrics)
        return best, prices, metrics
    except Exception as e:
        prices = get_prices()
        best = min(prices, key=prices.get)
        metrics = {"cpu": psutil.cpu_percent(interval=0.1),
                   "ram": psutil.virtual_memory().percent,
                   "net": psutil.net_io_counters().bytes_recv / (1024*1024)}
        return best, prices, metrics

def get_system_metrics():
    return {
        "cpu": psutil.cpu_percent(interval=0.1),
        "ram": psutil.virtual_memory().percent,
        "net": round(psutil.net_io_counters().bytes_recv / (1024*1024), 1),
        "disk": psutil.disk_usage('/').percent
    }

def get_routing():
    """Get routing info from service mesh or shared storage"""
    try:
        r = requests.get(f"{MESH_URL}/rules", timeout=2)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    try:
        if os.path.exists(ROUTING_FILE):
            with open(ROUTING_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"counter-app": {"current_vm": "AWS", "current_ip": VM1_IP, "migrations": 0}}

def get_mesh_status():
    try:
        r = requests.get(f"{MESH_URL}/status", timeout=2)
        return r.status_code == 200, r.json() if r.status_code == 200 else {}
    except:
        return False, {}

def get_nfs_status():
    return os.path.ismount("/shared-storage") or os.path.exists("/shared-storage/routing_rules.json")

def get_migration_history():
    history = []
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                lines = f.readlines()[-20:]
            for line in reversed(lines):
                line = line.strip()
                if line:
                    history.append(line)
    except:
        pass
    return history[:10]

def trend_arrow(price, avg=0.15):
    if price > avg * 1.1:
        return "🔴 HIGH"
    elif price < avg * 0.9:
        return "🟢 LOW"
    else:
        return "🟡 STABLE"

# ═══════════════════════════════════════════════════════
#   MAIN DASHBOARD
# ═══════════════════════════════════════════════════════
def main():

    # ── HEADER ──────────────────────────────────────────
    st.markdown("""
    <div class='big-title'>
        🚀 AI Live Container Migration Dashboard
    </div>
    <p style='text-align:center; color:#888; margin-top:-10px;'>
        Real-time monitoring across AWS → GCP → Azure
    </p>
    """, unsafe_allow_html=True)

    st.divider()

    # ── FETCH DATA ──────────────────────────────────────
    with st.spinner("Fetching live data..."):
        prices     = get_prices()
        metrics    = get_system_metrics()
        routing    = get_routing()
        mesh_ok, _ = get_mesh_status()
        nfs_ok     = get_nfs_status()

    try:
        best_cloud, _, _ = get_recommendation()
    except:
        best_cloud = min(prices, key=prices.get)

    # ── ROW 1: CLOUD PRICES ─────────────────────────────
    st.subheader("☁️ Live Cloud Spot Prices")
    c1, c2, c3 = st.columns(3)

    cloud_colors = {"AWS": "#ff9900", "GCP": "#4285f4", "Azure": "#00a4ef"}
    cloud_icons  = {"AWS": "🟠", "GCP": "🔵", "Azure": "🔷"}

    for col, (cloud, price) in zip([c1, c2, c3], prices.items()):
        is_best = cloud == best_cloud
        with col:
            st.markdown(f"""
            <div class='metric-card cloud-{"aws" if cloud=="AWS" else "gcp" if cloud=="GCP" else "az"}'>
                <h2 style='color:{cloud_colors[cloud]}'>{cloud_icons[cloud]} {cloud}</h2>
                <h1 style='color:{"#00ff88" if is_best else "white"}; font-size:2.5rem'>
                    ${price}/hr
                </h1>
                <p style='color:#aaa'>{trend_arrow(price)}</p>
                {"<p style='color:#00ff88; font-weight:bold'>⭐ GA RECOMMENDED</p>" if is_best else ""}
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── ROW 2: SYSTEM METRICS + RECOMMENDATION ──────────
    st.subheader("📊 System Metrics & AI Recommendation")
    m1, m2, m3, m4, m5 = st.columns(5)

    cpu_color = "#ff4444" if metrics["cpu"] > 80 else "#00ff88"
    ram_color = "#ff4444" if metrics["ram"] > 75 else "#00ff88"

    with m1:
        st.metric("🖥️ CPU Usage", f"{metrics['cpu']:.1f}%",
                  delta=f"{'⚠️ HIGH' if metrics['cpu']>80 else 'OK'}")
    with m2:
        st.metric("💾 RAM Usage", f"{metrics['ram']:.1f}%",
                  delta=f"{'⚠️ HIGH' if metrics['ram']>75 else 'OK'}")
    with m3:
        st.metric("🌐 Network", f"{metrics['net']:.1f} MB")
    with m4:
        st.metric("💿 Disk", f"{metrics['disk']:.1f}%")
    with m5:
        st.markdown(f"""
        <div class='metric-card recommend'>
            <p style='color:#aaa; margin:0'>🧠 GA Recommends</p>
            <h2 style='color:#00ff88; margin:5px 0'>{best_cloud}</h2>
            <p style='color:#aaa; margin:0'>${prices[best_cloud]}/hr</p>
        </div>
        """, unsafe_allow_html=True)

    # ── CPU/RAM PROGRESS BARS ───────────────────────────
    st.progress(metrics["cpu"] / 100, text=f"CPU: {metrics['cpu']:.1f}%")
    st.progress(metrics["ram"] / 100, text=f"RAM: {metrics['ram']:.1f}%")

    st.divider()

    # ── ROW 3: CONTAINER LOCATION + SERVICE STATUS ──────
    st.subheader("🐳 Container Location & Service Status")
    l1, l2, l3, l4 = st.columns(4)

    container_info = routing.get("counter-app", {})
    current_vm  = container_info.get("current_vm", "AWS")
    current_ip  = container_info.get("current_ip", VM1_IP)
    migrations  = container_info.get("migrations", 0)
    last_mig    = container_info.get("last_migration", "Never")

    with l1:
        st.markdown(f"""
        <div class='metric-card'>
            <p style='color:#aaa'>🐳 Container</p>
            <h3>counter-app</h3>
            <p style='color:#00ff88'>{current_vm} ({current_ip})</p>
        </div>
        """, unsafe_allow_html=True)

    with l2:
        st.markdown(f"""
        <div class='metric-card'>
            <p style='color:#aaa'>🔄 Total Migrations</p>
            <h1 style='color:#4285f4'>{migrations}</h1>
            <p style='color:#aaa'>Last: {last_mig}</p>
        </div>
        """, unsafe_allow_html=True)

    with l3:
        status_color = "#00ff88" if mesh_ok else "#ff4444"
        status_text  = "ACTIVE ✅" if mesh_ok else "OFFLINE ❌"
        st.markdown(f"""
        <div class='metric-card'>
            <p style='color:#aaa'>🌐 Service Mesh</p>
            <h3 style='color:{status_color}'>{status_text}</h3>
            <p style='color:#aaa'>Port 8888</p>
        </div>
        """, unsafe_allow_html=True)

    with l4:
        nfs_color = "#00ff88" if nfs_ok else "#ff4444"
        nfs_text  = "MOUNTED ✅" if nfs_ok else "OFFLINE ❌"
        st.markdown(f"""
        <div class='metric-card'>
            <p style='color:#aaa'>💾 NFS Storage</p>
            <h3 style='color:{nfs_color}'>{nfs_text}</h3>
            <p style='color:#aaa'>/shared-storage</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── ROW 4: VM STATUS ────────────────────────────────
    st.subheader("🖥️ Virtual Machines")
    v1, v2 = st.columns(2)

    with v1:
        is_active = current_vm == "AWS"
        st.markdown(f"""
        <div class='metric-card cloud-aws'>
            <h3>🟠 VM1 — AWS (Your Laptop)</h3>
            <p>IP: {VM1_IP}</p>
            <p style='color:{"#00ff88" if is_active else "#888"}'>
                {'🟢 CONTAINER RUNNING HERE' if is_active else '⚪ Container migrated away'}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with v2:
        is_active = current_vm == "GCP"
        st.markdown(f"""
        <div class='metric-card cloud-gcp'>
            <h3>🔵 VM2 — GCP (Friend's Laptop)</h3>
            <p>IP: {VM2_IP}</p>
            <p style='color:{"#00ff88" if is_active else "#888"}'>
                {'🟢 CONTAINER RUNNING HERE' if is_active else '⚪ Waiting for migration'}
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── ROW 5: MIGRATION HISTORY ────────────────────────
    st.subheader("📋 Migration Log")
    history = get_migration_history()
    if history:
        for line in history:
            st.code(line, language=None)
    else:
        st.info("No migration history yet — run migrate.py to start!")

    # ── FOOTER ──────────────────────────────────────────
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"🕐 Last updated: {datetime.now().strftime('%H:%M:%S')}")
    with col2:
        st.caption("🔄 Auto-refreshes every 5 seconds")
    with col3:
        st.caption("🚀 AI Live Container Migration System")

    # ── AUTO REFRESH ────────────────────────────────────
    time.sleep(REFRESH_SEC)
    st.rerun()

if __name__ == "__main__":
    main()
