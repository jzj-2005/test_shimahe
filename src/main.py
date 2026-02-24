"""
主程序入口
支持离线和实时两种模式
"""

import sys
import argparse
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.offline_pipeline import OfflinePipeline
from src.realtime_pipeline import RealtimePipeline


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='无人机水利四乱巡检系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  # 离线模式
  python main.py --mode offline --video ./data/input/videos/DJI_0001.MP4
  
  # 实时模式
  python main.py --mode realtime
  
  # 指定配置目录
  python main.py --mode offline --video test.mp4 --config ./config
        '''
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['offline', 'realtime'],
        required=True,
        help='运行模式: offline(离线处理) 或 realtime(实时处理)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='./config',
        help='配置文件目录路径 (默认: ./config)'
    )
    
    parser.add_argument(
        '--video',
        type=str,
        help='视频文件路径 (仅离线模式需要)'
    )
    
    args = parser.parse_args()
    
    # 运行对应模式的流程
    if args.mode == 'offline':
        print("="*60)
        print("离线处理模式")
        print("="*60)
        
        pipeline = OfflinePipeline(config_dir=args.config)
        pipeline.run(video_path=args.video)
        
    elif args.mode == 'realtime':
        print("="*60)
        print("实时处理模式")
        print("="*60)
        
        pipeline = RealtimePipeline(config_dir=args.config)
        pipeline.run()
    
    print("\n程序结束")


if __name__ == '__main__':
    main()
