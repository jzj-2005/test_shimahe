@echo off
echo ========================================
echo Installing dependencies for Orthophoto Processing
echo ========================================
echo.

echo [1/3] Installing core packages...
pip install opencv-python numpy pandas pyyaml tqdm loguru pillow

echo.
echo [2/3] Installing PyTorch and Ultralytics (YOLO)...
pip install torch torchvision ultralytics

echo.
echo [3/3] Installing optional visualization packages...
pip install matplotlib

echo.
echo ========================================
echo Installation completed!
echo ========================================
echo.
echo You can now run:
echo   python run_orthophoto.py "D:\Localsend\zhengshe"
echo.
pause
