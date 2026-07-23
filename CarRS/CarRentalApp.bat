@echo off
cd /d "%~dp0"
echo ================================================
echo  CAR RENTAL RECOMMENDATION SYSTEM
echo ================================================
echo.
echo Starting the car rental recommender...
echo Costs use pricing_config.json by default.
echo.

python car_rental_recommender_gui.py
pause
