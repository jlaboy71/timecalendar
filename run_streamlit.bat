@echo off
echo ========================================
echo   PTO and Market Calendar System
echo ========================================
echo.
echo Starting Streamlit application...
echo.
cd /d "%~dp0"
streamlit run streamlit_app/Home.py --server.port 8501
pause
