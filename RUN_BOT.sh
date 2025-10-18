#!/bin/bash
# Script to deploy fact-checking bot to your Zoom meeting

# Your Zoom meeting URL
MEETING_URL="https://app.zoom.us/wc/79523352234/start?fromPWA=1&pwd=Rsh6r5W0BeppgJ6AsmkZMivDzftClU.1"

# Change to the meeting-baas-speaking directory
cd /home/brian-isaac/Documents/personal/uhmm-achtually/meeting-baas-speaking

# Activate virtual environment and deploy bot
source .venv/bin/activate && python deploy_fact_checker_v2.py "$MEETING_URL"
