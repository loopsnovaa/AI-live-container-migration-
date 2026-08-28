## Complete Setup Guide  📋

---

## Prerequisites
- Windows laptop with VirtualBox installed
- Ubuntu 22.04 VM running inside VirtualBox

---

## PART 1 — Install VirtualBox (if not already)

1. Go to *https://virtualbox.org*
2. Download *VirtualBox for Windows*
3. Install it normally
4. Download *Ubuntu 22.04 ISO* from **https://ubuntu.com/download/desktop**
5. Create new VM (Name: UbuntuMigration, RAM: 4GB, Storage: 30GB)
6. Install Ubuntu using the ISO

---

## PART 2 — Inside Ubuntu VM (open terminal Ctrl+Alt+T)

### Step 1 — Install all tools:
bash
sudo apt-get update

bash
sudo apt-get install -y docker.io git python3 python3-pip criu curl

bash
sudo systemctl start docker

bash
sudo usermod -aG docker $USER

bash
newgrp docker


### Step 2 — Install Python libraries:
bash
pip3 install requests psutil numpy


### Step 3 — Clone your GitHub project:
bash
cd ~
git clone https://github.com/loopsnovaa/AI-live-container-migration-.git

bash
cd AI-live-container-migration-


### Step 4 — Verify all files are there:
bash
ls -la

Should show:

✅ migrate.py
✅ price_oracle.py
✅ predictor.py
✅ service_mesh.py
✅ README.md
✅ dashboard.py

---

## PART 3 — Run the project (in order!)

### Run 1 — Test Price Oracle:
bash
python3 price_oracle.py

Wait 10 seconds → see prices → press Ctrl+C

---

### Run 2 — Test AI Predictor:
bash
python3 predictor.py

Wait 1-2 minutes → see GA recommendation

---

### Run 3 — Test Migration Engine:
bash
python3 migrate.py GCP

See full 4-layer migration output

---

### Run 4 — Run Full Auto Controller:
bash
python3 migration_controller.py

This runs everything together automatically!

---

## PART 4 — Common Errors & Fixes

| Error | Fix |
|-------|-----|
| docker: permission denied | Run sudo usermod -aG docker $USER then newgrp docker |
| pip3: command not found | Run sudo apt-get install -y python3-pip |
| ModuleNotFoundError: psutil | Run pip3 install psutil |
| ModuleNotFoundError: requests | Run pip3 install requests |
| git: command not found | Run sudo apt-get install -y git |
| criu: command not found | Run sudo apt-get install -y criu |

---

bash
cd ~/AI-live-container-migration-
chmod +x setup.sh
git add .
git commit -m "Add auto setup script for new machines"
git push origin main


---

## Summary :


1. Install VirtualBox + Ubuntu VM
2. Open terminal in Ubuntu
3. Run: git clone https://github.com/loopsnovaa/AI-live-container-migration-.git
4. Run: cd AI-live-container-migration- 
5. Run: python3 migrate.py GCP

