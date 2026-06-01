"""双缓冲实现，用于摄像头捕获和推理并行。"""

from __future__ import annotations

import threading
import numpy as np


class DoubleBuffer:
    """双缓冲实现，用于摄像头捕获和推理并行。
    
    使用两个缓冲区交替读写，实现摄像头捕获和推理的并行执行：
    - 摄像头线程写入一个缓冲区
    - 推理线程读取另一个缓冲区
    - 写入完成后交换缓冲区
    
    这样可以避免推理等待摄像头读取，提高整体FPS。
    """

    def __init__(self, shape: tuple, dtype=np.uint8):
        """初始化双缓冲。
        
        Args:
            shape: 缓冲区形状，如 (480, 640, 3)
            dtype: 数据类型
        """
        self.buffers = [
            np.zeros(shape, dtype=dtype),
            np.zeros(shape, dtype=dtype)
        ]
        self.write_idx = 0
        self.ready = [False, False]
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.frame_count = 0
        self.drop_count = 0

    def get_write_buffer(self) -> tuple[int, np.ndarray]:
        """获取写入缓冲区。
        
        Returns:
            (索引, 缓冲区数组)
        """
        return self.write_idx, self.buffers[self.write_idx]

    def commit_write(self):
        """提交写入，切换缓冲区。"""
        with self.lock:
            # 如果另一个缓冲区还没被读取，计数丢帧
            if self.ready[self.write_idx]:
                self.drop_count += 1
            
            self.ready[self.write_idx] = True
            self.write_idx = 1 - self.write_idx
            self.frame_count += 1
            self.cond.notify_all()

    def get_read_buffer(self) -> np.ndarray:
        """获取最新的可读缓冲区（阻塞）。
        
        Returns:
            最新帧的副本
        """
        with self.lock:
            # 等待有新数据
            while not self.ready[1 - self.write_idx]:
                self.cond.wait()
            
            # 获取另一个缓冲区的数据
            read_idx = 1 - self.write_idx
            frame = self.buffers[read_idx].copy()
            self.ready[read_idx] = False
            
            return frame

    def get_read_buffer_nonblock(self) -> np.ndarray | None:
        """获取最新的可读缓冲区（非阻塞）。
        
        Returns:
            最新帧的副本，如果没有新数据返回None
        """
        with self.lock:
            read_idx = 1 - self.write_idx
            if not self.ready[read_idx]:
                return None
            
            frame = self.buffers[read_idx].copy()
            self.ready[read_idx] = False
            
            return frame

    def get_frame_count(self) -> int:
        """获取总帧数。"""
        with self.lock:
            return self.frame_count

    def get_drop_count(self) -> int:
        """获取丢帧数。"""
        with self.lock:
            return self.drop_count

    def get_stats(self) -> dict:
        """获取统计信息。"""
        with self.lock:
            return {
                "frame_count": self.frame_count,
                "drop_count": self.drop_count,
                "drop_rate": self.drop_count / max(self.frame_count, 1) * 100,
            }
