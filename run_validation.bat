@echo off
REM 完整验证流程脚本
REM 处理完视频后运行此脚本完成所有验证步骤

echo ============================================================
echo 视频推理结果验证流程
echo ============================================================
echo.

REM 激活环境
call conda activate yolo11m-orthophoto

REM 检查CSV是否存在
if not exist "data\output\csv\detections_offline.csv" (
    echo ✗ 未找到检测结果文件！
    echo.
    echo 请先运行: python run_offline.py "视频路径.MP4"
    echo.
    pause
    exit /b 1
)

echo ✓ 检测结果文件已找到
echo.

REM 步骤1: 导出GeoJSON
echo ============================================================
echo 步骤1: 导出GeoJSON格式
echo ============================================================
python tools\export_to_geojson.py data\output\csv\detections_offline.csv
if %ERRORLEVEL% NEQ 0 (
    echo ✗ 导出失败！
    pause
    exit /b 1
)
echo.

REM 步骤2: 打开地图
echo ============================================================
echo 步骤2: 在浏览器中查看地图
echo ============================================================
echo 正在打开地图...
python tools\quick_visualize.py
echo.
echo 请在浏览器中检查检测框位置是否合理
echo.
pause
echo.

REM 步骤3: 抽样验证（可选）
echo ============================================================
echo 步骤3: 抽样验证坐标准确度（可选）
echo ============================================================
choice /C YN /M "是否进行抽样验证（需要5-10分钟）"
if %ERRORLEVEL% EQU 1 (
    echo.
    echo 启动抽样验证工具...
    python tools\sample_validation.py --samples 20
    echo.
    echo 请在浏览器中完成验证操作
    echo.
    pause
    echo.
) else (
    echo 跳过抽样验证
    echo.
)

REM 步骤4: 生成报告
echo ============================================================
echo 步骤4: 生成提交报告
echo ============================================================

REM 检查是否有验证结果
set VALIDATION_FILE=
for %%f in (data\output\validation_results_*.json) do set VALIDATION_FILE=%%f

if defined VALIDATION_FILE (
    echo 找到验证结果: %VALIDATION_FILE%
    python tools\generate_report.py --validation "%VALIDATION_FILE%"
) else (
    echo 未找到验证结果，生成基础报告
    python tools\generate_report.py
)

if %ERRORLEVEL% NEQ 0 (
    echo ✗ 报告生成失败！
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✅ 验证流程完成！
echo ============================================================
echo.
echo 交付文件位置:
echo   - CSV结果:    data\output\csv\detections_offline.csv
echo   - GeoJSON:    data\output\detections.geojson
echo   - 地图:       data\output\map.html
echo   - 报告:       data\output\delivery_report.md
echo.
echo 请打包以上文件提交给公司
echo.

pause
