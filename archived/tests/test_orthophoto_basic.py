"""
正射图片处理基础功能测试
测试MRK解析器和图片序列读取器
"""

import sys
sys.path.insert(0, 'd:/jzj/siluan_new')

from src.input.mrk_parser import MRKParser
from src.input.image_sequence_reader import ImageSequenceReader


def test_mrk_parser():
    """测试MRK解析器"""
    print("="*60)
    print("测试1: MRK文件解析")
    print("="*60)
    
    mrk_file = "D:/Localsend/zhengshe/DJI_20260204142623_0002_D.MRK"
    
    parser = MRKParser()
    pose_data = parser.parse(mrk_file)
    
    if pose_data:
        print(f"[OK] MRK file parsing successful")
        print(f"  Total poses: {len(pose_data)}")
        parser.print_sample(3)
        return True
    else:
        print("[FAIL] MRK file parsing failed")
        return False


def test_image_reader():
    """测试图片序列读取器"""
    print("\n" + "="*60)
    print("测试2: 图片序列读取")
    print("="*60)
    
    image_dir = "D:/Localsend/zhengshe"
    
    reader = ImageSequenceReader(
        image_dir=image_dir,
        image_pattern="*.jpeg",
        start_index=0,
        end_index=5  # 只读取前5张
    )
    
    if not reader.open():
        print("[FAIL] Open image sequence failed")
        return False
    
    print(f"[OK] Image sequence opened successfully")
    reader.print_info()
    
    # 读取并测试前3张图片
    print("\n读取前3张图片:")
    for i in range(3):
        success, image, metadata = reader.read()
        if success and image is not None:
            print(f"  图片 {i+1}: {metadata['filename']}")
            print(f"    尺寸: {metadata['width']}x{metadata['height']}")
            print(f"    时间戳: {metadata['timestamp']}")
        else:
            print(f"  图片 {i+1}: 读取失败")
            break
    
    reader.close()
    return True


def main():
    """主测试函数"""
    print("正射图片处理基础功能测试")
    print("="*60)
    
    # 测试MRK解析器
    mrk_ok = test_mrk_parser()
    
    # 测试图片读取器
    img_ok = test_image_reader()
    
    # 总结
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"MRK Parser: {'[OK] PASS' if mrk_ok else '[FAIL]'}")
    print(f"Image Reader: {'[OK] PASS' if img_ok else '[FAIL]'}")
    print("="*60)
    
    if mrk_ok and img_ok:
        print("\n[OK] All basic tests passed!")
        print("\nNext steps:")
        print("  1. Install full dependencies: pip install -r requirements.txt")
        print("  2. Run full pipeline: python run_orthophoto.py \"D:\\Localsend\\zhengshe\"")
    else:
        print("\n[FAIL] Some tests failed, please check error messages")


if __name__ == '__main__':
    main()
