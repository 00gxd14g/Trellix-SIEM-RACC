#!/bin/bash

# ====================================
# Trellix Alarm Management Web - Production Start Script
# ====================================
# This script builds the frontend and starts the backend server
# The backend will serve both API and static frontend files
# ====================================

set -e  # Exit immediately if a command exits with a non-zero status

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[START]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Define directories
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

print_message "Starting Trellix Alarm Management Web Application (Production Mode)"
print_message "============================================================"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install npm."
    exit 1
fi

# --- Frontend Build ---
print_message "Building frontend for production..."
cd "$FRONTEND_DIR"

# Install frontend dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    print_message "Installing frontend dependencies..."
    npm install
fi

# Build the frontend
print_message "Building frontend assets..."
npm run build

if [ ! -d "dist" ]; then
    print_error "Frontend build failed. dist directory not created."
    exit 1
fi

print_message "Frontend build completed successfully!"

# --- Backend Setup and Start ---
print_message "Setting up backend..."
cd "$BACKEND_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_message "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_message "Activating virtual environment..."
source venv/bin/activate

# Install/Update backend dependencies
print_message "Installing backend dependencies..."
pip install -q -r requirements.txt

# Create necessary directories
print_message "Creating necessary directories..."
mkdir -p logs
mkdir -p uploads
mkdir -p database

# Set environment variables for production
export FLASK_CONFIG=production
export FLASK_ENV=production
export FLASK_DEBUG=0

print_message "============================================================"
print_message "Starting Flask backend server..."
print_message "============================================================"
print_message ""
print_message "Application will be available at:"
print_message "  - Web Interface: http://localhost:5000"
print_message "  - API Documentation: http://localhost:5000/api/docs"
print_message "  - API Base URL: http://localhost:5000/api"
print_message ""
print_message "Press Ctrl+C to stop the application"
print_message "============================================================"

# Start the Flask application
python3 main.py