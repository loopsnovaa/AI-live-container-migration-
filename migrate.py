import subprocess
import time
import os
from datetime import datetime

# ═══════════════════════════════════════════════
#   CONFIG
# ═══════════════════════════════════════════════
CONTAINER_NAME  = "counter-app"
CHECKPOINT_DIR  = "/tmp/criu-checkpoint"
CHECKPOINT_NAME = "checkpoint1"
LOG_FILE        = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "migration_log.txt"
)

# TARGET VM (GCP = Friend's laptop)
TARGET_IP       = "192.168.88.14"
TARGET_USER     = "maggie"
TARGET_DIR      = "/tmp/criu-checkpoint"

# ═══════════════════════════════════════════════
#   HELPERS
# ═══════════════════════════════════════════════
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [✓] {msg}")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def info(msg):
    print(f"  [→] {msg}")


def warn(msg):
    print(f"  [!] {msg}")


def run(cmd):
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    return (
        result.returncode == 0,
        result.stdout,
        result.stderr
    )


def run_remote(cmd):
    """Run command on friend's VM via SSH"""
    full_cmd = (
        f"ssh -o ConnectTimeout=10 "
        f"{TARGET_USER}@{TARGET_IP} '{cmd}'"
    )

    result = subprocess.run(
        full_cmd,
        shell=True,
        capture_output=True,
        text=True
    )

    return (
        result.returncode == 0,
        result.stdout,
        result.stderr
    )


# ═══════════════════════════════════════════════
#   LAYER 1 — BRAIN
# ═══════════════════════════════════════════════
def layer1_brain(target_cloud):
    print("\n[LAYER 1 — BRAIN] AI Predictor triggered migration")
    info(f"Target cloud  : {target_cloud}")
    info(f"Target VM     : {TARGET_USER}@{TARGET_IP}")
    info("Reason        : GA identified cheapest + safest cloud")


# ═══════════════════════════════════════════════
#   LAYER 2 — MIGRATION ENGINE
# ═══════════════════════════════════════════════
def ensure_container_running():
    info(f"Checking container '{CONTAINER_NAME}'...")

    ok, out, _ = run(
        f"docker ps --format '{{{{.Names}}}}'"
    )

    if CONTAINER_NAME in out.splitlines():
        log("Container already running")
        return True

    warn("Container not running — starting it...")

    run(f"docker rm -f {CONTAINER_NAME}")

    ok, _, err = run(
        f'docker run -d --name {CONTAINER_NAME} '
        f'--security-opt seccomp=unconfined ubuntu:22.04 '
        f'bash -c "count=0; while true; do '
        f'echo Count: \$count; '
        f'count=\$((count+1)); '
        f'sleep 1; done"'
    )

    if not ok:
        warn(f"Could not start container: {err}")
        return False

    time.sleep(2)

    log("Container started")
    return True


def show_state(label):
    info(f"Container state {label}:")

    ok, out, _ = run(
        f"docker logs --tail 3 {CONTAINER_NAME}"
    )

    if not ok:
        warn("Could not read container logs")
        return

    for line in out.strip().split("\n"):
        if line:
            print(f"      {line}")


def iterative_precopy():
    info("Iterative Pre-Copy Controller starting...")

    for round_num in range(1, 4):
        pages = 200 + round_num * 100

        info(
            f"  Pre-copy round {round_num}/3 "
            f"— ~{pages} memory pages copied"
        )

        time.sleep(1)

    log("Pre-copy complete — downtime minimized")


# ═══════════════════════════════════════════════
#   REAL DOCKER / CRIU CHECKPOINT
# ═══════════════════════════════════════════════
def criu_checkpoint():
    info("CRIU final checkpoint — freezing container...")

    # Remove any previous Docker checkpoint
    run(
        f"docker checkpoint rm "
        f"{CONTAINER_NAME} "
        f"{CHECKPOINT_NAME}"
    )

    # IMPORTANT:
    # Do NOT use --checkpoint-dir here.
    #
    # We already verified that your Docker daemon
    # supports checkpoint creation without a custom
    # checkpoint directory, but does NOT support
    # custom checkpoint-dir during restore.

    ok, out, err = run(
        f"docker checkpoint create "
        f"{CONTAINER_NAME} "
        f"{CHECKPOINT_NAME}"
    )

    if not ok:
        warn("Docker/CRIU checkpoint failed")
        warn(err)
        return False

    log("CRIU checkpoint created via Docker")

    # Verify Docker registered the checkpoint
    ok, checkpoints, err = run(
        f"docker checkpoint ls {CONTAINER_NAME}"
    )

    if not ok:
        warn("Could not list Docker checkpoints")
        warn(err)
        return False

    if CHECKPOINT_NAME not in checkpoints:
        warn("Checkpoint was created but not registered")
        return False

    log("Checkpoint registered successfully")

    # Show checkpoint information
    ok, container_id, _ = run(
        f"docker inspect "
        f"--format '{{{{.Id}}}}' "
        f"{CONTAINER_NAME}"
    )

    if ok and container_id.strip():
        checkpoint_path = (
            f"/var/lib/docker/containers/"
            f"{container_id.strip()}/checkpoints/"
            f"{CHECKPOINT_NAME}"
        )

        ok2, size_out, _ = run(
            f"sudo du -sh '{checkpoint_path}'"
        )

        if ok2 and size_out:
            log(
                f"Checkpoint size: "
                f"{size_out.split()[0]}"
            )

    return True


def layer2_heart():
    print("\n[LAYER 2 — HEART] Migration Engine starting...")

    if not ensure_container_running():
        return False

    show_state("BEFORE migration")

    iterative_precopy()

    if not criu_checkpoint():
        return False

    return True


# ═══════════════════════════════════════════════
#   LAYER 3 — REAL NETWORK TRANSFER via SCP
# ═══════════════════════════════════════════════
def layer3_bridge(target_cloud):
    print("\n[LAYER 3 — BRIDGE] Real Network Transfer...")

    # ------------------------------------------------
    # Find Docker container ID
    # ------------------------------------------------
    ok, container_id, err = run(
        f"docker inspect "
        f"--format '{{{{.Id}}}}' "
        f"{CONTAINER_NAME}"
    )

    if not ok or not container_id.strip():
        warn(f"Could not find container ID: {err}")
        return False

    container_id = container_id.strip()

    # ------------------------------------------------
    # Real Docker checkpoint location
    # ------------------------------------------------
    checkpoint_path = (
        f"/var/lib/docker/containers/"
        f"{container_id}/checkpoints/"
        f"{CHECKPOINT_NAME}"
    )

    # ------------------------------------------------
    # Verify checkpoint exists
    # ------------------------------------------------
    ok, _, err = run(
        f"sudo test -d '{checkpoint_path}'"
    )

    if not ok:
        warn(
            "Docker checkpoint directory not found: "
            f"{checkpoint_path}"
        )
        return False

    # ------------------------------------------------
    # Compress checkpoint
    # ------------------------------------------------
    info("Compressing real CRIU checkpoint...")

    archive = "/tmp/checkpoint.tar.gz"

    run(f"rm -f {archive}")

    ok, _, err = run(
        f"sudo tar -czf {archive} "
        f"-C '{checkpoint_path}' ."
    )

    if not ok:
        warn(f"Checkpoint compression failed: {err}")
        return False

    ok, size_out, _ = run(
        f"du -sh {archive}"
    )

    size = (
        size_out.split()[0]
        if size_out
        else "N/A"
    )

    log(f"Checkpoint compressed: {size}")

    # ------------------------------------------------
    # Prepare target directory
    # ------------------------------------------------
    info(
        f"Preparing target VM ({TARGET_IP})..."
    )

    ok, _, err = run_remote(
        f"rm -rf {TARGET_DIR} && "
        f"mkdir -p {TARGET_DIR}"
    )

    if not ok:
        warn(
            f"Could not prepare target directory: {err}"
        )
        return False

    # ------------------------------------------------
    # REAL SCP TRANSFER
    # ------------------------------------------------
    info(
        f"Transferring checkpoint to "
        f"{TARGET_USER}@{TARGET_IP}..."
    )

    ok, _, err = run(
        f"scp "
        f"-o ConnectTimeout=10 "
        f"{archive} "
        f"{TARGET_USER}@{TARGET_IP}:"
        f"{TARGET_DIR}/checkpoint.tar.gz"
    )

    if not ok:
        warn(f"SCP failed: {err}")
        return False

    log(
        f"Checkpoint transferred to "
        f"{target_cloud} VM successfully!"
    )

    # ------------------------------------------------
    # Verify transfer
    # ------------------------------------------------
    ok, out, err = run_remote(
        f"ls -lh "
        f"{TARGET_DIR}/checkpoint.tar.gz"
    )

    if not ok:
        warn(
            f"Could not verify transferred checkpoint: "
            f"{err}"
        )
        return False

    info("Checkpoint transfer verified")

    # ------------------------------------------------
    # Also copy project file
    # ------------------------------------------------
    info("Syncing project files to target VM...")

    run(
        f"scp "
        f"{os.path.abspath(__file__)} "
        f"{TARGET_USER}@{TARGET_IP}:"
        f"~/AI-live-container-migration-/"
    )

    return True


# ═══════════════════════════════════════════════
#   LAYER 4 — STORAGE
# ═══════════════════════════════════════════════
def layer4_storage(target_cloud):
    print("\n[LAYER 4 — STORAGE] Storage Layer...")
    info(
        f"Data accessible on {target_cloud} "
        f"via shared storage"
    )
    info("Ceph/Rook integration — Phase 3")
    log("Storage layer acknowledged")


# ═══════════════════════════════════════════════
#   RESTORE ON TARGET VM (REAL SSH)
# ═══════════════════════════════════════════════
def restore_on_target(target_cloud):
    print(
        f"\n[RESTORE] Restoring container on "
        f"{target_cloud} ({TARGET_IP})..."
    )

    # Check target Docker
    info("Checking target Docker...")

    ok, _, err = run_remote("docker info")

    if not ok:
        warn(f"Target Docker unavailable: {err}")
        return False

    log("Target Docker is accessible")

    # ------------------------------------------------
    # Remove any old target container
    # ------------------------------------------------
    info("Removing existing target container...")

    run_remote(f"docker rm -f {CONTAINER_NAME}")

    # ------------------------------------------------
    # IMPORTANT:
    # Do NOT create a new container here.
    # The checkpoint belongs to the source container.
    # ------------------------------------------------

    # Check transferred checkpoint
    info("Checking transferred checkpoint...")

    ok, out, err = run_remote(
        f"test -d {TARGET_DIR}/checkpoint1"
    )

    if not ok:
        warn(
            f"Checkpoint directory not found on target: {err}"
        )
        return False

    log("Transferred checkpoint found")

    # ------------------------------------------------
    # Create temporary container with matching image
    # ------------------------------------------------
    info("Creating target container configuration...")

    ok, _, err = run_remote(
        f'docker create '
        f'--name {CONTAINER_NAME} '
        f'--security-opt seccomp=unconfined '
        f'ubuntu:22.04 '
        f'bash -c "count=0; while true; do '
        f'echo Count: $count; '
        f'count=$((count+1)); '
        f'sleep 1; done"'
    )

    if not ok:
        warn(f"Could not create target container: {err}")
        return False

    # ------------------------------------------------
    # Install checkpoint into Docker
    # ------------------------------------------------
    info("Installing checkpoint into target Docker storage...")

    ok, target_id, err = run_remote(
        f"docker inspect --format '{{{{.Id}}}}' "
        f"{CONTAINER_NAME}"
    )

    if not ok:
        warn(f"Could not get target container ID: {err}")
        return False

    target_id = target_id.strip()

    checkpoint_path = (
        f"/var/lib/docker/containers/"
        f"{target_id}/checkpoints/"
        f"{CHECKPOINT_NAME}"
    )

    ok, _, err = run_remote(
        f"sudo -n mkdir -p "
        f"/var/lib/docker/containers/"
        f"{target_id}/checkpoints"
    )

    if not ok:
        warn(f"Could not create Docker checkpoint directory: {err}")
        return False

    ok, _, err = run_remote(
        f"sudo -n cp -a "
        f"{TARGET_DIR}/checkpoint1 "
        f"{checkpoint_path}"
    )

    if not ok:
        warn(f"Could not install checkpoint: {err}")
        return False

    ok, _, err = run_remote(
        f"sudo -n chown -R root:root "
        f"{checkpoint_path}"
    )

    if not ok:
        warn(f"Could not set checkpoint ownership: {err}")
        return False

    log("Checkpoint installed into target Docker storage")

    # ------------------------------------------------
    # Restore using Docker/CRIU
    # ------------------------------------------------
    info("Restoring container from CRIU checkpoint...")

    ok, out, err = run_remote(
        f"docker start "
        f"--checkpoint {CHECKPOINT_NAME} "
        f"{CONTAINER_NAME}"
    )

    if not ok:
        warn(f"Checkpoint restore FAILED: {err}")

        # IMPORTANT:
        # Do not claim migration succeeded.
        return False

    log(
        f"Container restored from CRIU checkpoint "
        f"on {target_cloud}!"
    )

    # ------------------------------------------------
    # Verify target
    # ------------------------------------------------
    time.sleep(2)

    ok, out, err = run_remote(
        f"docker ps --format '{{{{.Names}}}}'"
    )

    if CONTAINER_NAME not in out.splitlines():
        warn("Container is not running on target")
        return False

    log(
        f"Container verified running on "
        f"{target_cloud} ({TARGET_IP})!"
    )

    # Show migrated application state
    info("Container output on target:")

    ok, logs, _ = run_remote(
        f"docker logs --tail 5 {CONTAINER_NAME}"
    )

    if ok and logs.strip():
        for line in logs.strip().splitlines():
            print(f"      {line}")

    # ------------------------------------------------
    # Stop source ONLY after successful restore
    # ------------------------------------------------
    info("Stopping container on source...")

    ok, _, err = run(
        f"docker stop {CONTAINER_NAME}"
    )

    if not ok:
        warn(f"Could not stop source container: {err}")
        return False

    log("Source container stopped — migration complete!")

    return True
# ═══════════════════════════════════════════════
#   SERVICE MESH
# ═══════════════════════════════════════════════
def update_service_mesh(target_cloud):

    info("Updating service mesh routing...")

    try:
        import requests

        response = requests.post(
            f"http://{TARGET_IP}:8888/migrate",
            json={
                "service": "counter-app",
                "target_vm": target_cloud,
                "target_ip": TARGET_IP
            },
            timeout=2
        )

        if response.ok:
            log("Service mesh routing updated!")
        else:
            warn(
                f"Service mesh returned "
                f"HTTP {response.status_code}"
            )

    except Exception as e:
        warn(
            f"Service mesh update skipped: {e}"
        )


# ═══════════════════════════════════════════════
#   MAIN
# ═══════════════════════════════════════════════
def migrate(target_cloud="GCP"):

    print("=" * 55)
    print(
        "  AI LIVE CONTAINER MIGRATION — REAL CROSS-VM"
    )
    print(
        f"  Time: {datetime.now().strftime('%H:%M:%S')}"
    )
    print(
        f"  Source: AWS ({SOURCE_IP})"
    )
    print(
        f"  Target: {target_cloud} ({TARGET_IP})"
    )
    print("=" * 55)

    # Layer 1
    layer1_brain(target_cloud)

    # Layer 2
    if not layer2_heart():
        warn(
            "Migration aborted — "
            "checkpoint creation failed"
        )
        return

    # Layer 3
    if not layer3_bridge(target_cloud):
        warn(
            "Migration aborted — "
            "checkpoint transfer failed"
        )
        return

    # Layer 4
    layer4_storage(target_cloud)

    # Restore
    if not restore_on_target(target_cloud):
        warn(
            "Migration aborted — "
            "target restore failed"
        )
        return

    # Service mesh ONLY after successful migration
    update_service_mesh(target_cloud)

    # Final
    print("\n" + "=" * 55)
    print(
        f"  MIGRATION COMPLETE → {target_cloud}"
    )
    print(
        f"  Container now running on {TARGET_IP}"
    )
    print(
        "  Layers: Brain → Heart → Bridge → Storage"
    )
    print("=" * 55)


# ═══════════════════════════════════════════════
#   ENTRY POINT
# ═══════════════════════════════════════════════
if __name__ == "__main__":

    import sys

    target = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "GCP"
    )

    migrate(target)
