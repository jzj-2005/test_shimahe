#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
视频流帧提取工具
每5帧保存一张图片，分辨率调整为1920*1080
"""

import cv2
import os
from pathlib import Path
from datetime import datetime


def extract_frames_from_video(video_source, output_folder, frame_interval=5, target_size=(1440, 1080)):
    """
    从视频流中每隔指定帧数提取一帧并保存
    
    参数:
        video_source: 视频源(视频文件路径、RTSP流地址或摄像头索引如0)
        output_folder: 输出文件夹路径
        frame_interval: 帧间隔(默认每5帧保存一次)
        target_size: 目标分辨率(宽, 高), 默认1920*1080
    """
    
    # 创建输出文件夹
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 打开视频源
    cap = cv2.VideoCapture(video_source)
    
    if not cap.isOpened():
        print(f"错误: 无法打开视频源 {video_source}")
        return
    
    # 获取视频信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"视频信息:")
    print(f"  - FPS: {fps}")
    print(f"  - 总帧数: {total_frames if total_frames > 0 else '未知(实时流)'}")
    print(f"  - 提取间隔: 每{frame_interval}帧")
    print(f"  - 目标分辨率: {target_size[0]}x{target_size[1]}")
    print(f"  - 保存路径: {output_path.absolute()}")
    print("-" * 50)
    
    frame_count = 0
    saved_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("视频流结束或读取失败")
                break
            
            # 每隔指定帧数保存一次
            if frame_count % frame_interval == 0:
                # 调整分辨率
                resized_frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_LINEAR)
                
                # 生成文件名(使用时间戳)
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
                filename = f"frame_{saved_count:06d}_{timestamp}.jpg"
                filepath = output_path / filename
                
                # 保存图片
                cv2.imwrite(str(filepath), resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                saved_count += 1
                
                print(f"已保存: {filename} (第{frame_count}帧)")
            
            frame_count += 1
            
            # 按'q'键退出(仅当显示窗口时有效)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("用户中断...")
                break
                
    except KeyboardInterrupt:
        print("\n用户中断操作...")
    
    finally:
        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
        
        print("-" * 50)
        print(f"完成! 共处理 {frame_count} 帧, 保存 {saved_count} 张图片")


def main():
    """主函数"""
    
    # ==================== 配置参数 ====================
    
    # 视频源设置(选择其中一种)
    # 选项1: 视频文件路径
    video_source = "D:\Localsend\【批量压缩】 新建计划13 视频\【批量压缩】 新建计划13 视频\新建计划13 2026-02-11 09_54_24 (UTC+08)\Remote-Control\DJI_20260211095643_0001_V.mp4"
    
    # 选项2: RTSP网络摄像头流
    # video_source = "rtsp://username:password@ip_address:port/stream"
    
    # 选项3: 本地摄像头(0为默认摄像头, 1为第二个摄像头)
    # video_source = 0
    
    # 输出文件夹
    output_folder = "D:\jzj\siluan_new\data\input\siluan_images"
    
    # 帧提取间隔(每5帧保存一次)
    frame_interval = 10
    
    # 目标分辨率(宽x高)
    target_size = (1980, 1080)
    
    # ==================================================
    
    print("=" * 50)
    print("视频帧提取工具")
    print("=" * 50)
    
    # 执行提取
    extract_frames_from_video(
        video_source=video_source,
        output_folder=output_folder,
        frame_interval=frame_interval,
        target_size=target_size
    )


if __name__ == "__main__":
    main()
