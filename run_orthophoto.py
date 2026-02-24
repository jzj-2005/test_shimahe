"""
正射图片模式快捷启动脚本
"""

import sys
import os

# 兼容 PyTorch 2.6+ - 允许加载可信的 YOLO 模型文件
# 这会禁用 weights_only 的严格检查
os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '0'

from src.orthophoto_pipeline import OrthophotoPipeline


def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("=" * 60)
        print("无人机水利四乱巡检系统 - 正射图片处理模式")
        print("=" * 60)
        print()
        print("用法: python run_orthophoto.py <图片目录路径> [MRK文件路径]")
        print()
        print("参数说明:")
        print("  图片目录路径   - 包含正射图片的目录 (必需)")
        print("  MRK文件路径    - RTK位姿数据文件 (可选，默认自动查找)")
        print()
        print("示例:")
        print('  python run_orthophoto.py "D:\\Localsend\\zhengshe"')
        print('  python run_orthophoto.py "D:\\Localsend\\zhengshe" "D:\\Localsend\\zhengshe\\data.MRK"')
        print()
        print("=" * 60)
        sys.exit(1)
    
    image_dir = sys.argv[1]
    mrk_file = sys.argv[2] if len(sys.argv) >= 3 else None
    
    print("=" * 60)
    print("无人机水利四乱巡检系统 - 正射图片处理模式")
    print("=" * 60)
    print(f"图片目录: {image_dir}")
    if mrk_file:
        print(f"MRK文件: {mrk_file}")
    else:
        print("MRK文件: 自动查找")
    print("=" * 60)
    print("提示: 按ESC键退出可视化窗口")
    print("=" * 60)
    
    # 创建并运行正射图片处理流程
    pipeline = OrthophotoPipeline(config_dir='./config')
    pipeline.run(image_dir=image_dir, mrk_file=mrk_file)
    
    print("\n处理完成!")


if __name__ == '__main__':
    main()
