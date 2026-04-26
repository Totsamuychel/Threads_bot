@echo off
REM Setup script for Threads Automation (Windows)

echo 🧵 Threads Automation - Setup Script
echo ======================================
echo.

REM Check Python version
echo Checking Python version...
python --version
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    exit /b 1
)
echo ✅ Python found
echo.

REM Create virtual environment
echo Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment already exists
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo ✅ Virtual environment activated
echo.

REM Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo ✅ Dependencies installed
echo.

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo Creating .env file...
    copy .env.example .env
    echo ✅ .env file created
    echo ⚠️  Please edit .env with your configuration
) else (
    echo ✅ .env file already exists
)
echo.

REM Create logs directory
echo Creating logs directory...
if not exist "logs" mkdir logs
echo ✅ Logs directory created
echo.

REM Run database migrations
echo Running database migrations...
alembic upgrade head
echo ✅ Database initialized
echo.

REM Create example account
echo Creating example account...
python scripts\create_example_account.py
echo.

echo ======================================
echo ✅ Setup complete!
echo.
echo Next steps:
echo 1. Edit .env with your configuration (LLM settings, etc.)
echo 2. Start the server: python run.py
echo 3. Visit http://localhost:8000
echo 4. Check the API docs: http://localhost:8000/docs
echo.
echo Optional:
echo - Test LLM connection: python scripts\test_llm.py
echo - Read QUICKSTART.md for detailed usage
echo.
pause
