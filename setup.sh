#!/usr/bin/env bash

# LossGraph Development Setup Script
# This script automates the initial setup of the project

set -e

echo "🚀 LossGraph Development Setup"
echo "================================"

# Check Python
echo "✓ Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 is required but not installed."
    exit 1
fi

# Check Node.js
echo "✓ Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "✗ Node.js is required but not installed."
    exit 1
fi

# Backend Setup
echo ""
echo "📦 Setting up backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "  → Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "  → Installing Python dependencies..."
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "  → Creating .env file..."
    cp .env.example .env
    echo "  ⚠️  Edit backend/.env with your configuration"
fi

cd ..

# Frontend Setup
echo ""
echo "🎨 Setting up frontend..."
cd frontend

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "  → Installing Node dependencies..."
    npm install
fi

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo "  → Creating .env.local file..."
    cp .env.example .env.local
fi

cd ..

# Summary
echo ""
echo "✅ Setup Complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Review and update configuration files:"
echo "     - backend/.env"
echo "     - frontend/.env.local"
echo ""
echo "  2. Start the development servers:"
echo "     npm run dev"
echo ""
echo "  3. Or start individually:"
echo "     Terminal 1: cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload"
echo "     Terminal 2: cd frontend && npm run dev"
echo ""
echo "  4. Open http://localhost:3000 in your browser"
echo ""
echo "📚 Documentation:"
echo "  - Setup: docs/SETUP.md"
echo "  - Architecture: docs/ARCHITECTURE.md"
echo "  - API Reference: docs/API.md"
echo "  - Data Model: docs/DATA_MODEL.md"
