#!/bin/bash

echo "🚀 Starting McAfee SIEM Alarm Editor Frontend..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start Vite development server
echo "🌐 Starting Vite dev server on http://localhost:3000"
npm run dev