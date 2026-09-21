@echo off
cd /d "%~dp0backend"
echo 국내주식 추천 서버를 시작합니다...
echo 이 PC에서:      http://localhost:8000
echo 같은 Wi-Fi 휴대폰에서: http://%COMPUTERNAME%:8000  (또는 PC의 IP 주소:8000)
echo 종료하려면 이 창을 닫으세요.
echo.
".\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
