"""
HTTP OSD 接口快速测试
用法: python tools/test_http_osd.py [--sn 设备SN] [--url 服务地址] [--loop 持续轮询秒数]
"""

import argparse
import sys
import time
from pathlib import Path

import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "realtime_config.yaml"


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None


def single_request(url: str, dev_sn: str, timeout: float = 3.0) -> dict | None:
    """发送一次 GET 请求并返回解析结果"""
    t0 = time.time()
    try:
        resp = requests.get(url, params={"devSn": dev_sn}, timeout=timeout)
        latency_ms = (time.time() - t0) * 1000
        resp.raise_for_status()
        body = resp.json()
    except requests.RequestException as e:
        print(f"[FAIL] 请求失败: {e}")
        return None

    code = body.get("code")
    if code not in (0, 200):
        print(f"[FAIL] 接口返回错误 code={code}, msg={body.get('msg')}")
        return None

    data = body.get("data")
    if not data or not isinstance(data, dict):
        print(f"[FAIL] data 字段为空或格式异常: {body}")
        return None

    return {"data": data, "latency_ms": latency_ms}


def print_osd(data: dict, latency_ms: float, index: int = 0):
    lat = data.get("latitude", 0)
    lon = data.get("longitude", 0)
    alt = data.get("altitude", 0)
    yaw = data.get("yaw", 0)
    pitch = data.get("pitch", 0)
    roll = data.get("roll", 0)
    sat = data.get("satellite_count", data.get("satelliteCount", "N/A"))
    bat = data.get("battery_percent", data.get("batteryPercent", "N/A"))
    rel_h = data.get("relative_height", data.get("relativeHeight", "N/A"))
    g_pitch = data.get("gimbal_pitch", data.get("gimbalPitch", "N/A"))
    spd = data.get("ground_speed", data.get("groundSpeed", "N/A"))

    if index > 0:
        prefix = f"[#{index:04d}]"
    else:
        prefix = "[OK]"

    print(f"{prefix} 延迟 {latency_ms:.0f}ms | "
          f"GPS({lat:.6f}, {lon:.6f}) 海拔{alt:.1f}m | "
          f"姿态(yaw={yaw:.1f}, pitch={pitch:.1f}, roll={roll:.1f}) | "
          f"卫星{sat} 电量{bat}% 相对高度{rel_h}m 地速{spd}m/s 云台俯仰{g_pitch}")


def main():
    parser = argparse.ArgumentParser(description="HTTP OSD 接口快速测试")
    parser.add_argument("--sn", help="设备序列号 (默认读取配置文件)")
    parser.add_argument("--url", help="完整接口地址 (默认读取配置文件)")
    parser.add_argument("--loop", type=int, default=0,
                        help="持续轮询秒数 (0=仅单次测试)")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="轮询间隔秒数 (默认1)")
    args = parser.parse_args()

    cfg = load_config()
    http_cfg = (cfg or {}).get("http_osd", {})

    base_url = http_cfg.get("base_url", "http://10.5.52.129:10006")
    api_path = http_cfg.get("api_path", "/satxspace-airspace/ai/getDrone")
    dev_sn = args.sn or http_cfg.get("dev_sn", "")
    full_url = args.url or f"{base_url.rstrip('/')}{api_path}"

    if not dev_sn:
        print("[ERROR] 未指定设备SN。请通过 --sn 参数或 config/realtime_config.yaml 中的 http_osd.dev_sn 设置")
        sys.exit(1)

    print("=" * 70)
    print("HTTP OSD 接口快速测试")
    print("=" * 70)
    print(f"  接口地址: {full_url}")
    print(f"  设备SN  : {dev_sn}")
    print(f"  模式    : {'持续轮询 ' + str(args.loop) + 's' if args.loop else '单次测试'}")
    print("=" * 70)

    # --- 单次测试 ---
    result = single_request(full_url, dev_sn)
    if result is None:
        print("\n连接失败，请检查:")
        print("  1. 网络是否能访问到服务地址")
        print("  2. 设备SN是否正确")
        print("  3. 无人机是否已上电并联网")
        sys.exit(1)

    print_osd(result["data"], result["latency_ms"])

    gps_valid = result["data"].get("latitude", 0) != 0 and result["data"].get("longitude", 0) != 0
    print(f"\n  GPS有效: {'是' if gps_valid else '否 (经纬度为0，可能未锁星)'}")
    print(f"  返回字段数: {len(result['data'])}")
    print(f"  字段列表: {', '.join(sorted(result['data'].keys()))}")

    if args.loop <= 0:
        print("\n单次测试完成。加 --loop 30 可持续轮询30秒。")
        return

    # --- 持续轮询 ---
    print(f"\n开始持续轮询 {args.loop}s (间隔 {args.interval}s)，Ctrl+C 可提前终止...\n")
    deadline = time.time() + args.loop
    count = 0
    errors = 0
    latencies = []

    try:
        while time.time() < deadline:
            r = single_request(full_url, dev_sn)
            count += 1
            if r:
                latencies.append(r["latency_ms"])
                print_osd(r["data"], r["latency_ms"], index=count)
            else:
                errors += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n用户中断")

    print("\n" + "=" * 70)
    print("轮询统计")
    print("=" * 70)
    print(f"  总请求: {count}, 成功: {count - errors}, 失败: {errors}")
    if latencies:
        print(f"  延迟: 平均 {sum(latencies)/len(latencies):.0f}ms, "
              f"最小 {min(latencies):.0f}ms, 最大 {max(latencies):.0f}ms")


if __name__ == "__main__":
    main()
