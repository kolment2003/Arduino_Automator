#!/bin/bash
echo activate shell in 3 seconds...
sleep 3
source venv/bin/activate
echo install pkgs specified in requirements.txt
pip install -r requirements.txt
echo deativate shell in 3 seconds...
sleep 3
deactivate