@echo off
REM FFmpeg安装 - 步骤2（Chocolatey已安装，现在安装FFmpeg）

echo ============================================================
echo 安装FFmpeg（步骤2）
echo ============================================================
echo.

REM 刷新PATH环境变量
call refreshenv 2>nul

REM 直接安装FFmpeg
echo 正在使用Chocolatey安装FFmpeg...
echo.
choco install ffmpeg -y

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo FFmpeg安装成功！
    echo ============================================================
    echo.
    
    REM 刷新环境变量后验证
    call refreshenv 2>nul
    ffmpeg -version | findstr "ffmpeg version"
    
    echo.
    echo 安装完成！现在可以运行视频推理了。
    echo.
) else (
    echo.
    echo 安装失败，请尝试手动安装：
    echo   1. 打开新的PowerShell窗口
    echo   2. 运行: choco install ffmpeg -y
    echo.
)

pause
