"""
实时模式快捷启动脚本
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from src.realtime_pipeline import RealtimePipeline


def main():
    """主函数"""
    print("="*60)
    print("无人机水利四乱巡检系统 - 实时处理模式")
    print("="*60)
    print("提示: 按ESC键退出")
    print("="*60)
    
    # 创建并运行实时处理流程
    pipeline = RealtimePipeline(config_dir='./config')
    print(f"本次输出目录: {os.path.abspath(pipeline.run_output_dir)}")
    print("="*60)
    pipeline.run()
    
    print("\n处理完成!")


if __name__ == '__main__':
    main()
