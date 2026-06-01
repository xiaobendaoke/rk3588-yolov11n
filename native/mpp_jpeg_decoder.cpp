/**
 * mpp_jpeg_decoder.cpp - RK3588 MPP硬件JPEG解码器实现
 *
 * 使用Rockchip MPP进行硬件JPEG解码
 */

#include "mpp_jpeg_decoder.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// MPP头文件
#include "rk_mpi.h"
#include "mpp_frame.h"
#include "mpp_packet.h"
#include "mpp_buffer.h"
#include "mpp_err.h"

// 输出格式定义
#define OUT_FMT_NV12 0
#define OUT_FMT_BGR   1
#define OUT_FMT_RGB   2

struct MppJpegDecoder {
    MppCtx ctx;
    MppApi *mpi;
    MppFrame frame;
    int out_width;
    int out_height;
    int out_format;
    int initialized;

    // 缓冲区
    uint8_t *decode_buf;
    int decode_buf_size;
};

MppJpegDecoder* mpp_jpeg_decoder_create() {
    MppJpegDecoder* dec = (MppJpegDecoder*)calloc(1, sizeof(MppJpegDecoder));
    if (!dec) {
        fprintf(stderr, "mpp_jpeg_decoder_create: alloc failed\n");
        return NULL;
    }
    return dec;
}

int mpp_jpeg_decoder_init(MppJpegDecoder* dec,
                          int out_width, int out_height,
                          int out_format) {
    if (!dec) return -1;

    dec->out_width = out_width;
    dec->out_height = out_height;
    dec->out_format = out_format;
    dec->initialized = 0;

    MPP_RET ret = MPP_OK;

    // 创建MPP解码上下文
    ret = mpp_create(&dec->ctx, &dec->mpi);
    if (ret != MPP_OK) {
        fprintf(stderr, "mpp_create failed: %d\n", ret);
        return -1;
    }

    // 初始化为MJPEG解码器
    ret = mpp_init(dec->ctx, MPP_CTX_DEC, MPP_VIDEO_CodingMJPEG);
    if (ret != MPP_OK) {
        fprintf(stderr, "mpp_init failed: %d\n", ret);
        mpp_destroy(dec->ctx);
        dec->ctx = NULL;
        return -1;
    }

    // 分配解码缓冲区
    // NV12: width * height * 3/2
    dec->decode_buf_size = out_width * out_height * 3 / 2;
    dec->decode_buf = (uint8_t*)malloc(dec->decode_buf_size);
    if (!dec->decode_buf) {
        fprintf(stderr, "malloc decode buffer failed\n");
        mpp_destroy(dec->ctx);
        dec->ctx = NULL;
        return -1;
    }

    dec->initialized = 1;
    return 0;
}

int mpp_jpeg_decoder_decode(MppJpegDecoder* dec,
                            const uint8_t* mjpg_data, int mjpg_size,
                            uint8_t* out_data, int out_size) {
    if (!dec || !dec->initialized || !mjpg_data || !out_data) return -1;

    MPP_RET ret = MPP_OK;
    MppPacket packet = NULL;
    MppFrame frame = NULL;

    // 创建输入数据包
    ret = mpp_packet_init(&packet, (void*)mjpg_data, mjpg_size);
    if (ret != MPP_OK) {
        fprintf(stderr, "mpp_packet_init failed: %d\n", ret);
        return -1;
    }

    // 发送数据到解码器
    ret = dec->mpi->decode_put_packet(dec->ctx, packet);
    if (ret != MPP_OK) {
        fprintf(stderr, "decode_put_packet failed: %d\n", ret);
        mpp_packet_deinit(&packet);
        return -1;
    }

    // 获取解码帧
    ret = dec->mpi->decode_get_frame(dec->ctx, &frame);
    if (ret != MPP_OK || !frame) {
        fprintf(stderr, "decode_get_frame failed: %d\n", ret);
        mpp_packet_deinit(&packet);
        return -1;
    }

    // 检查帧是否有效
    if (!mpp_frame_get_info_change(frame)) {
        // 帧有效，拷贝数据
        int y_size = dec->out_width * dec->out_height;
        int uv_size = y_size / 2;
        int total_size = y_size + uv_size;

        if (out_size < total_size) {
            fprintf(stderr, "output buffer too small: %d < %d\n", out_size, total_size);
            mpp_frame_deinit(&frame);
            mpp_packet_deinit(&packet);
            return -1;
        }

        // 从MPP帧拷贝到输出缓冲区
        MppBuffer buf = mpp_frame_get_buffer(frame);
        if (buf) {
            void *ptr = mpp_buffer_get_ptr(buf);
            if (ptr) {
                memcpy(out_data, ptr, total_size);
                mpp_frame_deinit(&frame);
                mpp_packet_deinit(&packet);
                return total_size;
            }
        }

        fprintf(stderr, "failed to get frame buffer\n");
        mpp_frame_deinit(&frame);
        mpp_packet_deinit(&packet);
        return -1;
    } else {
        // 帧信息变化，需要重新初始化
        fprintf(stderr, "frame info changed, reinitializing\n");
        mpp_frame_deinit(&frame);
        mpp_packet_deinit(&packet);
        return -1;
    }
}

int mpp_jpeg_decoder_decode_left_half(MppJpegDecoder* dec,
                                      const uint8_t* mjpg_data, int mjpg_size,
                                      uint8_t* out_data, int out_size) {
    if (!dec || !dec->initialized || !mjpg_data || !out_data) return -1;

    // 先解码完整帧到临时缓冲区
    int ret = mpp_jpeg_decoder_decode(dec, mjpg_data, mjpg_size,
                                      dec->decode_buf, dec->decode_buf_size);
    if (ret < 0) return ret;

    // 裁剪左半帧 (NV12格式)
    int half_width = dec->out_width / 2;
    int y_size = half_width * dec->out_height;
    int uv_size = y_size / 2;
    int total_size = y_size + uv_size;

    if (out_size < total_size) {
        fprintf(stderr, "output buffer too small for left half: %d < %d\n", out_size, total_size);
        return -1;
    }

    // 拷贝Y平面（左半）
    const uint8_t* src_y = dec->decode_buf;
    uint8_t* dst_y = out_data;
    for (int i = 0; i < dec->out_height; i++) {
        memcpy(dst_y + i * half_width, src_y + i * dec->out_width, half_width);
    }

    // 拷贝UV平面（左半）
    const uint8_t* src_uv = dec->decode_buf + dec->out_width * dec->out_height;
    uint8_t* dst_uv = out_data + y_size;
    for (int i = 0; i < dec->out_height / 2; i++) {
        memcpy(dst_uv + i * half_width, src_uv + i * dec->out_width, half_width);
    }

    return total_size;
}

void mpp_jpeg_decoder_destroy(MppJpegDecoder* dec) {
    if (!dec) return;

    if (dec->ctx) {
        dec->mpi->reset(dec->ctx);
        mpp_destroy(dec->ctx);
    }

    if (dec->decode_buf) {
        free(dec->decode_buf);
    }

    free(dec);
}
