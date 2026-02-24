"""
离线模式快捷启动脚本
"""

import sys
from src.offline_pipeline import OfflinePipeline


def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python run_offline.py <视频文件路径>")
        print("示例: python run_offline.py ./data/input/videos/DJI_0001.MP4")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    print("="*60)
    print("无人机水利四乱巡检系统 - 离线处理模式")
    print("="*60)
    print(f"视频文件: {video_path}")
    print("="*60)
    
    # 创建并运行离线处理流程
    pipeline = OfflinePipeline(config_dir='./config')
    pipeline.run(video_path=video_path)
    
    print("\n处理完成!")


if __name__ == '__main__':
    main()
