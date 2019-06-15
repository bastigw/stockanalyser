#!/bin/bash -e

python3 -m venv env
source env/bin/activate 
pip install -r requirements.txt

echo "Switch to Virtualenv with: 'source env/bin/activate'"
