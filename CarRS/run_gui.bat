@echo off
echo ================================================
echo   CAR RENTAL RECOMMENDATION SYSTEM - GUI VERSION
echo ================================================
echo.
echo Installing required packages...
pip install -r requirements.txt

echo.
echo Starting the GUI application...
python car_rental_recommender_gui.py
pause 