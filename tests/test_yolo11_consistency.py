#!/usr/bin/env python3
"""验证C++后处理与Python后处理输出一致。"""

import sys
import time
import cv2
import numpy as np
from pathlib import Path

sys.path.insert(0, "/opt/desk-safety")
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import load_settings
from app.infer.engine import InferenceEngine
from app.infer.native_engine import NativeInferenceEngine


def load_test_image():
    """加载测试图片。"""
    # 尝试加载测试图片
    candidates = [
        "test.jpg",
        "test.png",
        "data/test.jpg",
        "data/test.png",
    ]
    
    for path in candidates:
        if Path(path).exists():
            img = cv2.imread(path)
            if img is not None:
                return img
    
    # 如果没有测试图片，创建一个合成图片
    print("WARNING: No test image found, creating synthetic image")
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # 画一些物体轮廓
    cv2.rectangle(img, (100, 100), (200, 200), (0, 255, 0), 2)
    cv2.rectangle(img, (300, 150), (400, 250), (0, 0, 255), 2)
    cv2.circle(img, (500, 300), 50, (255, 0, 0), 2)
    
    return img


def compare_detections(py_dets, cpp_dets, tolerance=0.05):
    """比较两组检测结果。
    
    Args:
        py_dets: Python检测结果
        cpp_dets: C++检测结果
        tolerance: 允许的误差范围
        
    Returns:
        (是否一致, 差异描述)
    """
    if len(py_dets) != len(cpp_dets):
        return False, f"Detection count mismatch: {len(py_dets)} vs {len(cpp_dets)}"
    
    # 按置信度排序
    py_sorted = sorted(py_dets, key=lambda d: d.conf, reverse=True)
    cpp_sorted = sorted(cpp_dets, key=lambda d: d.conf, reverse=True)
    
    diffs = []
    for i, (py_det, cpp_det) in enumerate(zip(py_sorted, cpp_sorted)):
        # 检查类别
        if py_det.class_name != cpp_det.class_name:
            diffs.append(f"  [{i}] Class mismatch: {py_det.class_name} vs {cpp_det.class_name}")
        
        # 检查置信度
        conf_diff = abs(py_det.conf - cpp_det.conf)
        if conf_diff > tolerance:
            diffs.append(f"  [{i}] Confidence mismatch: {py_det.conf:.4f} vs {cpp_det.conf:.4f} (diff={conf_diff:.4f})")
        
        # 检查边界框
        box_diffs = []
        for j, (p, c) in enumerate(zip(py_det.bbox_xyxy, cpp_det.bbox_xyxy)):
            if abs(p - c) > 5:  # 允许5像素误差
                box_diffs.append(f"{p} vs {c}")
        
        if box_diffs:
            diffs.append(f"  [{i}] BBox mismatch: {', '.join(box_diffs)}")
    
    if diffs:
        return False, "\n".join(diffs)
    return True, "All detections match"


def main():
    """主函数。"""
    print("=" * 60)
    print("YOLO11 Consistency Test")
    print("=" * 60)
    
    # 加载配置
    config_path = "./configs/config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    print(f"\nLoading config: {config_path}")
    cfg = load_settings(config_path)
    
    # 创建Python引擎
    print("\nInitializing Python engine...")
    py_engine = InferenceEngine(
        cfg.model_path,
        cfg.class_names,
        cfg.conf_threshold,
        cfg.nms_threshold,
        cfg.input_size,
    )
    py_engine.open()
    
    # 创建C++引擎（使用YOLO11接口）
    print("Initializing C++ engine (YOLO11)...")
    cpp_engine = NativeInferenceEngine(
        cfg.model_path,
        cfg.class_names,
        cfg.conf_threshold,
        cfg.nms_threshold,
        cfg.input_size,
        use_yolo11=True,
    )
    cpp_engine.open()
    
    # 加载测试图片
    print("\nLoading test image...")
    test_img = load_test_image()
    if test_img is None:
        print("ERROR: Failed to load test image")
        return 1
    
    print(f"Image shape: {test_img.shape}")
    
    # Python推理
    print("\nRunning Python inference...")
    t0 = time.perf_counter()
    py_dets, py_frame = py_engine.infer(test_img)
    t1 = time.perf_counter()
    py_time = (t1 - t0) * 1000
    print(f"  Time: {py_time:.1f} ms")
    print(f"  Detections: {len(py_dets)}")
    
    # C++推理
    print("\nRunning C++ inference (YOLO11)...")
    t0 = time.perf_counter()
    cpp_dets, cpp_frame = cpp_engine.infer(test_img)
    t1 = time.perf_counter()
    cpp_time = (t1 - t0) * 1000
    print(f"  Time: {cpp_time:.1f} ms")
    print(f"  Detections: {len(cpp_dets)}")
    
    # 比较结果
    print("\n" + "=" * 60)
    print("Comparison Results:")
    print("=" * 60)
    
    # 打印Python检测结果
    print("\nPython detections:")
    for i, det in enumerate(py_dets):
        print(f"  [{i}] {det.class_name}: conf={det.conf:.4f}, box={det.bbox_xyxy}")
    
    # 打印C++检测结果
    print("\nC++ detections:")
    for i, det in enumerate(cpp_dets):
        print(f"  [{i}] {det.class_name}: conf={det.conf:.4f}, box={det.bbox_xyxy}")
    
    # 比较
    consistent, diff_msg = compare_detections(py_dets, cpp_dets)
    
    print("\n" + "-" * 60)
    if consistent:
        print("✓ CONSISTENT: Python and C++ outputs match!")
    else:
        print("✗ INCONSISTENT: Python and C++ outputs differ!")
        print(f"\nDifferences:\n{diff_msg}")
    
    # 性能比较
    print("\n" + "-" * 60)
    print("Performance:")
    print(f"  Python: {py_time:.1f} ms")
    print(f"  C++:    {cpp_time:.1f} ms")
    if py_time > 0:
        speedup = py_time / cpp_time
        print(f"  Speedup: {speedup:.2f}x")
    
    # 清理
    py_engine.close()
    cpp_engine.close()
    
    return 0 if consistent else 1


if __name__ == "__main__":
    sys.exit(main())
