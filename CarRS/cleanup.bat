@echo off
echo ================================================
echo  CLEANING UP REDUNDANT FILES
echo ================================================
echo.

echo The following files will be deleted:
echo  - run_gui.bat
echo  - run_recommender.bat
echo  - run_with_data.bat
echo  - run_fixed_app.bat
echo  - run_direct_load.bat
echo  - load_and_run.py
echo  - direct_load.py
echo.

set /p confirm=Are you sure you want to delete these files? (Y/N):

if /i "%confirm%"=="Y" (
  echo.
  echo Deleting redundant files...
  
  if exist run_gui.bat (
    del run_gui.bat
    echo Deleted: run_gui.bat
  )
  
  if exist run_recommender.bat (
    del run_recommender.bat
    echo Deleted: run_recommender.bat
  )
  
  if exist run_with_data.bat (
    del run_with_data.bat
    echo Deleted: run_with_data.bat
  )
  
  if exist run_fixed_app.bat (
    del run_fixed_app.bat
    echo Deleted: run_fixed_app.bat
  )
  
  if exist run_direct_load.bat (
    del run_direct_load.bat
    echo Deleted: run_direct_load.bat
  )
  
  if exist load_and_run.py (
    del load_and_run.py
    echo Deleted: load_and_run.py
  )
  
  if exist direct_load.py (
    del direct_load.py
    echo Deleted: direct_load.py
  )
  
  echo.
  echo Cleanup completed successfully!
  echo Only CarRentalApp.bat and necessary files remain.
  ) else (
  echo.
  echo Cleanup cancelled. No files were deleted.
)

echo.
echo Press any key to exit...
pause > nul
