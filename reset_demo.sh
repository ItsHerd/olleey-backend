#!/bin/bash

# Quick script to reset and seed demo data

echo "🧹 Resetting demo data..."
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Cleanup old data
python3 scripts/seed_demo_flow.py --cleanup

# Create fresh demo data
python3 scripts/seed_demo_flow.py

echo ""
echo "✅ Demo reset complete!"
echo "📧 Login with: demo@olleey.com"
echo "🔑 Password: password"
echo ""
echo "Refresh your browser to see the new data."
