from ultralytics import YOLO
import cv2
import os

# 加载模型
model = YOLO('D:\jzj\siluan_new\models\yolo11x-obb_1280.pt')

# 输入输出路径
input_video = "D:/jzj/siluan_new/data/input/videos/3月3日.mp4"
output_video = 'D:/jzj/siluan_new/data/output/videos/siluan02121_detected3.mp4'

# 确保输出目录存在
output_dir = os.path.dirname(output_video)
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 打开视频
cap = cv2.VideoCapture(input_video)
if not cap.isOpened():
    print(f"错误: 无法打开视频 {input_video}")
    exit()

# 获取视频属性
fps = int(cap.get(cv2.CAP_PROP_FPS))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

print(f"视频信息: {width}x{height}, {fps}fps, 共{total_frames}帧")

# 创建输出视频
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))

if not out.isOpened():
    print("错误: 无法创建输出视频")
    cap.release()
    exit()

frame_count = 0

# 处理每一帧
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1

    # YOLO检测
    results = model(frame, conf=0.25)  # 可调整置信度阈值

    # 绘制结果（缩小字体和线宽，减少对目标的遮挡）
    annotated_frame = results[0].plot(font_size=10, line_width=1)

    # 写入输出
    out.write(annotated_frame)

    # 显示进度
    print(f"处理进度: {frame_count}/{total_frames} ({frame_count / total_frames * 100:.1f}%)", end='\r')

# 清理资源
cap.release()
out.release()
print(f"\n处理完成！结果已保存到 {output_video}")