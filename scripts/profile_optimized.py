#!/usr/bin/env python3
"""性能分析脚本，用于测试优化效果。"""

import sys
import time
import cv2
import numpy as np
from pathlib import Path

sys.path.insert(0, "/opt/desk-safety")
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import load_settings
from app.capture.camera import CameraCapture
from app.capture.v4l2_camera import NativeV4l2Camera
from app.infer.engine import InferenceEngine
from app.infer.native_engine import NativeInferenceEngine


def profile_camera(camera, n_frames=30):
    """分析摄像头性能。"""
    print(f"\n{'='*60}")
    print("Camera Performance Profile")
    print(f"{'='*60}")
    
    # 预热
    for _ in range(5):
        camera.read()
    
    # 测试
    times = []
    for i in range(n_frames):
        t0 = time.perf_counter()
        frame = camera.read()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
        
        if frame is not None and i == 0:
            print(f"Frame shape: {frame.shape}")
    
    avg_time = np.mean(times)
    std_time = np.std(times)
    fps = 1000 / avg_time if avg_time > 0 else 0
    
    print(f"Frames: {n_frames}")
    print(f"Average: {avg_time:.1f} ms (±{std_time:.1f})")
    print(f"Min: {min(times):.1f} ms")
    print(f"Max: {max(times):.1f} ms")
    print(f"FPS: {fps:.1f}")
    
    return avg_time, fps


def profile_inference(infer, camera, n_frames=30):
    """分析推理性能。"""
    print(f"\n{'='*60}")
    print("Inference Performance Profile")
    print(f"{'='*60}")
    
    # 预热
    for _ in range(5):
        frame = camera.read()
        if frame is not None:
            infer.infer(frame)
    
    # 测试
    total_times = []
    infer_times = []
    dets_counts = []
    
    for i in range(n_frames):
        frame = camera.read()
        if frame is None:
            continue
        
        t0 = time.perf_counter()
        dets, _ = infer.infer(frame)
        t1 = time.perf_counter()
        
        infer_time = (t1 - t0) * 1000
        infer_times.append(infer_time)
        dets_counts.append(len(dets))
    
    avg_infer = np.mean(infer_times)
    std_infer = np.std(infer_times)
    fps = 1000 / avg_infer if avg_infer > 0 else 0
    avg_dets = np.mean(dets_counts)
    
    print(f"Frames: {n_frames}")
    print(f"Average inference: {avg_infer:.1f} ms (±{std_infer:.1f})")
    print(f"Min: {min(infer_times):.1f} ms")
    print(f"Max: {max(infer_times):.1f} ms")
    print(f"FPS: {fps:.1f}")
    print(f"Average detections: {avg_dets:.1f}")
    
    return avg_infer, fps


def profile_pipeline(camera, infer, n_frames=30):
    """分析流水线性能。"""
    print(f"\n{'='*60}")
    print("Pipeline Performance Profile")
    print(f"{'='*60}")
    
    from app.pipeline.buffer import DoubleBuffer
    
    # 初始化双缓冲
    frame = camera.read()
    if frame is None:
        print("ERROR: No frame from camera")
        return
    
    buffer = DoubleBuffer(frame.shape)
    results = []
    
    # 摄像头线程
    def capture_worker():
        for _ in range(n_frames + 10):
            frame = camera.read()
            if frame is not None:
                idx, write_buf = buffer.get_write_buffer()
                np.copyto(write_buf, frame)
                buffer.commit_write()
    
    # 推理线程
    def infer_worker():
        for _ in range(n_frames):
            frame = buffer.get_read_buffer()
            t0 = time.perf_counter()
            dets, _ = infer.infer(frame)
            t1 = time.perf_counter()
            results.append((t1 - t0) * 1000)
    
    # 启动线程
    import threading
    capture_thread = threading.Thread(target=capture_worker)
    infer_thread = threading.Thread(target=infer_worker)
    
    capture_thread.start()
    infer_thread.start()
    
    capture_thread.join()
    infer_thread.join()
    
    if results:
        avg_time = np.mean(results)
        fps = 1000 / avg_time if avg_time > 0 else 0
        
        print(f"Frames: {len(results)}")
        print(f"Average inference: {avg_time:.1f} ms")
        print(f"FPS: {fps:.1f}")
        
        # 获取双缓冲统计
        stats = buffer.get_stats()
        print(f"Drop rate: {stats['drop_rate']:.1f}%")
        
        return avg_time, fps
    
    return 0, 0


def main():
    """主函数。"""
    print("=" * 60)
    print("Desk-Safety Performance Profile")
    print("=" * 60)
    
    # 加载配置
    config_path = "./configs/config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    print(f"\nConfig: {config_path}")
    cfg = load_settings(config_path)
    
    # 创建摄像头
    print(f"\nCamera: {cfg.camera_device}")
    print(f"use_v4l2: {cfg.use_v4l2}")
    
    # 尝试V4L2，失败则回退到OpenCV
    camera = None
    if cfg.use_v4l2:
        try:
            camera = NativeV4l2Camera(
                cfg.camera_device,
                cfg.camera_width,
                cfg.camera_height,
                cfg.camera_crop_left
            )
            camera.open()
            print("Using V4L2 camera")
        except Exception as e:
            print(f"V4L2 failed: {e}, falling back to OpenCV")
            camera = None
    
    if camera is None:
        camera = CameraCapture(
            cfg.camera_device,
            cfg.camera_width,
            cfg.camera_height,
            cfg.camera_crop_left
        )
        camera.open()
        print("Using OpenCV camera")
    
    # 创建推理引擎
    print(f"\nModel: {cfg.model_path}")
    print(f"use_native: {cfg.use_native}")
    
    if cfg.use_native:
        infer = NativeInferenceEngine(
            cfg.model_path,
            cfg.class_names,
            cfg.conf_threshold,
            cfg.nms_threshold,
            cfg.input_size,
            num_classes=len(cfg.class_names),
            use_yolo11=True,
        )
    else:
        infer = InferenceEngine(
            cfg.model_path,
            cfg.class_names,
            cfg.conf_threshold,
            cfg.nms_threshold,
            cfg.input_size,
        )
    
    infer.open()
    
    # 运行性能测试
    cam_time, cam_fps = profile_camera(camera)
    infer_time, infer_fps = profile_inference(infer, camera)
    pipeline_time, pipeline_fps = profile_pipeline(camera, infer)
    
    # 汇总
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"Camera: {cam_time:.1f} ms ({cam_fps:.1f} FPS)")
    print(f"Inference: {infer_time:.1f} ms ({infer_fps:.1f} FPS)")
    print(f"Pipeline: {pipeline_time:.1f} ms ({pipeline_fps:.1f} FPS)")
    print(f"Estimated total: {cam_time + infer_time:.1f} ms ({1000/(cam_time + infer_time):.1f} FPS)")
    
    # 清理
    camera.close()
    infer.close()


if __name__ == "__main__":
    main()
