#!/bin/bash

# ====================================
# Trellix Alarm Management Web - Development Start Script
# ====================================
# This script starts both frontend and backend in development mode
# Frontend runs on port 3000 with hot-reload
# Backend runs on port 5000 with debug mode
# Frontend proxies API calls to backend
# ====================================

set -e  # Exit immediately if a command exits with a non-zero status

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[DEV]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Define directories
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Function to cleanup background processes on exit
cleanup() {
    print_warning "Stopping all services..."

    # Kill backend process if running
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi

    # Kill frontend process if running
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    # Kill any remaining python or node processes started by this script
    jobs -p | xargs -r kill 2>/dev/null || true

    print_message "All services stopped."
}

# Set up trap to cleanup on script exit
trap cleanup EXIT INT TERM

print_message "Starting Trellix Alarm Management Web Application (Development Mode)"
print_message "================================================================"

# Check requirements
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install npm."
    exit 1
fi

# --- Backend Setup ---
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
mkdir -p logs
mkdir -p uploads
mkdir -p database

# Set environment variables for development
export FLASK_CONFIG=development
export FLASK_ENV=development
export FLASK_DEBUG=1

# Start backend in background
print_message "Starting Flask backend on port 5000..."
python3 main.py &
BACKEND_PID=$!

# Wait for backend to start
print_info "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:5000/api/health > /dev/null; then
        print_message "Backend is running!"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Backend failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# --- Frontend Setup ---
print_message "Setting up frontend..."
cd "$FRONTEND_DIR"

# Install frontend dependencies if node_modules doesn't exist or is outdated
if [ ! -d "node_modules" ]; then
    print_message "Installing frontend dependencies..."
    npm install
else
    print_info "Frontend dependencies already installed (run 'npm install' in frontend/ to update)"
fi

# Start frontend development server
print_message "Starting Vite dev server on port 3000..."
print_message "================================================================"
print_message ""
print_info "Development servers are starting..."
print_message ""
print_message "  Frontend (with hot-reload): http://localhost:3000"
print_message "  Backend API: http://localhost:5000/api"
print_message "  API Documentation: http://localhost:5000/api/docs"
print_message ""
print_info "API calls from frontend are automatically proxied to backend"
print_warning "Press Ctrl+C to stop all services"
print_message "================================================================"
print_message ""

# Start frontend and wait
npm run dev &
FRONTEND_PID=$!

# Wait for both processes
wait $FRONTEND_PID $BACKEND_PID