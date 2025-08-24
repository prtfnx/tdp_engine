#!/bin/bash
set -e

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Run build and deploy
python build_and_deploy.py

echo "Setup complete. To activate the environment later, run: source venv/bin/activate"
