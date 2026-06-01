"""V4L2 + MPP硬件JPEG解码摄像头Python绑定。"""

from __future__ import annotations

import ctypes
import logging
import time
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger("desk-safety.v4l2_camera")


class NativeV4l2Camera:
    """使用C++实现的V4L2摄像头，支持MPP硬件JPEG解码。
    
    相比OpenCV VideoCapture，有以下优势：
    1. V4L2 MMAP零拷贝，减少内核到用户空间的数据拷贝
    2. MPP硬件JPEG解码，比软件解码快3-5倍
    3. 直接裁剪左半帧，无需额外处理
    """

    def __init__(self, device: str, width: int, height: int, crop_left: bool = True):
        """初始化V4L2摄像头。
        
        Args:
            device: 设备路径，如 "/dev/video21"
            width: 宽度
            height: 高度
            crop_left: 是否裁剪左半帧
        """
        self.device = device
        self.width = width
        self.height = height
        self.crop_left = crop_left
        self._lib = None
        self._cam = None
        self._buffer = None
        self._stub_mode = False
        self._log = logging.getLogger("desk-safety.v4l2_camera")

    def _find_library(self) -> str | None:
        """查找librknn_infer.so。"""
        candidates = [
            Path("/opt/desk-safety/native/librknn_infer.so"),
            Path(__file__).parent.parent.parent / "native" / "librknn_infer.so",
            Path("native/librknn_infer.so"),
            Path("native/build/librknn_infer.so"),
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    def open(self) -> None:
        """打开摄像头。"""
        lib_path = self._find_library()
        if not lib_path:
            self._log.warning("librknn_infer.so not found, falling back to stub mode")
            self._stub_mode = True
            return

        try:
            self._lib = ctypes.CDLL(lib_path)

            # 设置函数签名
            self._lib.v4l2_camera_create.restype = ctypes.c_void_p
            self._lib.v4l2_camera_create.argtypes = [
                ctypes.c_char_p, ctypes.c_int, ctypes.c_int
            ]

            self._lib.v4l2_camera_open.restype = ctypes.c_int
            self._lib.v4l2_camera_open.argtypes = [ctypes.c_void_p]

            self._lib.v4l2_camera_read.restype = ctypes.c_int
            self._lib.v4l2_camera_read.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int
            ]

            self._lib.v4l2_camera_read_nv12_left.restype = ctypes.c_int
            self._lib.v4l2_camera_read_nv12_left.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int
            ]

            self._lib.v4l2_camera_destroy.restype = None
            self._lib.v4l2_camera_destroy.argtypes = [ctypes.c_void_p]

            # 创建摄像头
            self._cam = self._lib.v4l2_camera_create(
                self.device.encode("utf-8"),
                self.width,
                self.height
            )

            if not self._cam:
                self._log.error("v4l2_camera_create failed")
                self._stub_mode = True
                return

            # 打开摄像头
            ret = self._lib.v4l2_camera_open(self._cam)
            if ret != 0:
                self._log.error("v4l2_camera_open failed: %d", ret)
                self._stub_mode = True
                return

            # 分配缓冲区
            if self.crop_left:
                out_width = self.width // 2
            else:
                out_width = self.width
            out_height = self.height

            # NV12缓冲区: width * height * 3/2
            buf_size = out_width * out_height * 3 // 2
            self._buffer = np.zeros(buf_size, dtype=np.uint8)

            self._log.info("V4L2 camera opened: %s (%dx%d)", self.device, self.width, self.height)

        except Exception as e:
            self._log.error("Failed to open V4L2 camera: %s", e)
            self._stub_mode = True

    def read(self) -> np.ndarray | None:
        """读取一帧。
        
        Returns:
            BGR格式的图像帧，失败返回None
        """
        if self._stub_mode:
            # Stub模式，返回黑色帧
            if self.crop_left:
                return np.zeros((self.height, self.width // 2, 3), dtype=np.uint8)
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

        if not self._cam:
            raise RuntimeError("camera not opened")

        # 读取NV12数据
        buf_ptr = self._buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        ret = self._lib.v4l2_camera_read_nv12_left(
            self._cam, buf_ptr, len(self._buffer)
        )

        if ret <= 0:
            return None

        # NV12转BGR
        if self.crop_left:
            out_width = self.width // 2
        else:
            out_width = self.width
        out_height = self.height

        # 重塑NV12数据
        y_size = out_width * out_height
        y_plane = self._buffer[:y_size].reshape(out_height, out_width)
        uv_plane = self._buffer[y_size:y_size + y_size // 2].reshape(out_height // 2, out_width)

        # NV12转BGR
        frame = cv2.cvtColorTwoPlane(y_plane, uv_plane, cv2.COLOR_YUV2BGR_NV12)

        return frame

    def read_mjpg(self) -> bytes | None:
        """读取原始MJPG数据（用于调试）。
        
        Returns:
            MJPG数据，失败返回None
        """
        if self._stub_mode or not self._cam:
            return None

        # 分配MJPG缓冲区
        mjpg_buf = np.zeros(2560 * 960 * 2, dtype=np.uint8)
        buf_ptr = mjpg_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        ret = self._lib.v4l2_camera_read(self._cam, buf_ptr, len(mjpg_buf))

        if ret <= 0:
            return None

        return mjpg_buf[:ret].tobytes()

    def close(self) -> None:
        """关闭摄像头。"""
        if self._cam:
            self._lib.v4l2_camera_destroy(self._cam)
            self._cam = None
        self._log.info("V4L2 camera closed")


class OpenCVCamera:
    """OpenCV VideoCapture摄像头（备用）。"""

    def __init__(self, device: str, width: int, height: int, crop_left: bool = True):
        """初始化OpenCV摄像头。"""
        self.device = device
        self.width = width
        self.height = height
        self.crop_left = crop_left
        self.cap = None
        self._log = logging.getLogger("desk-safety.opencv_camera")

    def open(self) -> None:
        """打开摄像头。"""
        self.cap = cv2.VideoCapture(self.device)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if not self.cap.isOpened():
            raise RuntimeError(f"failed to open camera device: {self.device}")
        self._log.info("OpenCV camera opened: %s", self.device)

    def read(self) -> np.ndarray | None:
        """读取一帧。"""
        if self.cap is None:
            raise RuntimeError("camera not opened")
        ok, frame = self.cap.read()
        if not ok:
            return None
        if self.crop_left:
            h, w = frame.shape[:2]
            frame = frame[:, :w // 2]
        return frame

    def close(self) -> None:
        """关闭摄像头。"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None


def create_camera(device: str, width: int, height: int, 
                  crop_left: bool = True, use_v4l2: bool = True) -> NativeV4l2Camera | OpenCVCamera:
    """创建摄像头实例。
    
    Args:
        device: 设备路径
        width: 宽度
        height: 高度
        crop_left: 是否裁剪左半帧
        use_v4l2: 是否使用V4L2（默认True）
        
    Returns:
        摄像头实例
    """
    if use_v4l2:
        return NativeV4l2Camera(device, width, height, crop_left)
    return OpenCVCamera(device, width, height, crop_left)
