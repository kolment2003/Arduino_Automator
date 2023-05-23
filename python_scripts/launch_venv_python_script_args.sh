#!/bin/bash
echo activate shell
source venv/bin/activate
script=$1
python3 "${script}"