/**
 * rknn_infer.h - RKNN 推理库头文件
 *
 * 支持多 NPU 核心并行推理，支持YOLO11格式
 */

#ifndef __RKNN_INFER_H__
#define __RKNN_INFER_H__

#include <stdint.h>

#define MAX_DETECTIONS 128

typedef struct {
    int class_id;
    float confidence;
    int x1, y1, x2, y2;
} C_Detection;

typedef struct {
    C_Detection dets[MAX_DETECTIONS];
    int count;
} DetectionResult;

#ifdef __cplusplus
extern "C" {
#endif

/**
 * 创建RKNN推理引擎
 * @param model_path RKNN模型文件路径
 * @param input_size 输入尺寸（如640）
 * @param conf_threshold 置信度阈值
 * @param nms_threshold NMS阈值
 * @param num_classes 类别数
 * @return 引擎句柄，失败返回NULL
 */
void* rknn_engine_create(const char* model_path, int input_size,
                          float conf_threshold, float nms_threshold,
                          int num_classes);

/**
 * 使用通用后处理推理（兼容旧格式）
 * @param engine 引擎句柄
 * @param img_data 输入图像数据（RGB格式，input_size x input_size）
 * @param img_width 图像宽度
 * @param img_height 图像高度
 * @param result 输出检测结果
 * @return 0成功，负数失败
 */
int rknn_engine_infer(void* engine, const uint8_t* img_data,
                       int img_width, int img_height,
                       DetectionResult* result);

/**
 * 使用YOLO11专用后处理推理（推荐）
 * @param engine 引擎句柄
 * @param img_data 输入图像数据（RGB格式，input_size x input_size）
 * @param img_width 图像宽度
 * @param img_height 图像高度
 * @param result 输出检测结果
 * @return 0成功，负数失败
 */
int rknn_engine_infer_yolo11(void* engine, const uint8_t* img_data,
                              int img_width, int img_height,
                              DetectionResult* result);

/**
 * 销毁推理引擎
 * @param engine 引擎句柄
 */
void rknn_engine_destroy(void* engine);

#ifdef __cplusplus
}
#endif

#endif /* __RKNN_INFER_H__ */
