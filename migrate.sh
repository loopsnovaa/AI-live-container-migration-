#!/bin/bash

echo "============================="
echo " AI SMART CONTANIER MIGRATION SYSTEM"
echo " Phase 1 demo "
echo "============================"
sleep 1

sudo rm -f /tmp/counter.log
sudo rm -rf /tmp/criu-checkpoint
sudo mkdir -p /tmp/criu-checkpoint

echo ""
echo "STEP 1 : starting stateful application..."
echo "==========================="
python3 ~/migration-project/counter.py > /tmp/counter.log 2>&1 & 
APP_PID=$!
echo "application started with PID: $APP_PID"
sleep 8

echo ""
echo "current state of running application"
tail -5 /tmp/counter.log
sleep 2

echo ""
echo "============================"
echo "PROBLEM: normal restart loses all state!"
echo "==========================="
sleep 1
echo "Killing application(simulating cold restart)..."
kill $APP_PID 2>/dev/null
sleep 2
echo "restarting application..."
python3 ~/migration-project/counter.py > /tmp/counter_restart.log 2>&1 &
RESTART_PID=$!
sleep 5
echo "after normal restart - counter resets to:"
tail -5 /tmp/counter_restart.log
echo "state lost! counter reset to 0!"
kill $RESTART_PID 2>/dev/null
sleep 2

echo ""
echo "=========================="
echo "CRIU LIVE MIGRATION"
echo "========================="
sleep 1

sudo rm -f /tmp/counter.log
python3 ~/migration-project/counter.py > /tmp/counter.log 2>&1 &
APP_PID=$!
echo "application started with PID: $APP_PID"
sleep 10

echo ""
echo "current state before migration:"
tail -5 /tmp/counter.log
FROZEN_COUNT=$(tail -1 /tmp/counter.log | grep -o '[0-9]*')
sleep 2 

echo ""
echo "STEP 2: freezing application with CRIU..."
echo "------------------------------"
sudo criu dump -t $APP_PID -D /tmp/criu-checkpoint --shell-job
echo "application frozen at count: $FROZEN_COUNT"
sleep 2 

echo ""
echo "checkpoint files saved:"
sudo ls /tmp/criu-checkpoint/
sleep 2 

echo ""
echo "STEP 3: Restoring application at destination..."
echo "--------------------------------------------"
sudo criu restore -D /tmp/criu-checkpoint --shell-job -d
shell 5

echo ""
echo "state after migration:"
tail -10 /tmp/counter.log

echo ""
echo "==============================="
echo "MIGRATION COMPLETE!"
echo "counter continued from: $FROZEN_COUNT"
echo "zero state loss- zero runtime"
echo "=============================="

