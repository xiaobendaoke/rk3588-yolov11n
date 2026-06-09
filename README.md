# rk3588-yolov11n

> 基于 RK3588 NPU + YOLO11n 的实时桌面安全监控系统，平均推理帧率 **65 FPS**

---

## 项目简介

rk3588-yolov11n 是一个运行在 RK3588 开发板上的实时桌面安全监控系统。通过 USB 摄像头采集画面，利用 RK3588 的 NPU 硬件加速进行 YOLO11n 目标检测，并根据安全规则实时判断桌面是否存在风险行为，通过 Web 界面提供实时监控和事件记录。

**核心数据：**

| 指标 | 数据 |
|------|------|
| 平均推理帧率 | **65 FPS** |
| 相比Python原生 | **3.75x 提升** |
| NPU 利用率 | 100% |
| 检测类别 | 16 类桌面物品 |
| 安全规则 | 3 条 |

---

## 功能特性

### 实时目标检测

- 基于 YOLO11n 模型，支持 16 类桌面物品检测
- 利用 RK3588 NPU 硬件加速，FP16 推理
- 三核心并行推理，充分利用硬件性能

### 安全规则引擎

系统内置 3 条安全规则，实时评估桌面安全状态：

1. **液体靠近电子设备**：检测杯子/瓶子是否靠近手机、键盘、鼠标等电子设备
2. **尖锐工具误放**：检测剪刀是否出现在配置的危险区域内
3. **桌面物品拥挤**：检测桌面物品是否过于密集

### Web 实时监控

- 浏览器访问实时视频流
- 显示检测框和风险标签
- 实时显示 FPS、CPU/GPU/NPU 负载、温度等系统状态
- 风险事件列表与快照查看

### 事件记录

- 风险事件自动截图保存
- SQLite 数据库持久化存储
- 支持按风险类型查询和统计

### 开机自启

- systemd 服务管理
- 开机自动启动
- 异常自动重启

---

## 硬件要求

| 组件 | 要求 |
|------|------|
| 开发板 | RK3588 系列（如 ELF2、Orange Pi 5 Plus 等） |
| 内存 | 4GB+ |
| 摄像头 | USB 摄像头（支持 MJPG 格式） |
| 存储 | 8GB+ 可用空间 |

---

## 性能数据

### 推理帧率对比

| 模式 | FPS | 提升倍数 | 说明 |
|------|-----|----------|------|
| Python RKNN | ~16 | 1x (基准) | Python 后处理 |
| C++ Native | ~30 | 1.8x | C++ 后处理 |
| C++ Native + 流水线 | **~65** | **3.75x** | C++ 后处理 + 双缓冲流水线 |

### 系统资源占用

| 资源 | 占用率 |
|------|--------|
| CPU | ~32% |
| GPU | ~20% |
| NPU | 100% |
| 内存 | ~46% |
| CPU 温度 | ~84°C |

---

## 系统架构

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│  USB Camera │───>│  双缓冲流水线  │───>│ RKNN NPU 推理 │───>│  规则引擎    │
│  /dev/video │    │  (捕获并行)   │    │  (3核心并行)  │    │  (风险评估)  │
└─────────────┘    └──────────────┘    └──────────────┘    └──────┬──────┘
                                                                  │
                                                                  v
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│  Web 浏览器  │<───│  FastAPI 服务 │<───│  JPEG 编码   │<───│  标注绘制    │
│  实时监控    │    │  状态API     │    │  (OpenCV)    │    │  (检测框)    │
└─────────────┘    └──────────────┘    └──────────────┘    └─────────────┘
```

### 核心模块

| 模块 | 功能 | 文件 |
|------|------|------|
| 摄像头采集 | V4L2/OpenCV 读取摄像头帧 | `app/capture/` |
| 推理引擎 | RKNN 模型推理 + C++ 后处理 | `app/infer/`, `native/` |
| 规则引擎 | 安全规则评估 | `app/rules/` |
| 流水线 | 双缓冲并行处理 | `app/pipeline/` |
| Web 服务 | 实时监控与API | `app/web/` |
| 事件存储 | SQLite 持久化 | `app/storage/` |

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/xiaobendaoke/rk3588-yolov11n.git
cd rk3588-yolov11n
```

### 2. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置

复制配置文件并根据设备修改：

```bash
cp configs/config.example.yaml configs/config.yaml
```

主要配置项：

```yaml
# 摄像头设备（通过 v4l2-ctl --list-devices 查看）
camera_device: /dev/video21

# 模型文件路径
model_path: ./models/yolo11n_desk_v4.rknn

# 检测类别（16类桌面物品）
class_names:
  - bottle
  - cell phone
  - cup
  - cutter
  - fork
  - keyboard
  - knife
  - mouse
  - remote
  - scissors
  - spoon
  - laptop
  - monitor
  - tablet
  - book
  - pen

# 优化配置
use_native: true        # 使用C++推理引擎
pipeline_enabled: true  # 启用双缓冲流水线
```

### 4. 启动服务

```bash
python -m app.main --config ./configs/config.yaml
```

### 5. 访问监控界面

浏览器打开：`http://<板子IP>:8080`

---

## 部署到开发板

### 方式一：systemd 服务（推荐）

```bash
# 1. 同步代码到板子
sudo mkdir -p /opt/desk-safety
sudo rsync -a --delete ./ /opt/desk-safety/

# 2. 安装 systemd 服务
sudo cp ./systemd/desk-safety.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now desk-safety.service

# 3. 检查服务状态
sudo systemctl status desk-safety.service
```

### 方式二：使用部署脚本

```bash
chmod +x deploy_optimized.sh
./deploy_optimized.sh
```

---

## 项目结构

```
rk3588-yolov11n/
├── app/                          # Python 应用代码
│   ├── capture/                  # 摄像头采集
│   │   ├── camera.py             # OpenCV 摄像头
│   │   └── v4l2_camera.py        # V4L2 摄像头（MPP加速）
│   ├── infer/                    # 推理引擎
│   │   ├── engine.py             # Python RKNN 引擎
│   │   ├── native_engine.py      # C++ 引擎绑定
│   │   └── multi_process.py      # 多进程引擎
│   ├── pipeline/                 # 流水线
│   │   └── buffer.py             # 双缓冲实现
│   ├── rules/                    # 规则引擎
│   │   └── engine.py             # 安全规则评估
│   ├── storage/                  # 事件存储
│   │   └── events.py             # SQLite 存储
│   ├── web/                      # Web 服务
│   │   ├── server.py             # FastAPI 服务
│   │   └── templates/            # HTML 模板
│   ├── config.py                 # 配置加载
│   ├── main.py                   # 主入口
│   └── types.py                  # 类型定义
├── configs/                      # 配置文件
│   ├── config.example.yaml       # 示例配置
│   ├── config.yaml               # 运行配置
│   └── config_yolo11s.yaml       # YOLO11s 配置
├── native/                       # C++ 推理库
│   ├── rknn_infer.cpp            # RKNN 推理 + YOLO11 后处理
│   ├── rknn_infer.h              # 推理接口
│   ├── mpp_jpeg_decoder.cpp      # MPP 硬件 JPEG 解码
│   ├── mpp_jpeg_decoder.h        # 解码接口
│   ├── v4l2_camera.cpp           # V4L2 摄像头封装
│   ├── v4l2_camera.h             # 摄像头接口
│   ├── CMakeLists.txt            # CMake 构建
│   ├── build.sh                  # CMake 编译脚本
│   └── build_gpp.sh              # g++ 直接编译脚本
├── models/                       # 模型文件
│   ├── yolo11n_desk_v4.rknn      # YOLO11n RKNN 模型
│   ├── yolo11s.rknn              # YOLO11s RKNN 模型
│   └── yolo11m.rknn              # YOLO11m RKNN 模型
├── scripts/                      # 工具脚本
│   ├── convert_yolo11.py         # 模型转换
│   ├── profile_optimized.py      # 性能分析
│   └── sample_infer_100.py       # 采样推理测试
├── tests/                        # 测试代码
│   └── test_yolo11_consistency.py # 一致性测试
├── systemd/                      # systemd 服务
│   └── desk-safety.service       # 服务配置
├── deploy_optimized.sh           # 部署脚本
├── requirements.txt              # Python 依赖
└── README.md                     # 项目说明
```

---

## 优化技术

### 1. C++ YOLO11 后处理

将 Python 后处理逻辑完整移植到 C++，包括：

- DFL（Distribution Focal Loss）解码
- 网格坐标生成
- 边界框坐标转换
- NMS（非极大值抑制）

**效果**：后处理耗时从 10-18ms 降至 1.3-2.5ms

### 2. 双缓冲流水线

使用双缓冲实现摄像头捕获和推理的并行执行：

- 摄像头线程持续读取帧到写入缓冲区
- 推理线程从读取缓冲区处理最新帧
- 编码线程处理推理结果并更新 Web 状态

**效果**：整体 FPS 从 30 提升至 65

### 3. NPU 三核心并行

RK3588 内置 3 个 NPU 核心，通过核心掩码绑定实现并行推理：

```c++
// 设置 NPU 核心掩码 (RK3588: core0=1, core1=2, core2=4)
int core_mask = 1 << core_id;
rknn_set_core_mask(ctx, (rknn_core_mask)core_mask);
```

**效果**：推理吞吐量提升 3 倍

### 4. MPP 硬件 JPEG 解码（待启用）

集成 Rockchip MPP 进行硬件 JPEG 解码，替代软件解码：

- V4L2 MMAP 零拷贝获取 MJPG 数据
- MPP 硬件解码 MJPG → NV12
- 减少内核到用户空间的数据拷贝

**预期效果**：摄像头读取延迟从 5-10ms 降至 1-2ms

---

## 检测类别

系统支持 16 类桌面物品检测：

| 类别 | 类别 | 类别 | 类别 |
|------|------|------|------|
| bottle | cell phone | cup | cutter |
| fork | keyboard | knife | mouse |
| remote | scissors | spoon | laptop |
| monitor | tablet | book | pen |

---

## 配置参考

### 配置文件说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `camera_device` | string | `/dev/video21` | 摄像头设备路径 |
| `camera_width` | int | `1280` | 摄像头宽度 |
| `camera_height` | int | `480` | 摄像头高度 |
| `camera_crop_left` | bool | `true` | 是否裁剪左半帧（双目摄像头） |
| `input_size` | int | `640` | 模型输入尺寸 |
| `model_path` | string | - | RKNN 模型文件路径 |
| `class_names` | list | - | 检测类别列表 |
| `conf_threshold` | float | `0.15` | 置信度阈值 |
| `nms_threshold` | float | `0.45` | NMS 阈值 |
| `risk_distance_px` | int | `120` | 液体-设备接近风险距离（像素） |
| `risk_hold_frames` | int | `5` | 风险确认所需连续帧数 |
| `event_cooldown_sec` | int | `8` | 同类事件最小间隔（秒） |
| `use_native` | bool | `true` | 使用 C++ 推理引擎 |
| `pipeline_enabled` | bool | `true` | 启用双缓冲流水线 |
| `web_host` | string | `0.0.0.0` | Web 服务绑定地址 |
| `web_port` | int | `8080` | Web 服务端口 |

---

## 开发指南

### 模型训练

使用 Ultralytics YOLO11 训练自定义模型：

```bash
# 安装 ultralytics
pip install ultralytics

# 训练模型
yolo detect train \
    model=yolo11n.pt \
    data=data.yaml \
    epochs=200 \
    imgsz=640 \
    device=0
```

### 模型转换

将 ONNX 模型转换为 RKNN 格式：

```bash
# 使用 rknn-toolkit2 转换
python scripts/convert_yolo11.py
```

### 编译 C++ 推理库

在 RK3588 板子上编译：

```bash
cd native

# 方式一：使用 CMake（需要安装 cmake）
./build.sh

# 方式二：直接使用 g++
./build_gpp.sh

# 安装库
cp build/librknn_infer.so .
```

### 性能测试

```bash
# 性能分析
python scripts/profile_optimized.py

# 采样推理测试
python scripts/sample_infer_100.py --frames 100

# 一致性测试
python tests/test_yolo11_consistency.py
```

---

## API 接口

### 获取系统状态

```
GET /api/status
```

响应示例：

```json
{
    "fps": 65.2,
    "queue_size": 0,
    "last_event_time": "2026-04-03T03:00:00",
    "cpu_percent": 32.7,
    "gpu_load": 20.0,
    "npu_load": 100.0,
    "mem_percent": 46.0,
    "cpu_temp": 84.1,
    "gpu_temp": 84.1,
    "detection_count": 1
}
```

### 获取事件列表

```
GET /api/events?page=1&size=20&risk_type=liquid_near_electronics
```

### 获取事件统计

```
GET /api/events/stats
```

### 获取事件详情

```
GET /api/events/{event_id}
```

### 实时视频流

```
GET /live.mjpg
```

### 获取当前帧

```
GET /frame.jpg
```

---

## 常见问题

### 摄像头无法打开

```bash
# 检查摄像头设备
v4l2-ctl --list-devices

# 检查摄像头是否被占用
fuser /dev/video21

# 杀死占用进程
sudo kill -9 $(fuser /dev/video21 2>/dev/null)
```

### NPU 未启用

```bash
# 检查 NPU 驱动
cat /sys/class/devfreq/fdab0000.npu/cur_freq

# 检查 RKNN 库
python3 -c "from rknnlite.api import RKNNLite; print('OK')"
```

### FPS 过低

1. 确认 `use_native: true` 已启用
2. 确认 `pipeline_enabled: true` 已启用
3. 检查 NPU 是否正常工作：`cat /sys/class/devfreq/fdab0000.npu/load`
4. 检查 CPU/GPU 温度是否过高导致降频

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。
