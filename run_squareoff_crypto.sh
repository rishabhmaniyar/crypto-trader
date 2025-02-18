#!/bin/bash
cd /home/ubuntu/crypto-trader || { echo "Failed to cd to /home/ubuntu/crypto-trader"; exit 1; }
echo "Directory changed" >> /home/ubuntu/log/squareoff_crypto_strategy.log 2>&1
source ./venv/bin/activate
echo "Virtual environment activated" >> /home/ubuntu/log/squareoff_crypto_strategy.log 2>&1
python3 square_off_positions.py >> /home/ubuntu/log/squareoff_crypto_strategy.log 2>&1
echo "Script executed" >> /home/ubuntu/log/squareoff_crypto_strategy.log 2>&1