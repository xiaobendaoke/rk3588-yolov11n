from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional

import cv2
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

from app.types import RuntimeStatus


class AppState:
    """推理循环和 Web 服务器之间的共享状态。

    存储最新帧的 JPEG 编码和运行时状态，通过锁保护实现线程安全访问。

    Attributes:
        lock: 用于同步帧和状态访问的线程锁。
        latest_jpeg: 最新帧编码为 JPEG 字节。
        status: 当前运行时状态快照。
    """

    def __init__(self) -> None:
        """初始化共享应用状态。"""
        self.lock = threading.Lock()
        self.latest_jpeg = b""
        self.status = RuntimeStatus()


def create_app(
    state: AppState,
    list_events: Callable[..., list],
    get_event: Callable[[int], dict | None] | None = None,
    get_event_stats: Callable[[], dict] | None = None,
) -> FastAPI:
    """创建并配置 FastAPI Web 应用。

    注册仪表板、实时视频流、帧服务、事件 API 和系统状态接口的路由。

    Args:
        state: 用于线程安全数据访问的共享应用状态。
        list_events: 列出事件的可调用对象（支持分页/过滤）。
        get_event: 根据 ID 获取单条事件的可调用对象。
        get_event_stats: 获取事件统计信息的可调用对象。

    Returns:
        配置好的 FastAPI 应用实例。
    """
    app = FastAPI(title="Desk Safety")

    @app.get("/")
    async def root():
        """提供主监控仪表板 HTML 页面。"""
        html_path = Path(__file__).parent / "templates" / "index.html"
        return FileResponse(html_path, media_type="text/html")

    @app.get("/live.mjpg")
    def live_mjpg() -> StreamingResponse:
        """以 MJPEG 视频流方式推送最新帧。"""
        def stream():
            while True:
                with state.lock:
                    frame = state.latest_jpeg
                if frame:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                else:
                    time.sleep(0.05)

        return StreamingResponse(stream(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/frame.jpg")
    def frame_jpeg() -> Response:
        """提供最新帧的静态 JPEG 图片。"""
        with state.lock:
            frame = state.latest_jpeg
        if frame:
            return Response(content=frame, media_type="image/jpeg")
        return Response(content=b"", media_type="image/jpeg")

    @app.get("/api/events")
    def api_events(
        page: int = Query(default=1, ge=1),
        size: int = Query(default=20, ge=1, le=200),
        risk_type: Optional[str] = Query(default=None),
    ) -> JSONResponse:
        """列出风险事件，支持分页和可选的风险类型过滤。"""
        items = list_events(page=page, size=size, risk_type=risk_type)
        return JSONResponse({"page": page, "size": size, "items": items})

    @app.get("/api/events/stats")
    def api_event_stats() -> JSONResponse:
        """获取事件聚合统计信息。"""
        if get_event_stats is None:
            return JSONResponse({"error": "not supported"}, status_code=501)
        return JSONResponse(get_event_stats())

    @app.get("/api/events/{event_id}")
    def api_event_detail(event_id: int) -> JSONResponse:
        """根据 ID 获取单条风险事件详情。"""
        if get_event is None:
            return JSONResponse({"error": "not supported"}, status_code=501)
        item = get_event(event_id)
        if item is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(item)

    @app.get("/api/status")
    def api_status() -> JSONResponse:
        """获取当前系统运行时状态。"""
        with state.lock:
            status = {
                "fps": round(state.status.fps, 2),
                "queue_size": state.status.queue_size,
                "last_event_time": state.status.last_event_time,
                "cpu_percent": state.status.cpu_percent,
                "gpu_load": round(state.status.gpu_load, 1),
                "npu_load": round(state.status.npu_load, 1),
                "mem_percent": state.status.mem_percent,
                "cpu_temp": round(state.status.cpu_temp, 1),
                "gpu_temp": round(state.status.gpu_temp, 1),
                "detection_count": state.status.detection_count,
            }
        return JSONResponse(status)

    return app


def annotate_frame(frame, detections, risks):
    """在帧上绘制检测框和风险标签。

    Args:
        frame: 要标注的图像帧（原地修改）。
        detections: 要绘制的 Detection 对象列表。
        risks: 要显示为文本的 RiskEventCandidate 对象列表。

    Returns:
        标注后的帧（与输入相同对象，原地修改）。
    """
    for d in detections:
        x1, y1, x2, y2 = d.bbox_xyxy
        cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 220, 80), 2)
        cv2.putText(
            frame,
            f"{d.class_name} {d.conf:.2f}",
            (x1, max(y1 - 6, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    for i, r in enumerate(risks):
        cv2.putText(
            frame,
            f"RISK:{r.risk_type}({r.severity})",
            (10, 24 + i * 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (20, 20, 250),
            2,
            cv2.LINE_AA,
        )

    return frame