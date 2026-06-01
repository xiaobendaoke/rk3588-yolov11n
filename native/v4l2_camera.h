/**
 * v4l2_camera.h - V4L2摄像头封装
 *
 * 使用V4L2 MMAP零拷贝访问摄像头，减少内核到用户空间的数据拷贝
 */

#ifndef __V4L2_CAMERA_H__
#define __V4L2_CAMERA_H__

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct V4l2Camera V4l2Camera;

/**
 * 创建V4L2摄像头
 * @param device 设备路径，如 "/dev/video21"
 * @param width 宽度
 * @param height 高度
 * @return 摄像头句柄，失败返回NULL
 */
V4l2Camera* v4l2_camera_create(const char* device, int width, int height);

/**
 * 打开摄像头
 * @param cam 摄像头句柄
 * @return 0成功，负数失败
 */
int v4l2_camera_open(V4l2Camera* cam);

/**
 * 读取一帧MJPG数据
 * @param cam 摄像头句柄
 * @param buffer 输出缓冲区
 * @param buffer_size 缓冲区大小
 * @return 读取的数据大小，0表示无数据，负数失败
 */
int v4l2_camera_read(V4l2Camera* cam, uint8_t* buffer, int buffer_size);

/**
 * 读取一帧并解码为NV12（左半帧）
 * @param cam 摄像头句柄
 * @param out_data 输出缓冲区（NV12格式，左半帧）
 * @param out_size 输出缓冲区大小
 * @return 解码后的数据大小，负数失败
 */
int v4l2_camera_read_nv12_left(V4l2Camera* cam, uint8_t* out_data, int out_size);

/**
 * 读取一帧并解码为RGB（左半帧）
 * @param cam 摄像头句柄
 * @param out_data 输出缓冲区（RGB格式，左半帧）
 * @param out_size 输出缓冲区大小
 * @return 解码后的数据大小，负数失败
 */
int v4l2_camera_read_rgb_left(V4l2Camera* cam, uint8_t* out_data, int out_size);

/**
 * 释放摄像头
 * @param cam 摄像头句柄
 */
void v4l2_camera_destroy(V4l2Camera* cam);

#ifdef __cplusplus
}
#endif

#endif /* __V4L2_CAMERA_H__ */
