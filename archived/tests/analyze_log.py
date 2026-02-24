"""分析最新运行的日志"""
import re

log_file = r"C:\Users\EDY\.cursor\projects\d-jzj-siluan-new\terminals\901067.txt"

with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# 找到最新运行的开始
latest_run_start = -1
for i in range(len(lines) - 1, -1, -1):
    if "开始处理正射图片" in lines[i]:
        latest_run_start = i
        break

if latest_run_start == -1:
    print("未找到最新运行的开始")
    exit()

print(f"找到最新运行开始于第 {latest_run_start} 行")
print("\n" + "="*60)
print("最新运行的关键日志:")
print("="*60)

# 提取关键信息
for i in range(latest_run_start, min(latest_run_start + 100, len(lines))):
    line = lines[i]
    if any(kw in line for kw in ["步骤", "MRK", "位姿", "检测器调试", "同步器调试", "【调试】", "容差"]):
        print(line.strip())

# 查找匹配失败的日志
print("\n" + "="*60)
print("位姿匹配情况:")
print("="*60)

matched = 0
unmatched = 0
for i in range(latest_run_start, len(lines)):
    if "未找到匹配的位姿数据" in lines[i]:
        unmatched += 1
        if unmatched <= 3:  # 只打印前3条
            print(lines[i].strip())
    elif "成功匹配位姿数据" in lines[i]:
        matched += 1
        if matched <= 3:  # 只打印前3条
            print(lines[i].strip())

print(f"\n匹配成功: {matched}")
print(f"匹配失败: {unmatched}")
