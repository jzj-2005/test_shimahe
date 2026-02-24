"""
RTSP视频流连接测试脚本
用于验证RTSP配置是否正确，能否正常接收视频流

使用方法:
    python test_rtsp_connection.py

要求:
    1. 已配置 config/realtime_config.yaml
    2. RTSP流源在线（无人机图传或机场）
    3. 网络连接正常
    4. 已安装OpenCV: pip install opencv-python
"""

import sys
import time
import yaml
import cv2
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))


def print_separator(char="=", length=60):
    """打印分隔线"""
    print(char * length)


def print_header(title):
    """打印标题"""
    print_separator()
    print(f"  {title}")
    print_separator()


def print_step(step_num, total_steps, description):
    """打印步骤"""
    print(f"\n[{step_num}/{total_steps}] {description}")
    print("-" * 60)


def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent / "config" / "realtime_config.yaml"
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        print("请确保 config/realtime_config.yaml 文件存在")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config['rtsp']
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        sys.exit(1)


def validate_config(rtsp_config):
    """验证配置参数"""
    print("\n配置参数检查:")
    
    issues = []
    
    # 检查URL
    if 'url' not in rtsp_config:
        issues.append("  ❌ 缺少RTSP URL")
    else:
        url = rtsp_config['url']
        if not url.startswith('rtsp://'):
            issues.append(f"  ❌ URL格式错误（应以rtsp://开头）: {url}")
        elif '192.168.1.100' in url or 'your_ip' in url:
            issues.append(f"  ⚠️  URL可能仍为示例地址: {url}")
    
    # 打印结果
    if issues:
        print("\n发现配置问题:")
        for issue in issues:
            print(issue)
        print("\n请修改 config/realtime_config.yaml 后重试")
        return False
    else:
        print("  ✅ 配置参数检查通过")
        return True


def print_config_info(rtsp_config):
    """打印配置信息"""
    print(f"\n当前配置:")
    print(f"  RTSP URL: {rtsp_config['url']}")
    print(f"  传输协议: {rtsp_config.get('transport_protocol', 'tcp')}")
    print(f"  连接超时: {rtsp_config.get('connection_timeout', 10)} 秒")
    print(f"  读取超时: {rtsp_config.get('read_timeout', 5)} 秒")


def test_rtsp_connection(rtsp_url, transport='tcp', timeout=10):
    """测试RTSP连接"""
    print("\n正在连接RTSP流...")
    print(f"  URL: {rtsp_url}")
    print(f"  传输协议: {transport}")
    
    try:
        # 设置OpenCV选项
        options = {
            cv2.CAP_PROP_BUFFERSIZE: 3,
        }
        
        # 创建VideoCapture对象
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        
        # 设置超时
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout * 1000)
        
        # 检查是否打开成功
        if not cap.isOpened():
            print("  ❌ RTSP连接失败!")
            return None
        
        print("  ✅ RTSP连接成功!")
        return cap
        
    except Exception as e:
        print(f"  ❌ 连接异常: {e}")
        return None


def get_stream_info(cap):
    """获取视频流信息"""
    print("\n视频流信息:")
    print_separator("-", 60)
    
    # 获取基本信息
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    
    # 解码FOURCC
    fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
    
    print(f"  分辨率: {width} x {height}")
    print(f"  帧率: {fps:.1f} FPS")
    print(f"  编码格式: {fourcc_str}")
    
    # 验证参数合理性
    issues = []
    if width == 0 or height == 0:
        issues.append("  ⚠️  分辨率为0，可能获取失败")
    if fps == 0:
        issues.append("  ⚠️  帧率为0，可能获取失败")
    
    if issues:
        print("\n发现问题:")
        for issue in issues:
            print(issue)
        print("  注意: 某些RTSP流可能无法准确获取这些参数")
    else:
        print("\n  ✅ 视频流参数正常")
    
    print_separator("-", 60)
    
    return {
        'width': width,
        'height': height,
        'fps': fps,
        'fourcc': fourcc_str
    }


def test_frame_reading(cap, num_frames=30):
    """测试帧读取"""
    print(f"\n测试帧读取... (读取{num_frames}帧)")
    
    success_count = 0
    fail_count = 0
    read_times = []
    
    for i in range(num_frames):
        start_time = time.time()
        ret, frame = cap.read()
        read_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        if ret:
            success_count += 1
            read_times.append(read_time)
            
            # 每读取10帧输出一次
            if (i + 1) % 10 == 0:
                print(f"  已读取 {i+1}/{num_frames} 帧")
        else:
            fail_count += 1
        
        # 短暂延迟避免过快
        time.sleep(0.01)
    
    # 统计结果
    print(f"\n读取结果:")
    print(f"  成功: {success_count} 帧")
    print(f"  失败: {fail_count} 帧")
    print(f"  成功率: {success_count/num_frames*100:.1f}%")
    
    if read_times:
        avg_time = sum(read_times) / len(read_times)
        max_time = max(read_times)
        min_time = min(read_times)
        
        print(f"\n读取耗时统计:")
        print(f"  平均: {avg_time:.1f} ms")
        print(f"  最大: {max_time:.1f} ms")
        print(f"  最小: {min_time:.1f} ms")
    
    # 判断是否正常
    if success_count / num_frames >= 0.95:
        print(f"\n  ✅ 帧读取正常")
        return True
    else:
        print(f"\n  ❌ 帧读取失败率过高")
        return False


def test_frame_quality(cap, num_samples=5):
    """测试帧质量"""
    print(f"\n测试帧质量... (采样{num_samples}帧)")
    
    for i in range(num_samples):
        ret, frame = cap.read()
        
        if not ret:
            print(f"  ❌ 第{i+1}帧读取失败")
            continue
        
        # 检查帧尺寸
        height, width = frame.shape[:2]
        
        # 检查帧内容（计算平均亮度）
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        brightness = gray.mean()
        
        # 判断是否为黑屏或纯色
        if brightness < 10:
            print(f"  ⚠️  第{i+1}帧可能为黑屏 (亮度: {brightness:.1f})")
        elif brightness > 245:
            print(f"  ⚠️  第{i+1}帧可能为白屏 (亮度: {brightness:.1f})")
        else:
            print(f"  ✅ 第{i+1}帧正常 (分辨率: {width}x{height}, 亮度: {brightness:.1f})")
        
        time.sleep(0.5)
    
    print("\n  提示: 如果所有帧都是黑屏，可能的原因:")
    print("    - RTSP流源未发送画面")
    print("    - 相机未启动")
    print("    - 编码格式不支持")


def test_stability(cap, duration=30):
    """测试稳定性"""
    print(f"\n稳定性测试... (持续{duration}秒)")
    print("  监控: 连续读取、帧率稳定性、断流检测")
    print_separator("-", 60)
    
    start_time = time.time()
    frame_count = 0
    fail_count = 0
    frame_times = []
    last_frame_time = time.time()
    
    while time.time() - start_time < duration:
        ret, frame = cap.read()
        current_time = time.time()
        
        if ret:
            frame_count += 1
            
            # 记录帧间隔
            frame_interval = current_time - last_frame_time
            frame_times.append(frame_interval)
            last_frame_time = current_time
            
            # 每5秒输出一次状态
            elapsed = current_time - start_time
            if int(elapsed) % 5 == 0 and int(elapsed) != 0:
                current_fps = frame_count / elapsed
                print(f"  运行时间: {int(elapsed)}秒, 已接收: {frame_count}帧, 当前帧率: {current_fps:.1f}fps")
        else:
            fail_count += 1
            
            # 连续失败过多，可能断流
            if fail_count > 10:
                print(f"  ❌ 检测到断流! (连续{fail_count}次读取失败)")
                break
        
        time.sleep(0.01)
    
    # 统计结果
    elapsed_total = time.time() - start_time
    
    print(f"\n稳定性测试结果:")
    print(f"  测试时长: {elapsed_total:.1f} 秒")
    print(f"  成功读取: {frame_count} 帧")
    print(f"  失败次数: {fail_count}")
    print(f"  平均帧率: {frame_count/elapsed_total:.1f} fps")
    
    if frame_times:
        avg_interval = sum(frame_times) / len(frame_times)
        print(f"  平均帧间隔: {avg_interval*1000:.1f} ms")
    
    # 判断是否稳定
    success_rate = frame_count / (frame_count + fail_count) if (frame_count + fail_count) > 0 else 0
    
    if success_rate >= 0.95 and fail_count < 10:
        print(f"\n  ✅ 稳定性测试通过")
        return True
    else:
        print(f"\n  ❌ 稳定性测试失败")
        return False


def save_test_frame(cap):
    """保存测试帧"""
    print("\n保存测试帧...")
    
    ret, frame = cap.read()
    
    if not ret:
        print("  ❌ 无法读取帧，保存失败")
        return False
    
    # 创建输出目录
    output_dir = Path(__file__).parent / "data" / "output" / "test_frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"rtsp_test_frame_{timestamp}.jpg"
    
    # 保存图片
    cv2.imwrite(str(filename), frame)
    print(f"  ✅ 测试帧已保存: {filename}")
    
    # 显示帧信息
    height, width = frame.shape[:2]
    print(f"  帧尺寸: {width}x{height}")
    
    return True


def print_troubleshooting_tips():
    """打印故障排查提示"""
    print("\n" + "="*60)
    print("故障排查提示:")
    print("="*60)
    print("""
如果测试失败，请检查:

1. RTSP地址配置
   - 确认IP地址正确
   - 确认端口号正确（通常为554或8554）
   - 确认路径正确（如/live或/stream）
   - 如需认证，确认用户名密码正确

2. 网络连接
   - Ping测试: ping 目标IP
   - 端口测试: telnet 目标IP 端口
   - 使用VLC播放器测试: vlc rtsp://...

3. RTSP源状态
   - 确认无人机图传已开启
   - 确认机场视频流已启用
   - 确认相机已启动

4. 传输协议
   - 尝试切换TCP/UDP:
     rtsp:
       transport_protocol: "tcp"  # 或 "udp"

5. 防火墙设置
   - 检查Windows防火墙
   - 检查路由器防火墙
   - 允许端口554/8554通过

6. 编码格式
   - 确认OpenCV支持该编码格式
   - H.264和H.265通常支持
   - 如有问题，尝试在源端更改编码

7. 使用其他工具测试
   - VLC播放器: vlc rtsp://...
   - FFplay: ffplay -rtsp_transport tcp rtsp://...
   - RTSP Simple Server (测试用)

8. 获取帮助
   - 查看开发指南: 无人机实时流处理配置与开发指南.md
   - 查看机场/无人机用户手册
""")


def main():
    """主函数"""
    print_header("RTSP视频流连接测试")
    
    # 步骤1: 加载配置
    print_step(1, 6, "加载配置文件")
    rtsp_config = load_config()
    print("  ✅ 配置文件加载成功")
    
    # 显示配置信息
    print_config_info(rtsp_config)
    
    # 验证配置
    if not validate_config(rtsp_config):
        sys.exit(1)
    
    # 步骤2: 连接RTSP
    print_step(2, 6, "连接RTSP流")
    cap = test_rtsp_connection(
        rtsp_config['url'],
        rtsp_config.get('transport_protocol', 'tcp'),
        rtsp_config.get('connection_timeout', 10)
    )
    
    if not cap:
        print("\n可能的原因:")
        print("  1. RTSP地址错误")
        print("  2. 网络连接问题")
        print("  3. RTSP源未启动")
        print("  4. 需要认证但未提供")
        print_troubleshooting_tips()
        sys.exit(1)
    
    # 步骤3: 获取流信息
    print_step(3, 6, "获取视频流信息")
    stream_info = get_stream_info(cap)
    
    # 步骤4: 测试帧读取
    print_step(4, 6, "测试帧读取")
    read_success = test_frame_reading(cap, num_frames=30)
    
    if not read_success:
        cap.release()
        print_troubleshooting_tips()
        sys.exit(1)
    
    # 步骤5: 测试帧质量
    print_step(5, 6, "测试帧质量")
    test_frame_quality(cap, num_samples=5)
    
    # 保存测试帧
    save_test_frame(cap)
    
    # 步骤6: 稳定性测试（可选）
    print_step(6, 6, "稳定性测试")
    response = input("\n是否进行30秒稳定性测试? (y/n): ")
    
    if response.lower() == 'y':
        stability_success = test_stability(cap, duration=30)
        if stability_success:
            print("\n  ✅ 稳定性测试通过")
        else:
            print("\n  ❌ 稳定性测试失败")
    else:
        print("  跳过稳定性测试")
    
    # 释放资源
    cap.release()
    print("\n✅ RTSP连接已关闭")
    
    # 最终结果
    print_header("测试结果总结")
    print("✅ RTSP连接测试通过!")
    print("✅ 能够正常接收视频流")
    print("✅ 帧读取正常")
    
    print("\n下一步:")
    print("  1. 测试MQTT位姿数据连接: python test_mqtt_realtime.py")
    print("  2. 运行完整实时处理: python run_realtime.py")
    print("  3. 查看开发指南了解更多配置选项")
    print_separator()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        print_troubleshooting_tips()
        sys.exit(1)
