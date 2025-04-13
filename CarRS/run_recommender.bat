@echo off
echo ================================================
echo   CAR RENTAL RECOMMENDATION SYSTEM - CLI VERSION
echo ================================================
echo.
echo Installing required packages...
pip install -r requirements.txt

echo.
echo Starting the recommendation system...
python car_rental_recommender.py
pause 