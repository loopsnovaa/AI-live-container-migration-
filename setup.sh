#!/bin/bash
echo "Setting  up AI Container Migration System..."
sudo apt update
sudo apt install docker.io git curl python3-pip criu -y
sudo add-apt-repository ppa:criu/ppa -y
sudo apt update
sudo apt install criu -y
echo '{"experimental": true}' | sudo tee /etc/docker/daemon.json
sudo service docker start
sudo usermod -aG docker $USER 
pip3 install numpy scipy streamlit flask pandas matplotlib 
echo "Setup complete!"

