#!/bin/bash

echo "🚀 Starting McAfee SIEM Alarm Editor Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Start Flask server
echo "🌐 Starting Flask server on http://localhost:5000"
python main.py