@echo off
chcp 65001 >nul
echo ======================================================================
echo 石马河四乱检测系统 v2.1 功能测试
echo ======================================================================
echo.

echo [1/5] 检查环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    pause
    exit /b 1
)
echo ✓ Python环境正常

echo.
echo [2/5] 检查CSV数据...
if not exist "data\output\csv\detections_offline.csv" (
    echo ⚠️ 未找到CSV文件，将跳过后处理测试
    echo.
    echo 请先运行检测生成数据：
    echo   python src/main.py --mode offline --video ^<视频文件^>
    echo.
    pause
    exit /b 0
)

echo ✓ 找到CSV文件
for %%A in ("data\output\csv\detections_offline.csv") do set csv_size=%%~zA
echo   文件大小: %csv_size% 字节

echo.
echo [3/5] 测试后处理功能...
python test_post_processing.py
if errorlevel 1 (
    echo.
    echo ❌ 后处理测试失败
    echo 请查看上面的错误信息
    pause
    exit /b 1
)

echo.
echo [4/5] 验证输出文件...
set /a file_count=0

if exist "data\output\geojson\detections_raw.geojson" (
    echo ✓ detections_raw.geojson
    set /a file_count+=1
)

if exist "data\output\geojson\detections_unique.geojson" (
    echo ✓ detections_unique.geojson
    set /a file_count+=1
)

if exist "data\output\geojson\detections_high_conf.geojson" (
    echo ✓ detections_high_conf.geojson
    set /a file_count+=1
)

if exist "data\output\map_test.html" (
    echo ✓ map_test.html
    set /a file_count+=1
)

if exist "data\output\summary_test.txt" (
    echo ✓ summary_test.txt
    set /a file_count+=1
)

echo.
echo 生成文件数: %file_count%/5

if %file_count% LSS 5 (
    echo ⚠️ 部分文件未生成，请检查配置和日志
)

echo.
echo [5/5] 打开查看结果...
echo.
echo 是否打开测试地图？ (Y/N)
set /p open_map=
if /i "%open_map%"=="Y" (
    if exist "data\output\map_test.html" (
        start data\output\map_test.html
        echo ✓ 地图已在浏览器中打开
    ) else (
        echo ❌ 地图文件不存在
    )
)

echo.
echo ======================================================================
echo 测试完成！
echo ======================================================================
echo.
echo 生成的测试文件：
echo   - 地图: data\output\map_test.html
echo   - 摘要: data\output\summary_test.txt
echo   - GeoJSON: data\output\geojson\detections_*.geojson
echo.
echo 下一步：
echo   1. 查看地图验证可视化效果
echo   2. 在QGIS中导入GeoJSON验证数据
echo   3. 查看summary_test.txt了解统计信息
echo   4. 如果测试通过，可以正常使用系统进行巡检
echo.
echo ======================================================================
pause
