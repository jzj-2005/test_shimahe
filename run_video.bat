@echo off
REM 视频推理快速启动脚本
REM 用法: run_video.bat "视频路径.MP4"

echo ============================================================
echo 无人机视频推理 - 快速启动
echo ============================================================
echo.

REM 检查参数
if "%~1"=="" (
    echo 错误: 请提供视频文件路径
    echo.
    echo 用法: run_video.bat "视频路径.MP4"
    echo 示例: run_video.bat "data\input\videos\DJI_0001.MP4"
    pause
    exit /b 1
)

REM 检查文件是否存在
if not exist "%~1" (
    echo 错误: 视频文件不存在: %~1
    pause
    exit /b 1
)

echo 视频文件: %~1
echo.

REM 激活环境并运行
echo 激活conda环境...
call conda activate yolo11m-orthophoto

echo.
echo 开始处理视频...
echo.
python run_offline.py "%~1"

echo.
echo ============================================================
echo 处理完成！
echo ============================================================
echo.
echo 下一步操作:
echo   1. 导出GeoJSON: python tools\export_to_geojson.py
echo   2. 查看地图:   python tools\quick_visualize.py
echo   3. 验证坐标:   python tools\sample_validation.py
echo   4. 生成报告:   python tools\generate_report.py
echo.
pause
