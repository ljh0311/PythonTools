@echo off
echo ================================================
echo  CAR RENTAL RECOMMENDATION SYSTEM (ENHANCED)
echo ================================================
echo.

echo Installing required packages...
pip install -r requirements.txt

echo.
echo Starting the enhanced application with:
echo  - Automatic data loading from 22 - Sheet1.csv
echo  - Fixed data analysis features
echo  - Separated duration and fuel costs in recommendations
echo  (Even when entering new values and clicking "Get Recommendations")
echo.

python fixed_car_loader.py

pause
