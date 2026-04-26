#!/bin/bash
# Setup script for Threads Automation

set -e

echo "🧵 Threads Automation - Setup Script"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.10 or higher is required. Found: $python_version"
    exit 1
fi
echo "✅ Python $python_version"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created"
    echo "⚠️  Please edit .env with your configuration"
else
    echo "✅ .env file already exists"
fi
echo ""

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs
echo "✅ Logs directory created"
echo ""

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "✅ Database initialized"
echo ""

# Create example account
echo "Creating example account..."
python scripts/create_example_account.py
echo ""

echo "======================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your configuration (LLM settings, etc.)"
echo "2. Start the server: python run.py"
echo "3. Visit http://localhost:8000"
echo "4. Check the API docs: http://localhost:8000/docs"
echo ""
echo "Optional:"
echo "- Test LLM connection: python scripts/test_llm.py"
echo "- Read QUICKSTART.md for detailed usage"
echo ""
