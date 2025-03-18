@echo off
echo Installing required packages...
pip install -r requirements.txt
echo.
echo Running Car Rental Recommendation System...
python car_rental_recommender.py
pause 