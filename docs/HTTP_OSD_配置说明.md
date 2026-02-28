# HTTP OSD 数据源配置说明

> 版本: v2.2  
> 日期: 2026-02-28  
> 适用设备: DJI M3TD / M4TD

---

## 1. 概述

### 1.1 背景

实时巡检系统需要获取无人机的 OSD（On-Screen Display）数据，包括 GPS 坐标、飞行高度、姿态角等，用于将检测目标的像素坐标转换为地理坐标。

原有方案直连 DJI Cloud API MQTT 获取 OSD 数据。现在开发部已将 MQTT 数据桥接为 HTTP 接口，本次升级新增了 HTTP 数据源支持，并实现了三级降级策略。

### 1.2 数据源层级

```
HTTP 接口（优先）→ MQTT 直连（备选）→ OCR 画面识别（兜底）
```

| 数据源 | 协议 | 延迟 | 精度 | 依赖 |
|--------|------|------|------|------|
| HTTP   | HTTP GET 轮询 | ~100ms | 与MQTT一致 | 开发部桥接服务 |
| MQTT   | MQTT 订阅推送 | ~50ms  | 原始精度 | DJI Cloud API |
| OCR    | 视频帧 OCR | ~500ms | 较低 | PaddleOCR |

### 1.3 架构图

```
                  ┌──────────────────┐
                  │  DJI M3TD/M4TD   │
                  └──────┬───────────┘
                         │ MQTT OSD (~10Hz)
                         ▼
              ┌──────────────────────┐
              │ 开发部 MQTT→HTTP     │
              │ 桥接服务             │
              │ (10.5.52.129:10006)  │
              └──────────┬───────────┘
                         │ HTTP GET
                         ▼
┌────────────────────────────────────────────┐
│           实时巡检系统                       │
│                                            │
│  ┌─────────────┐  ┌─────────────┐          │
│  │ HttpOsdClient│  │DJIMQTTClient│          │
│  │ (HTTP轮询)   │  │ (MQTT订阅)  │          │
│  └──────┬──────┘  └──────┬──────┘          │
│         │    统一接口     │                  │
│         └───────┬────────┘                  │
│                 ▼                           │
│         ┌──────────────┐                    │
│         │ _get_pose()  │ ← OSD OCR (兜底)  │
│         └──────┬───────┘                    │
│                ▼                           │
│    ┌────────────────────┐                  │
│    │ YOLO检测 + 坐标转换 │                  │
│    └────────────────────┘                  │
└────────────────────────────────────────────┘
```

---

## 2. HTTP 接口说明

### 2.1 接口信息

| 项目 | 值 |
|------|---|
| 方法 | `GET` |
| 地址 | `http://10.5.52.129:10006/satxspace-airspace/ai/getDrone` |
| 参数 | `devSn` — 设备序列号 |
| 文档 | https://s.apifox.cn/241bc285-9a83-43cd-9f71-e927407134ec |

### 2.2 响应格式

```json
{
    "code": 0,
    "msg": "",
    "data": {
        "latitude": 22.779954,
        "longitude": 114.100891,
        "altitude": 139.231,
        "pitch": -88.5,
        "yaw": 45.2,
        "roll": 0.1,
        "gimbal_pitch": -90.0,
        "gimbal_yaw": 0.0,
        "gimbal_roll": 0.0,
        "satellite_count": 18,
        "altitude_above_sea_level": 139.231,
        "relative_height": 120.5,
        "velocity_z": 0.1,
        "ground_speed": 3.1,
        "battery_percent": 68
    }
}
```

### 2.3 可用字段清单

**核心字段（坐标转换必需）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `latitude` | float | 纬度（WGS84） |
| `longitude` | float | 经度（WGS84） |
| `altitude` | float | 海拔高度（米） |
| `yaw` | float | 偏航角/航向（度），0=正北 |
| `pitch` | float | 俯仰角（度），-90=垂直向下 |
| `roll` | float | 横滚角（度） |

**扩展字段（可选）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `gimbal_pitch` | float | 云台俯仰角 |
| `gimbal_yaw` | float | 云台偏航角 |
| `gimbal_roll` | float | 云台横滚角 |
| `satellite_count` | int | 可见卫星数 |
| `altitude_above_sea_level` | float | 海拔高度 |
| `relative_height` | float | 相对起飞点高度 |
| `velocity_z` | float | 垂直速度（m/s） |
| `ground_speed` | float | 地速（m/s） |
| `battery_percent` | int | 电池电量百分比 |

**HTTP 接口不可用的字段（仅 MQTT 有）：**

| 字段 | 影响 |
|------|------|
| `gpsLevel` | GPS质量控制：信号强度评估不可用，改为卫星数评估 |
| `positioningState` | GPS质量控制：无法识别RTK模式，默认按普通GPS处理 |
| `hdop` / `vdop` | 精度因子不可用，不影响坐标转换 |
| `velocityX` / `velocityY` | 水平分速度不可用，不影响坐标转换 |
| `angularVelocityZ` | 角速度不可用，不影响坐标转换 |
| `compassHeading` | 指南针航向不可用（已有yaw替代） |
| `homeDistance` / `flightTime` | 辅助信息不可用，不影响坐标转换 |

> **结论：** 坐标转换所需的6个核心字段全部可用，HTTP模式不影响定位精度。缺失字段仅影响GPS质量评估的精细程度，已做兼容处理。

---

## 3. 配置方法

### 3.1 配置文件

编辑 `config/realtime_config.yaml`：

```yaml
# ========== OSD数据源选择 ==========
# "http"  - 仅使用HTTP接口
# "mqtt"  - 仅使用DJI MQTT直连
# "auto"  - HTTP优先，不可用时自动降级到MQTT（推荐）
osd_source: "auto"

# ========== HTTP OSD接口配置 ==========
http_osd:
  base_url: "http://10.5.52.129:10006"
  api_path: "/satxspace-airspace/ai/getDrone"
  dev_sn: "1581F6Q8D248E00G0M54"     # ← 替换为实际设备SN
  poll_interval: 0.1                   # 轮询间隔（秒）
  request_timeout: 2                   # 请求超时（秒）
  max_retry: 3                         # 连续失败标记不可用
  pose_buffer_size: 100                # 位姿缓冲区大小
```

### 3.2 三种模式说明

#### 模式一：`osd_source: "http"`

仅使用 HTTP 接口，不连接 MQTT。

适用场景：
- 不需要直连 DJI Cloud API
- 网络环境只允许 HTTP
- 开发/测试阶段

#### 模式二：`osd_source: "mqtt"`

保持原有逻辑，仅使用 MQTT 直连。

适用场景：
- HTTP 桥接服务不可用
- 需要获取完整的 OSD 字段（含 gpsLevel、positioningState 等）
- 需要 RTK 质量识别

#### 模式三：`osd_source: "auto"`（推荐）

启动时先尝试 HTTP 连接，成功则以 HTTP 为主数据源，同时尝试连接 MQTT 作为备选。

降级策略：
1. 启动时 HTTP 连接失败 → 直接使用 MQTT
2. 运行中 HTTP 连续 30 帧无数据 → 自动切换到 MQTT
3. MQTT 也无数据 → OCR 从视频画面识别（如已启用）

### 3.3 设备SN获取方法

HTTP 接口和 MQTT 使用相同的设备 SN：

1. **从 DJI Pilot 2 查看**：设置 → 关于 → 设备信息 → 序列号
2. **从机场管理界面**：系统信息 → 设备序列号
3. **从 DJI 开发者平台**：应用管理 → 设备管理 → 已绑定设备

---

## 4. 代码架构

### 4.1 新增文件

| 文件 | 说明 |
|------|------|
| `src/input/http_osd_client.py` | HTTP OSD 客户端，后台轮询线程 + 位姿缓冲区 |

### 4.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `config/realtime_config.yaml` | 新增 `osd_source` 和 `http_osd` 配置段 |
| `src/realtime_pipeline.py` | 集成 HTTP/MQTT/auto 模式调度逻辑 |
| `src/transform/coord_transform_new.py` | 质量评估兼容 HTTP 缺失字段 |

### 4.3 HttpOsdClient 接口

`HttpOsdClient` 与 `DJIMQTTClient` 具有相同的外部接口，便于管道层统一调度：

```python
class HttpOsdClient:
    def connect(self, timeout=10) -> bool      # 验证接口并启动轮询
    def disconnect()                            # 停止轮询
    def get_latest_pose() -> Optional[dict]     # 获取最新位姿
    def get_pose_buffer() -> list               # 获取缓冲区
    def get_stats() -> dict                     # 获取统计信息
    def print_stats()                           # 打印统计
```

### 4.4 位姿数据格式

无论来自 HTTP 还是 MQTT，输出的 pose 字典格式一致：

```python
{
    "timestamp": 1707730815123,    # Unix毫秒时间戳
    "latitude": 22.779954,         # 纬度 (WGS84)
    "longitude": 114.100891,       # 经度 (WGS84)
    "altitude": 139.231,           # 海拔高度 (米)
    "yaw": 45.2,                   # 偏航角 (度)
    "pitch": -88.5,                # 俯仰角 (度)
    "roll": 0.1,                   # 横滚角 (度)
    "source": "http",              # 数据来源标识
    # ... 扩展字段
}
```

### 4.5 字段命名兼容

HTTP 接口返回的字段名可能是 camelCase（如 `gimbalPitch`）或 snake_case（如 `gimbal_pitch`），客户端解析时两种格式都会尝试匹配。

---

## 5. GPS 质量控制适配

### 5.1 问题

HTTP 接口不返回 `gpsLevel` 和 `positioningState` 字段。增强版坐标转换器的 GPS 质量评估原本依赖这两个字段，如果不做处理，`gpsLevel` 默认为 0 会导致所有数据被标记为 INVALID 而拒绝处理。

### 5.2 解决方案

修改 `CoordinateTransformerEnhanced.evaluate_gps_quality()` 方法：

- 当 `gps_level` 字段缺失（None）时，不执行信号强度检查
- 改为仅基于 `satellite_count`（卫星数）进行评估
- 卫星数也缺失时，默认返回 `MEDIUM` 质量而非 `INVALID`

评估逻辑对照表：

| gps_level | satellite_count | 评估结果 | 是否跳过 |
|-----------|-----------------|----------|---------|
| 有值，< 3 | 任意 | INVALID/LOW | 是（可配置） |
| 有值，3-4 | >= 10 | MEDIUM | 否 |
| 有值，>= 5 | >= 15 | HIGH | 否 |
| 缺失 | >= 15 | HIGH | 否 |
| 缺失 | 10-14 | MEDIUM | 否 |
| 缺失 | 1-9 | LOW | 否（不跳过） |
| 缺失 | 0/缺失 | MEDIUM | 否（保守放行） |

### 5.3 对坐标转换精度的影响

**无影响。** 坐标转换的数学计算（3D旋转矩阵 → 射线-地面相交 → 偏移量转经纬度）仅依赖 6 个核心字段（lat, lon, alt, yaw, pitch, roll），不使用质量指标字段。

质量控制的作用是**过滤和标记**，不参与坐标计算。HTTP 模式下：
- 坐标转换结果与 MQTT 模式完全一致
- RTK 固定解无法被识别（无 `positioningState`），误差估算会偏保守（显示 5m 而非实际的 0.05m）
- 不会因缺少 `gpsLevel` 而误拒有效数据

---

## 6. 运行与验证

### 6.1 快速测试 HTTP 接口

可以先用 curl 或浏览器验证接口：

```bash
curl "http://10.5.52.129:10006/satxspace-airspace/ai/getDrone?devSn=你的设备SN"
```

确认返回 `"code": 0` 且 `data` 中包含有效的经纬度数据。

### 6.2 启动实时巡检

```bash
python main.py --mode realtime
```

启动后日志中会显示：

```
OSD数据源模式: auto
HTTP OSD客户端已创建 (base_url=http://10.5.52.129:10006)
MQTT客户端已创建
步骤1: 连接OSD数据源 (auto模式: HTTP优先)
正在测试HTTP OSD接口: http://10.5.52.129:10006/satxspace-airspace/ai/getDrone?devSn=...
HTTP OSD接口连接成功，收到 15 个字段
HTTP OSD接口连接成功 (主数据源)
HTTP OSD轮询线程已启动 (间隔 0.1s)
```

### 6.3 运行统计示例

```
--- 实时统计 ---
处理速度: 8.50 FPS | 主数据源: http
位姿来源: HTTP 100.0%
视频流: 已接收850帧, 缓冲区25, 重连0次
HTTP OSD: 成功850次, 错误0次, 延迟15.3ms
MQTT: 已接收0条消息, 缓冲区0, 有位姿数据: False
```

### 6.4 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `HTTP OSD接口连接失败` | 服务地址不通或SN错误 | 检查网络连通性和设备SN |
| `HTTP OSD: GPS坐标为0` | 无人机未锁定GPS | 等待GPS锁定后重试 |
| `HTTP OSD连续无数据，已自动切换到MQTT` | HTTP服务临时中断 | auto模式下自动降级，无需手动干预 |
| `GPS质量字段均缺失，按MEDIUM处理` | HTTP不返回gpsLevel | 正常现象，不影响坐标转换 |

---

## 7. 配置参数参考

### http_osd 配置段

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `base_url` | string | - | HTTP服务根地址 |
| `api_path` | string | `/satxspace-airspace/ai/getDrone` | 接口路径 |
| `dev_sn` | string | - | 设备序列号（必填） |
| `poll_interval` | float | `0.1` | 轮询间隔（秒），建议0.1~0.5 |
| `request_timeout` | float | `2` | 请求超时（秒） |
| `max_retry` | int | `3` | 连续失败此次数后标记不可用 |
| `pose_buffer_size` | int | `100` | 位姿缓冲区容量 |

### 轮询间隔建议

| 场景 | 建议值 | 说明 |
|------|--------|------|
| 高精度巡检 | `0.1` (10Hz) | 与MQTT推送频率一致 |
| 常规巡检 | `0.2` (5Hz) | 降低接口压力 |
| 低速飞行/悬停 | `0.5` (2Hz) | 位姿变化小，无需高频 |
