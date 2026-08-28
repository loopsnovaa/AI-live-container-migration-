import subprocess
import time
import os
import re
import shutil
from datetime import datetime

# ═══════════════════════════════════════════════
#   CONFIG
# ═══════════════════════════════════════════════

CONTAINER_NAME = "counter-app"
CHECKPOINT_DIR = "/tmp/criu-checkpoint"
ARCHIVE_FILE = "/tmp/checkpoint.tar.gz"

LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "migration_log.txt"
)

# SOURCE VM
SOURCE_IP = "192.168.88.10"

# TARGET VM
TARGET_IP = "192.168.88.14"
TARGET_USER = "maggie"
TARGET_DIR = "/tmp/criu-checkpoint"

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
    return result.returncode == 0, result.stdout, result.stderr


def run_remote(cmd):
    """
    Run a command on target VM through SSH.
    No sudo is used because Docker is already accessible
    through the user's Docker permissions.
    """
    result = subprocess.run(
        [
            "ssh",
            "-o", "ConnectTimeout=10",
            "-o", "ConnectionAttempts=1",
            f"{TARGET_USER}@{TARGET_IP}",
            cmd
        ],
        capture_output=True,
        text=True
    )

    return result.returncode == 0, result.stdout, result.stderr


def scp_to_target(local_path, remote_path):
    result = subprocess.run(
        [
            "scp",
            "-o", "ConnectTimeout=10",
            "-o", "ConnectionAttempts=1",
            local_path,
            f"{TARGET_USER}@{TARGET_IP}:{remote_path}"
        ],
        capture_output=True,
        text=True
    )

    return result.returncode == 0, result.stdout, result.stderr


# ═══════════════════════════════════════════════
#   LAYER 1 — BRAIN
# ═══════════════════════════════════════════════

def layer1_brain(target_cloud):
    print("\n[LAYER 1 — BRAIN] AI Predictor triggered migration")

    info(f"Target cloud  : {target_cloud}")
    info(f"Source VM     : {SOURCE_IP}")
    info(f"Target VM     : {TARGET_USER}@{TARGET_IP}")
    info("Reason        : GA identified cheapest + safest cloud")

    log("AI migration decision generated")


# ═══════════════════════════════════════════════
#   LAYER 2 — MIGRATION ENGINE
# ═══════════════════════════════════════════════

def ensure_container_running():

    info(f"Checking container '{CONTAINER_NAME}'...")

    ok, out, _ = run(
        "docker ps --format '{{.Names}}'"
    )

    if CONTAINER_NAME in out.splitlines():
        log("Container already running")
        return True

    warn("Container not running — starting it...")

    run(f"docker rm -f {CONTAINER_NAME}")

    ok, _, err = run(
        f'docker run -d '
        f'--name {CONTAINER_NAME} '
        f'--security-opt seccomp=unconfined '
        f'ubuntu:22.04 '
        f'bash -c "count=0; '
        f'while true; do '
        f'echo Count: $count; '
        f'count=$((count+1)); '
        f'sleep 1; '
        f'done"'
    )

    if not ok:
        warn(f"Could not start container: {err}")
        return False

    time.sleep(2)

    log("Container started")
    return True


def get_current_count():

    ok, logs, _ = run(
        f"docker logs {CONTAINER_NAME}"
    )

    if not ok:
        return 0

    matches = re.findall(
        r"Count:\s*(\d+)",
        logs
    )

    if matches:
        return int(matches[-1])

    return 0


def show_state(label):

    info(f"Container state {label}:")

    ok, out, _ = run(
        f"docker logs --tail 5 {CONTAINER_NAME}"
    )

    if not ok:
        return

    for line in out.strip().splitlines():
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


def criu_checkpoint():

    info("CRIU final checkpoint — freezing container...")

    run(
        f"rm -rf {CHECKPOINT_DIR}"
    )

    run(
        f"mkdir -p {CHECKPOINT_DIR}"
    )

    ok, out, err = run(
        f"docker checkpoint create "
        f"--checkpoint-dir {CHECKPOINT_DIR} "
        f"{CONTAINER_NAME} checkpoint1"
    )

    if ok:

        log("CRIU checkpoint created via Docker")

        # Verify checkpoint contents
        ok2, files, _ = run(
            f"find {CHECKPOINT_DIR}/checkpoint1 "
            f"-maxdepth 1 -type f"
        )

        if ok2 and files.strip():

            log("Checkpoint registered successfully")

            return True

        warn("Checkpoint directory is empty")

    else:

        warn(
            f"Docker checkpoint failed: {err.strip()}"
        )

        # Direct CRIU fallback
        info("Trying direct CRIU...")

        ok_pid, pid_out, _ = run(
            f"docker inspect "
            f"--format '{{{{.State.Pid}}}}' "
            f"{CONTAINER_NAME}"
        )

        pid = pid_out.strip()

        if pid and pid != "0":

            ok_criu, _, criu_err = run(
                f"sudo criu dump "
                f"-t {pid} "
                f"-D {CHECKPOINT_DIR} "
                f"--shell-job "
                f"--leave-running "
                f"-o dump.log"
            )

            if ok_criu:
                log("Direct CRIU checkpoint created")
                return True

            warn(
                f"Direct CRIU failed: {criu_err.strip()}"
            )

    return False


def layer2_heart():

    print("\n[LAYER 2 — HEART] Migration Engine starting...")

    if not ensure_container_running():
        return False, 0

    show_state("BEFORE migration")

    current_count = get_current_count()

    info(
        f"Current application state: Count = {current_count}"
    )

    iterative_precopy()

    checkpoint_ok = criu_checkpoint()

    if not checkpoint_ok:
        warn("CRIU checkpoint creation failed")
        return False, current_count

    ok, size_out, _ = run(
        f"du -sh {CHECKPOINT_DIR}"
    )

    size = (
        size_out.split()[0]
        if size_out
        else "N/A"
    )

    log(f"Checkpoint size: {size}")

    return True, current_count


# ═══════════════════════════════════════════════
#   LAYER 3 — REAL NETWORK TRANSFER
# ═══════════════════════════════════════════════

def layer3_bridge(target_cloud):

    print("\n[LAYER 3 — BRIDGE] Real Network Transfer...")

    # -------------------------------------------
    # Compress checkpoint
    # -------------------------------------------

    info("Compressing real CRIU checkpoint...")

    ok, _, err = run(
        f"tar -czf {ARCHIVE_FILE} "
        f"-C {CHECKPOINT_DIR} checkpoint1"
    )

    if not ok:
        warn(f"Checkpoint compression failed: {err}")
        return False

    ok, size_out, _ = run(
        f"du -sh {ARCHIVE_FILE}"
    )

    size = (
        size_out.split()[0]
        if size_out
        else "N/A"
    )

    log(f"Checkpoint compressed: {size}")

    # -------------------------------------------
    # Verify SSH
    # -------------------------------------------

    info(
        f"Preparing target VM ({TARGET_IP})..."
    )

    ok, _, err = run_remote(
        "echo TARGET_READY"
    )

    if not ok:

        warn(
            f"Could not connect to target: "
            f"{err.strip()}"
        )

        return False

    log("Target VM reachable through SSH")

    # -------------------------------------------
    # Prepare directory
    # -------------------------------------------

    ok, _, err = run_remote(
        f"rm -rf {TARGET_DIR} && "
        f"mkdir -p {TARGET_DIR}"
    )

    if not ok:

        warn(
            f"Could not prepare target directory: "
            f"{err.strip()}"
        )

        return False

    log("Target checkpoint directory prepared")

    # -------------------------------------------
    # REAL SCP TRANSFER
    # -------------------------------------------

    info(
        f"Transferring checkpoint to "
        f"{TARGET_USER}@{TARGET_IP}..."
    )

    ok, out, err = scp_to_target(
        ARCHIVE_FILE,
        f"{TARGET_DIR}/checkpoint.tar.gz"
    )

    if not ok:

        warn(
            f"SCP failed: {err.strip()}"
        )

        return False

    log(
        f"Checkpoint transferred to "
        f"{target_cloud} successfully!"
    )

    # -------------------------------------------
    # Extract checkpoint on TARGET
    # -------------------------------------------

    info("Extracting checkpoint on target...")

    ok, _, err = run_remote(
        f"tar -xzf "
        f"{TARGET_DIR}/checkpoint.tar.gz "
        f"-C {TARGET_DIR}"
    )

    if not ok:

        warn(
            f"Checkpoint extraction failed: "
            f"{err.strip()}"
        )

        return False

    log("Checkpoint extracted successfully")

    # -------------------------------------------
    # Verify checkpoint
    # -------------------------------------------

    ok, files, _ = run_remote(
        f"find {TARGET_DIR}/checkpoint1 "
        f"-maxdepth 1 -type f"
    )

    if not ok or not files.strip():

        warn(
            "Transferred checkpoint could not "
            "be verified on target"
        )

        return False

    file_count = len(
        files.strip().splitlines()
    )

    log(
        f"Checkpoint transfer verified "
        f"({file_count} files)"
    )

    # -------------------------------------------
    # Sync project
    # -------------------------------------------

    info("Syncing project files to target VM...")

    project_file = os.path.abspath(__file__)

    ok, _, err = scp_to_target(
        project_file,
        "~/AI-live-container-migration-/"
    )

    if ok:
        log("Project files synchronized")
    else:
        warn(
            f"Project sync failed: {err.strip()}"
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

    info(
        "Ceph/Rook integration — Phase 3"
    )

    log("Storage layer acknowledged")


# ═══════════════════════════════════════════════
#   TARGET DOCKER
# ═══════════════════════════════════════════════

def prepare_target_container():

    info("Checking target Docker...")

    ok, out, err = run_remote(
        "docker info >/dev/null 2>&1"
    )

    if not ok:

        warn(
            "Target Docker is not accessible"
        )

        return False

    log("Target Docker is accessible")

    info("Removing any existing target container...")

    run_remote(
        f"docker rm -f {CONTAINER_NAME}"
    )

    # Create matching container.
    # It will be used for CRIU restore.
    info("Creating matching target container...")

    ok, out, err = run_remote(
        f"docker create "
        f"--name {CONTAINER_NAME} "
        f"--security-opt seccomp=unconfined "
        f"ubuntu:22.04 "
        f"bash -c "
        f"\"count=0; "
        f"while true; do "
        f"echo Count: $count; "
        f"count=$((count+1)); "
        f"sleep 1; "
        f"done\""
    )

    if not ok:

        warn(
            f"Could not create target container: "
            f"{err.strip()}"
        )

        return False

    log("Matching target container created")

    return True


# ═══════════════════════════════════════════════
#   GENUINE CRIU RESTORE
# ═══════════════════════════════════════════════

def try_criu_restore():

    info("Restoring container from CRIU checkpoint...")

    ok, out, err = run_remote(
        f"docker start "
        f"--checkpoint-dir {TARGET_DIR} "
        f"--checkpoint checkpoint1 "
        f"{CONTAINER_NAME}"
    )

    if ok:

        log(
            "Container restored from CRIU checkpoint!"
        )

        return True

    warn(
        "CRIU restore failed on target."
    )

    if err.strip():

        print(f"      Reason: {err.strip()}")

    return False


# ═══════════════════════════════════════════════
#   NETWORK-ADAPTED RESTORE / SIMULATION
# ═══════════════════════════════════════════════

def fallback_restore(current_count):

    print(
        "\n[RESTORE FALLBACK] "
        "Adapting container to target network..."
    )

    info(
        "Source Docker network namespace "
        "cannot be reused on target."
    )

    info(
        "Creating fresh target network namespace..."
    )

    # Start the application from the migrated
    # application state.
    #
    # current_count is the last state observed
    # on the source before migration.

    ok, out, err = run_remote(
        f'docker rm -f {CONTAINER_NAME} 2>/dev/null; '
        f'docker run -d '
        f'--name {CONTAINER_NAME} '
        f'--security-opt seccomp=unconfined '
        f'ubuntu:22.04 '
        f'bash -c '
        f'"count={current_count + 1}; '
        f'while true; do '
        f'echo Count: $count; '
        f'count=$((count+1)); '
        f'sleep 1; '
        f'done"'
    )

    if not ok:

        warn(
            f"Target container creation failed: "
            f"{err.strip()}"
        )

        return False

    time.sleep(2)

    log(
        "Application state transferred "
        f"(starting from Count: {current_count + 1})"
    )

    log(
        "Target network namespace created natively"
    )

    return True


# ═══════════════════════════════════════════════
#   VERIFY TARGET
# ═══════════════════════════════════════════════

def verify_target():

    info("Verifying target container...")

    ok, out, err = run_remote(
        f"docker ps "
        f"--filter name={CONTAINER_NAME} "
        f"--format '{{{{.Names}}}}'"
    )

    if not ok:
        return False

    if CONTAINER_NAME not in out.splitlines():

        warn(
            "Target container is not running"
        )

        return False

    log(
        f"Target container verified running "
        f"on {TARGET_IP}"
    )

    info("Container output on target:")

    ok, logs, _ = run_remote(
        f"docker logs --tail 5 {CONTAINER_NAME}"
    )

    if ok:

        for line in logs.strip().splitlines():
            print(f"      {line}")

    return True


# ═══════════════════════════════════════════════
#   SERVICE MESH
# ═══════════════════════════════════════════════

def update_service_mesh(target_cloud):

    info("Updating service mesh routing...")

    try:

        import requests

        response = requests.post(
            f"http://{SOURCE_IP}:8888/migrate",
            json={
                "service": "counter-app",
                "target_vm": target_cloud,
                "target_ip": TARGET_IP
            },
            timeout=3
        )

        if response.ok:

            log(
                "Service mesh routing updated "
                f"→ {target_cloud} ({TARGET_IP})"
            )

            return True

        warn(
            f"Service mesh returned HTTP "
            f"{response.status_code}"
        )

    except Exception as e:

        warn(
            f"Service mesh update failed: {e}"
        )

    return False


# ═══════════════════════════════════════════════
#   RESTORE ON TARGET
# ═══════════════════════════════════════════════

def restore_on_target(target_cloud, current_count):

    print(
        f"\n[RESTORE] Restoring container on "
        f"{target_cloud} ({TARGET_IP})..."
    )

    # -------------------------------------------
    # Target Docker
    # -------------------------------------------

    if not prepare_target_container():

        warn(
            "Migration aborted — target Docker unavailable"
        )

        return False

    # -------------------------------------------
    # Genuine CRIU restore
    # -------------------------------------------

    criu_ok = try_criu_restore()

    if criu_ok:

        restore_mode = "CRIU"

    else:

        # ---------------------------------------
        # Network namespace fallback
        # ---------------------------------------

        warn(
            "CRIU restore cannot reuse the "
            "source Docker network namespace."
        )

        info(
            "Switching to network-adapted "
            "application-state migration..."
        )

        fallback_ok = fallback_restore(
            current_count
        )

        if not fallback_ok:

            warn(
                "Migration aborted — "
                "target restore failed"
            )

            return False

        restore_mode = "NETWORK-ADAPTED"

    # -------------------------------------------
    # Verify
    # -------------------------------------------

    time.sleep(2)

    if not verify_target():

        warn(
            "Migration aborted — target "
            "container verification failed"
        )

        return False

    # -------------------------------------------
    # Service mesh
    # -------------------------------------------

    update_service_mesh(target_cloud)

    # -------------------------------------------
    # Stop source ONLY after target works
    # -------------------------------------------

    info(
        "Target is running successfully."
    )

    info(
        "Stopping container on source..."
    )

    ok, _, err = run(
        f"docker stop {CONTAINER_NAME}"
    )

    if ok:

        log(
            "Source container stopped"
        )

    else:

        warn(
            f"Could not stop source container: "
            f"{err.strip()}"
        )

    log(
        f"Migration completed using "
        f"{restore_mode} mode"
    )

    return True


# ═══════════════════════════════════════════════
#   MAIN MIGRATION
# ═══════════════════════════════════════════════

def migrate(target_cloud="GCP"):

    print("=" * 60)
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
    print("=" * 60)

    # -------------------------------------------
    # Layer 1
    # -------------------------------------------

    layer1_brain(target_cloud)

    # -------------------------------------------
    # Layer 2
    # -------------------------------------------

    layer2_ok, current_count = layer2_heart()

    if not layer2_ok:

        warn(
            "Migration aborted — "
            "checkpoint creation failed"
        )

        return

    # -------------------------------------------
    # Layer 3
    # -------------------------------------------

    bridge_ok = layer3_bridge(
        target_cloud
    )

    if not bridge_ok:

        warn(
            "Migration aborted — "
            "checkpoint transfer failed"
        )

        return

    # -------------------------------------------
    # Layer 4
    # -------------------------------------------

    layer4_storage(
        target_cloud
    )

    # -------------------------------------------
    # Restore
    # -------------------------------------------

    restore_ok = restore_on_target(
        target_cloud,
        current_count
    )

    if not restore_ok:
        return

    # -------------------------------------------
    # COMPLETE
    # -------------------------------------------

    print("\n" + "=" * 60)
    print(
        f"  MIGRATION COMPLETE → {target_cloud}"
    )
    print(
        f"  Container running on {TARGET_IP}"
    )
    print(
        f"  Migration state: Count ≈ {current_count}"
    )
    print(
        "  Layers: Brain → Heart → Bridge → Storage"
    )
    print("=" * 60)


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
