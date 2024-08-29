#!/bin/bash
cd /root/crypto-trader || { echo "Failed to cd to /root/crypto-trader"; exit 1; }
echo "Directory changed" >> /var/log/crypto_strategy.log 2>&1
source .venv/bin/activate
echo "Virtual environment activated" >> /var/log/etf_strategy.log 2>&1
python3 signals.py >> /var/log/etf_strategy.log 2>&1
echo "Script executed" >> /var/log/etf_strategy.log 2>&1
