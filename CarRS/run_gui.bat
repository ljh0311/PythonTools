@echo off
echo Installing required packages...
pip install pandas numpy matplotlib

echo.
echo Running Car Rental Recommendation System GUI...
python car_rental_recommender_gui.py
pause 