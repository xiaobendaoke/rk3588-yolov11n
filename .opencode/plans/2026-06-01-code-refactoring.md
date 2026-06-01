# Desk Safety 代码质量改进与结构重组实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复所有已知bug，重组代码结构，提升代码质量和可维护性。

**Architecture:** 分阶段实施：先修复严重/中等bug，再重组文件结构，最后清理死代码和提取模板。每阶段独立可测试。

**Tech Stack:** Python 3.10+, C++ (native/rknn_infer.cpp), FastAPI, SQLite, OpenCV

---

## 第一阶段：严重Bug修复

### Task 1: 修复 C++ 层 NUM_CLASSES 硬编码问题

**Files:**
- Modify: `native/rknn_infer.h:17`
- Modify: `native/rknn_infer.cpp:34-36,241`
- Modify: `app/infer/native_engine.py:80-90`

- [ ] **Step 1: 修改 C 头文件，移除 NUM_CLASSES 硬编码**

修改 `native/rknn_infer.h`，删除第17行的 `#define NUM_CLASSES 80`，并在 `rknn_engine_create` 函数签名中添加 `num_classes` 参数。

```c
// 修改后的 rknn_engine_create 签名
void* rknn_engine_create(const char* model_path, int input_size,
                          float conf_threshold, float nms_threshold,
                          int num_classes);
```

- [ ] **Step 2: 修改 C++ 实现，使用动态 num_classes**

修改 `native/rknn_infer.cpp`：

1. 在 `RknnEngine` 结构体中添加 `int num_classes` 字段：
```cpp
struct RknnEngine {
    int input_size;
    int num_classes;  // 新增
    float conf_threshold;
    float nms_threshold;
    std::vector<Worker> workers;
    std::atomic<int> next_idx{0};
};
```

2. 修改 `rknn_engine_create` 函数实现，接收并存储 `num_classes`：
```cpp
void* rknn_engine_create(const char* model_path, int input_size,
                          float conf_threshold, float nms_threshold,
                          int num_classes) {
    RknnEngine* eng = new RknnEngine();
    eng->input_size = input_size;
    eng->num_classes = num_classes;  // 新增
    eng->conf_threshold = conf_threshold;
    eng->nms_threshold = nms_threshold;
    // ... 其余代码不变
}
```

3. 修改第241行的循环，使用 `eng->num_classes` 替代 `NUM_CLASSES`：
```cpp
for (int c = 0; c < eng->num_classes; c++) {
```

- [ ] **Step 3: 修改 Python ctypes 绑定，传递 num_classes**

修改 `app/infer/native_engine.py`：

1. 在 `NativeInferenceEngine.__init__` 中添加 `num_classes` 参数：
```python
def __init__(
    self,
    model_path: str,
    class_names: List[str],
    conf_threshold: float,
    nms_threshold: float,
    input_size: int,
    num_classes: int = 80,  # 新增
) -> None:
    self.num_classes = num_classes
    # ... 其余初始化代码
```

2. 修改 `_init_library` 方法中 `rknn_engine_create` 的调用：
```python
self._lib.rknn_engine_create.restype = ctypes.c_void_p
self._lib.rknn_engine_create.argtypes = [
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_float,
    ctypes.c_float,
    ctypes.c_int,  # 新增 num_classes 参数
]
self._engine = self._lib.rknn_engine_create(
    self.model_path.encode(),
    self.input_size,
    self.conf_threshold,
    self.nms_threshold,
    self.num_classes,  # 传递类别数
)
```

- [ ] **Step 4: 修改 main.py，传递 class_names 长度**

修改 `app/main.py` 第363-369行的 `NativeInferenceEngine` 实例化：

```python
if settings.use_native:
    infer = NativeInferenceEngine(
        settings.model_path,
        settings.class_names,
        settings.conf_threshold,
        settings.nms_threshold,
        settings.input_size,
        num_classes=len(settings.class_names),  # 新增
    )
```

- [ ] **Step 5: 重新编译 native 库并测试**

```bash
cd /home/nidie/文档/desk-safety/native
./build.sh
```

- [ ] **Step 6: Commit**

```bash
git add native/rknn_infer.h native/rknn_infer.cpp app/infer/native_engine.py app/main.py
git commit -m "fix: remove hardcoded NUM_CLASSES, pass num_classes dynamically"
```

---

### Task 2: 修复 scripts/fix_cutter_labels.py 替换逻辑错误

**Files:**
- Modify: `scripts/fix_cutter_labels.py:64`

- [ ] **Step 1: 修复 replace 调用，移除限制参数**

修改 `scripts/fix_cutter_labels.py` 第64行：

```python
# 修改前
content = content.replace(f'{CUTTER_CLASS_CUSTOM} ', f'{CUTTER_CLASS_COCO} ', 1)

# 修改后
content = content.replace(f'{CUTTER_CLASS_CUSTOM} ', f'{CUTTER_CLASS_COCO} ')
```

- [ ] **Step 2: Commit**

```bash
git add scripts/fix_cutter_labels.py
git commit -m "fix: remove replace count limit to fix all cutter instances"
```

---

## 第二阶段：中等Bug修复

### Task 3: 修复 main.py 中缺失的 numpy 导入

**Files:**
- Modify: `app/main.py:1`

- [ ] **Step 1: 在文件顶部添加 numpy 导入**

在 `app/main.py` 第1行 `from __future__ import annotations` 后添加：

```python
from __future__ import annotations

import argparse
import logging
import threading
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import cv2
import numpy as np  # 新增
import uvicorn
```

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "fix: add missing numpy import in main.py"
```

---

### Task 4: 移除 native_engine.py 中未使用的 threading 导入

**Files:**
- Modify: `app/infer/native_engine.py:7`

- [ ] **Step 1: 删除未使用的 threading 导入**

删除 `app/infer/native_engine.py` 第7行：

```python
# 删除这一行
import threading
```

- [ ] **Step 2: Commit**

```bash
git add app/infer/native_engine.py
git commit -m "fix: remove unused threading import from native_engine.py"
```

---

### Task 5: 修复多个脚本缺少 crop_left 参数

**Files:**
- Modify: `scripts/profile_infer.py:17`
- Modify: `scripts/debug_yolo11_output.py:15`
- Modify: `scripts/sample_infer_100.py:51`

- [ ] **Step 1: 修改 profile_infer.py**

在 `scripts/profile_infer.py` 中找到 `CameraCapture` 实例化，添加第4个参数：

```python
# 修改前
cap = CameraCapture(device, width, height)

# 修改后
cap = CameraCapture(device, width, height, cfg.camera_crop_left)
```

- [ ] **Step 2: 修改 debug_yolo11_output.py**

在 `scripts/debug_yolo11_output.py` 中找到 `CameraCapture` 实例化，添加第4个参数：

```python
# 修改前
cap = CameraCapture(device, width, height)

# 修改后
cap = CameraCapture(device, width, height, cfg.camera_crop_left)
```

- [ ] **Step 3: 修改 sample_infer_100.py**

在 `scripts/sample_infer_100.py` 中找到 `CameraCapture` 实例化，添加第4个参数：

```python
# 修改前
cap = CameraCapture(device, width, height)

# 修改后
cap = CameraCapture(device, width, height, cfg.camera_crop_left)
```

- [ ] **Step 4: Commit**

```bash
git add scripts/profile_infer.py scripts/debug_yolo11_output.py scripts/sample_infer_100.py
git commit -m "fix: add missing crop_left parameter to CameraCapture in scripts"
```

---

### Task 6: 修复 main.py 中重复的 NativeInferenceEngine 导入

**Files:**
- Modify: `app/main.py:205`

- [ ] **Step 1: 删除函数体内的重复导入**

删除 `app/main.py` 第205行：

```python
# 删除这一行
from app.infer.native_engine import NativeInferenceEngine
```

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "fix: remove redundant NativeInferenceEngine import in _infer_loop_native"
```

---

### Task 7: 修复 events.py 中的时区不一致问题

**Files:**
- Modify: `app/storage/events.py:181`

- [ ] **Step 1: 修改 _to_iso 函数使用 UTC 时区**

修改 `app/storage/events.py` 第181行：

```python
# 修改前
def _to_iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000.0).isoformat(timespec="seconds")

# 修改后
def _to_iso(ts_ms: int) -> str:
    from datetime import timezone
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).isoformat(timespec="seconds")
```

- [ ] **Step 2: Commit**

```bash
git add app/storage/events.py
git commit -m "fix: use UTC timezone in _to_iso for consistency with SQLite"
```

---

## 第三阶段：文件结构重组

### Task 8: 移动 scripts/ 下的测试脚本到 tests/

**Files:**
- Move: `scripts/test_async.py` → `tests/benchmark_async.py`
- Move: `scripts/test_native.py` → `tests/benchmark_native.py`
- Move: `scripts/test_pipeline.py` → `tests/benchmark_pipeline.py`
- Rename: `scripts/test_multi_thread.py` → `tests/benchmark_multi_process.py`

- [ ] **Step 1: 移动并重命名测试脚本**

```bash
cd /home/nidie/文档/desk-safety
mv scripts/test_async.py tests/benchmark_async.py
mv scripts/test_native.py tests/benchmark_native.py
mv scripts/test_pipeline.py tests/benchmark_pipeline.py
mv scripts/test_multi_thread.py tests/benchmark_multi_process.py
```

- [ ] **Step 2: 更新脚本中的导入路径（如有必要）**

检查每个脚本中的导入，确保路径正确。如果脚本使用相对导入，需要调整。

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor: move test scripts from scripts/ to tests/ with benchmark_ prefix"
```

---

### Task 9: 合并重复的 polygon_to_bbox 脚本

**Files:**
- Delete: `scripts/fix_cutter_labels.py`
- Delete: `scripts/fix_cutter_labels_v2.py`
- Keep: `scripts/fix_polygon_labels.py`

- [ ] **Step 1: 检查三个脚本的差异**

读取三个脚本，确认功能重叠程度。

- [ ] **Step 2: 合并功能到 fix_polygon_labels.py**

将 `fix_cutter_labels.py` 和 `fix_cutter_labels_v2.py` 中的独特功能合并到 `fix_polygon_labels.py`。

- [ ] **Step 3: 删除旧脚本**

```bash
cd /home/nidie/文档/desk-safety
rm scripts/fix_cutter_labels.py
rm scripts/fix_cutter_labels_v2.py
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: merge duplicate polygon_to_bbox scripts into fix_polygon_labels.py"
```

---

### Task 10: 删除死代码 multi_thread.py

**Files:**
- Delete: `app/infer/multi_thread.py`

- [ ] **Step 1: 确认 multi_thread.py 未被使用**

```bash
cd /home/nidie/文档/desk-safety
grep -r "multi_thread" --include="*.py" .
grep -r "MultiThreadEngine" --include="*.py" .
```

确认无引用后删除。

- [ ] **Step 2: 删除文件**

```bash
rm app/infer/multi_thread.py
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor: remove unused multi_thread.py (dead code)"
```

---

### Task 11: 提取 Web 模板到独立文件

**Files:**
- Create: `app/web/templates/index.html`
- Modify: `app/web/server.py:58-392`

- [ ] **Step 1: 创建 templates 目录**

```bash
mkdir -p /home/nidie/文档/desk-safety/app/web/templates
```

- [ ] **Step 2: 提取 HTML 到独立文件**

从 `app/web/server.py` 第58-392行提取 HTML 内容，保存到 `app/web/templates/index.html`。

- [ ] **Step 3: 修改 server.py 使用 FileResponse**

修改 `app/web/server.py` 中的根路由：

```python
from fastapi.responses import FileResponse

@app.get("/")
async def root():
    html_path = Path(__file__).parent / "templates" / "index.html"
    return FileResponse(html_path, media_type="text/html")
```

- [ ] **Step 4: Commit**

```bash
git add app/web/templates/index.html app/web/server.py
git commit -m "refactor: extract inline HTML to templates/index.html"
```

---

### Task 12: 统一配置文件字段

**Files:**
- Modify: `configs/config.example.yaml`

- [ ] **Step 1: 在 config.example.yaml 中添加缺失字段**

在 `configs/config.example.yaml` 末尾添加：

```yaml
# 推理引擎配置
npu_threads: 1
use_native: false
```

- [ ] **Step 2: Commit**

```bash
git add configs/config.example.yaml
git commit -m "fix: add missing npu_threads and use_native fields to example config"
```

---

### Task 13: 修复 .gitignore 中 systemd/ 的问题

**Files:**
- Modify: `.gitignore:20`

- [ ] **Step 1: 从 .gitignore 中移除 systemd/ 条目**

删除 `.gitignore` 第20行：

```gitignore
# 删除这一行
systemd/
```

- [ ] **Step 2: 确保 systemd 文件被追踪**

```bash
cd /home/nidie/文档/desk-safety
git add -f systemd/desk-safety.service
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore systemd/
git commit -m "fix: remove systemd/ from .gitignore to track service files"
```

---

## 第四阶段：代码清理与测试改进

### Task 14: 清理 web/server.py 中未使用的 latest_frame 字段

**Files:**
- Modify: `app/web/server.py:29`

- [x] **Step 1: 删除未使用的 latest_frame 字段**

在 `app/web/server.py` 的 `AppState` 类中删除：

```python
# 删除这一行
self.latest_frame = None
```

- [x] **Step 2: Commit**

```bash
git add app/web/server.py
git commit -m "refactor: remove unused latest_frame field from AppState"
```

---

### Task 15: 改进 test_yolo11_decode.py 使用 assert

**Files:**
- Modify: `tests/test_yolo11_decode.py`

- [ ] **Step 1: 将 print 语句替换为 assert**

读取 `tests/test_yolo11_decode.py`，将所有 `print()` 输出替换为 `assert` 断言。

例如：

```python
# 修改前
print(f"Result: {result}")

# 修改后
assert result is not None, "decode should return a result"
assert len(result) > 0, "decode should return non-empty result"
```

- [ ] **Step 2: 运行测试验证**

```bash
cd /home/nidie/文档/desk-safety
python -m pytest tests/test_yolo11_decode.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_yolo11_decode.py
git commit -m "test: convert print statements to assert in test_yolo11_decode.py"
```

---

## 第五阶段：最终验证

### Task 16: 运行所有测试确保无回归

**Files:**
- All modified files

- [ ] **Step 1: 运行完整测试套件**

```bash
cd /home/nidie/文档/desk-safety
python -m pytest tests/ -v
```

- [ ] **Step 2: 检查代码风格**

```bash
python -m flake8 app/ --max-line-length=120
python -m mypy app/ --ignore-missing-imports
```

- [ ] **Step 3: 验证 native 库编译**

```bash
cd native
./build.sh
```

- [ ] **Step 4: 最终 Commit（如有修复）**

```bash
git add -A
git commit -m "chore: final cleanup and verification"
```

---

## 执行选项

**Plan complete and saved to `.opencode/plans/2026-06-01-code-refactoring.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - 我为每个Task派遣一个独立的子代理执行，任务间进行审查，快速迭代

**2. Inline Execution** - 在当前会话中使用 executing-plans 批量执行，设置检查点进行审查

**选择哪种方式？**
