#!/bin/bash
python3 -u main.py &
exec python3 -u dashboard.py
