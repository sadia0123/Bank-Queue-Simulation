@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
python -m streamlit run app.py
if errorlevel 1 (
    echo.
    echo Could not start the app. Run: python -m pip install -r requirements.txt
    pause
)
