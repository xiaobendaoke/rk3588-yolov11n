/**
 * mpp_jpeg_decoder.h - RK3588 MPP硬件JPEG解码器
 *
 * 使用Rockchip MPP进行硬件JPEG解码，比软件解码快3-5倍
 */

#ifndef __MPP_JPEG_DECODER_H__
#define __MPP_JPEG_DECODER_H__

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct MppJpegDecoder MppJpegDecoder;

/**
 * 创建MPP JPEG解码器
 * @return 解码器句柄，失败返回NULL
 */
MppJpegDecoder* mpp_jpeg_decoder_create();

/**
 * 初始化解码器
 * @param dec 解码器句柄
 * @param out_width 输出宽度
 * @param out_height 输出高度
 * @param out_format 输出格式: 0=NV12, 1=BGR, 2=RGB
 * @return 0成功，负数失败
 */
int mpp_jpeg_decoder_init(MppJpegDecoder* dec,
                          int out_width, int out_height,
                          int out_format);

/**
 * 解码MJPG数据到NV12
 * @param dec 解码器句柄
 * @param mjpg_data MJPG数据指针
 * @param mjpg_size MJPG数据大小
 * @param out_data 输出缓冲区
 * @param out_size 输出缓冲区大小
 * @return 解码后的数据大小，负数失败
 */
int mpp_jpeg_decoder_decode(MppJpegDecoder* dec,
                            const uint8_t* mjpg_data, int mjpg_size,
                            uint8_t* out_data, int out_size);

/**
 * 解码并裁剪左半帧
 * @param dec 解码器句柄
 * @param mjpg_data MJPG数据指针（完整双目帧）
 * @param mjpg_size MJPG数据大小
 * @param out_data 输出缓冲区（左半帧）
 * @param out_size 输出缓冲区大小
 * @return 解码后的数据大小，负数失败
 */
int mpp_jpeg_decoder_decode_left_half(MppJpegDecoder* dec,
                                      const uint8_t* mjpg_data, int mjpg_size,
                                      uint8_t* out_data, int out_size);

/**
 * 释放解码器
 * @param dec 解码器句柄
 */
void mpp_jpeg_decoder_destroy(MppJpegDecoder* dec);

#ifdef __cplusplus
}
#endif

#endif /* __MPP_JPEG_DECODER_H__ */
