#!/bin/bash

echo "🏗️ Building McAfee SIEM Alarm Editor for Production..."

# Build frontend into the official dist folder
echo "📦 Building React frontend..."
cd /home/alrisk/alrisk-main/Trellix-Alarm-MNGT-WEB/frontend
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

echo "🔨 Building frontend assets..."
npm run build

echo "✅ Production build complete!"
echo "📍 Built files are in 'frontend/dist' (served by backend/main.py)"
echo "🚀 Start the backend with: ./start-backend.sh"
echo "🌐 Then visit: http://localhost:5000"
