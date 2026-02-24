@echo off
echo ========================================
echo Installing PyTorch with CUDA Support
echo ========================================
echo.

echo [1/2] Uninstalling CPU version...
pip uninstall torch torchvision -y

echo.
echo [2/2] Installing GPU version (CUDA 12.1)...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

echo.
echo ========================================
echo Verifying installation...
echo ========================================
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device count:', torch.cuda.device_count()); print('Device name:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"

echo.
echo ========================================
echo Installation completed!
echo ========================================
echo.
pause
