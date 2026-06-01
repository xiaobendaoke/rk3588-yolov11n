/**
 * v4l2_camera.cpp - V4L2摄像头实现
 *
 * 使用V4L2 MMAP零拷贝访问摄像头，集成MPP硬件JPEG解码
 */

#include "v4l2_camera.h"
#include "mpp_jpeg_decoder.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <linux/videodev2.h>

#define BUFFER_COUNT 4
#define MAX_MJPG_SIZE (2560 * 960 * 2)  // 最大MJPG大小

struct V4l2Camera {
    char device[256];
    int width;
    int height;
    int fd;

    struct Buffer {
        uint8_t* start;
        size_t length;
    } buffers[BUFFER_COUNT];

    int current_buf;
    int started;

    // MPP解码器
    MppJpegDecoder* decoder;

    // 临时缓冲区
    uint8_t* mjpg_buf;
    int mjpg_buf_size;
};

V4l2Camera* v4l2_camera_create(const char* device, int width, int height) {
    V4l2Camera* cam = (V4l2Camera*)calloc(1, sizeof(V4l2Camera));
    if (!cam) {
        fprintf(stderr, "v4l2_camera_create: alloc failed\n");
        return NULL;
    }

    strncpy(cam->device, device, sizeof(cam->device) - 1);
    cam->width = width;
    cam->height = height;
    cam->fd = -1;
    cam->started = 0;
    cam->decoder = NULL;

    // 分配MJPG缓冲区
    cam->mjpg_buf_size = MAX_MJPG_SIZE;
    cam->mjpg_buf = (uint8_t*)malloc(cam->mjpg_buf_size);
    if (!cam->mjpg_buf) {
        fprintf(stderr, "v4l2_camera_create: alloc mjpg buf failed\n");
        free(cam);
        return NULL;
    }

    // 创建MPP解码器
    cam->decoder = mpp_jpeg_decoder_create();
    if (!cam->decoder) {
        fprintf(stderr, "v4l2_camera_create: create decoder failed\n");
        free(cam->mjpg_buf);
        free(cam);
        return NULL;
    }

    return cam;
}

int v4l2_camera_open(V4l2Camera* cam) {
    if (!cam) return -1;

    // 打开设备
    cam->fd = open(cam->device, O_RDWR | O_NONBLOCK);
    if (cam->fd < 0) {
        fprintf(stderr, "Failed to open %s: %s\n", cam->device, strerror(errno));
        return -1;
    }

    // 查询能力
    struct v4l2_capability cap;
    if (ioctl(cam->fd, VIDIOC_QUERYCAP, &cap) < 0) {
        fprintf(stderr, "VIDIOC_QUERYCAP failed: %s\n", strerror(errno));
        close(cam->fd);
        return -1;
    }

    if (!(cap.capabilities & V4L2_CAP_VIDEO_CAPTURE)) {
        fprintf(stderr, "%s is not a video capture device\n", cam->device);
        close(cam->fd);
        return -1;
    }

    // 设置格式
    struct v4l2_format fmt;
    memset(&fmt, 0, sizeof(fmt));
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    fmt.fmt.pix.width = cam->width;
    fmt.fmt.pix.height = cam->height;
    fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_MJPEG;
    fmt.fmt.pix.field = V4L2_FIELD_NONE;

    if (ioctl(cam->fd, VIDIOC_S_FMT, &fmt) < 0) {
        fprintf(stderr, "VIDIOC_S_FMT failed: %s\n", strerror(errno));
        close(cam->fd);
        return -1;
    }

    // 验证格式
    if (fmt.fmt.pix.pixelformat != V4L2_PIX_FMT_MJPEG) {
        fprintf(stderr, "MJPEG not supported by %s\n", cam->device);
        close(cam->fd);
        return -1;
    }

    // 请求缓冲区
    struct v4l2_requestbuffers req;
    memset(&req, 0, sizeof(req));
    req.count = BUFFER_COUNT;
    req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    req.memory = V4L2_MEMORY_MMAP;

    if (ioctl(cam->fd, VIDIOC_REQBUFS, &req) < 0) {
        fprintf(stderr, "VIDIOC_REQBUFS failed: %s\n", strerror(errno));
        close(cam->fd);
        return -1;
    }

    // 映射缓冲区
    for (int i = 0; i < BUFFER_COUNT; i++) {
        struct v4l2_buffer buf;
        memset(&buf, 0, sizeof(buf));
        buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        buf.memory = V4L2_MEMORY_MMAP;
        buf.index = i;

        if (ioctl(cam->fd, VIDIOC_QUERYBUF, &buf) < 0) {
            fprintf(stderr, "VIDIOC_QUERYBUF failed: %s\n", strerror(errno));
            close(cam->fd);
            return -1;
        }

        cam->buffers[i].length = buf.length;
        cam->buffers[i].start = (uint8_t*)mmap(NULL, buf.length,
                                                PROT_READ | PROT_WRITE,
                                                MAP_SHARED,
                                                cam->fd, buf.m.offset);

        if (cam->buffers[i].start == MAP_FAILED) {
            fprintf(stderr, "mmap failed: %s\n", strerror(errno));
            close(cam->fd);
            return -1;
        }

        // 入队缓冲区
        if (ioctl(cam->fd, VIDIOC_QBUF, &buf) < 0) {
            fprintf(stderr, "VIDIOC_QBUF failed: %s\n", strerror(errno));
            close(cam->fd);
            return -1;
        }
    }

    // 开始流
    enum v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (ioctl(cam->fd, VIDIOC_STREAMON, &type) < 0) {
        fprintf(stderr, "VIDIOC_STREAMON failed: %s\n", strerror(errno));
        close(cam->fd);
        return -1;
    }

    cam->started = 1;

    // 初始化MPP解码器
    // 输出为左半帧的NV12格式
    int half_width = cam->width / 2;
    int half_height = cam->height;
    if (mpp_jpeg_decoder_init(cam->decoder, half_width, half_height, 0) != 0) {
        fprintf(stderr, "mpp_jpeg_decoder_init failed\n");
        // 继续，但不使用MPP解码
    }

    return 0;
}

int v4l2_camera_read(V4l2Camera* cam, uint8_t* buffer, int buffer_size) {
    if (!cam || cam->fd < 0 || !buffer) return -1;

    // 取出已填充的缓冲区
    struct v4l2_buffer buf;
    memset(&buf, 0, sizeof(buf));
    buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf.memory = V4L2_MEMORY_MMAP;

    if (ioctl(cam->fd, VIDIOC_DQBUF, &buf) < 0) {
        if (errno == EAGAIN) return 0;  // 无数据
        fprintf(stderr, "VIDIOC_DQBUF failed: %s\n", strerror(errno));
        return -1;
    }

    // 拷贝数据（MMAP零拷贝到用户缓冲区）
    int copy_size = buf.bytesused < (size_t)buffer_size ? buf.bytesused : buffer_size;
    memcpy(buffer, cam->buffers[buf.index].start, copy_size);

    // 归还缓冲区
    if (ioctl(cam->fd, VIDIOC_QBUF, &buf) < 0) {
        fprintf(stderr, "VIDIOC_QBUF failed: %s\n", strerror(errno));
        return -1;
    }

    return copy_size;
}

int v4l2_camera_read_nv12_left(V4l2Camera* cam, uint8_t* out_data, int out_size) {
    if (!cam || cam->fd < 0 || !out_data) return -1;

    // 读取MJPG数据
    int mjpg_size = v4l2_camera_read(cam, cam->mjpg_buf, cam->mjpg_buf_size);
    if (mjpg_size <= 0) return mjpg_size;

    // 使用MPP解码并裁剪左半帧
    return mpp_jpeg_decoder_decode_left_half(cam->decoder,
                                             cam->mjpg_buf, mjpg_size,
                                             out_data, out_size);
}

int v4l2_camera_read_rgb_left(V4l2Camera* cam, uint8_t* out_data, int out_size) {
    if (!cam || cam->fd < 0 || !out_data) return -1;

    // TODO: 实现NV12到RGB的转换
    // 暂时使用NV12输出
    return v4l2_camera_read_nv12_left(cam, out_data, out_size);
}

void v4l2_camera_destroy(V4l2Camera* cam) {
    if (!cam) return;

    // 停止流
    if (cam->started && cam->fd >= 0) {
        enum v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        ioctl(cam->fd, VIDIOC_STREAMOFF, &type);
    }

    // 取消映射
    for (int i = 0; i < BUFFER_COUNT; i++) {
        if (cam->buffers[i].start && cam->buffers[i].start != MAP_FAILED) {
            munmap(cam->buffers[i].start, cam->buffers[i].length);
        }
    }

    // 关闭设备
    if (cam->fd >= 0) {
        close(cam->fd);
    }

    // 释放MPP解码器
    if (cam->decoder) {
        mpp_jpeg_decoder_destroy(cam->decoder);
    }

    // 释放缓冲区
    if (cam->mjpg_buf) {
        free(cam->mjpg_buf);
    }

    free(cam);
}
