#!/bin/bash
# YOLO11 16类桌面安全检测模型训练脚本 - v5
# 使用清理后的数据集 + Open Images V7 补充数据

set -e

echo "=========================================="
echo "开始训练 YOLO11 16类桌面安全检测模型 (v5)"
echo "=========================================="

# 检查数据集
echo "检查数据集..."
DATA_YAML="/mnt/hgfs/merged_dataset/data.yaml"
if [ ! -f "$DATA_YAML" ]; then
    echo "错误: data.yaml 不存在"
    exit 1
fi

# 检查图片数量
TRAIN_COUNT=$(ls /mnt/hgfs/merged_dataset/train/images/*.jpg 2>/dev/null | wc -l)
VAL_COUNT=$(ls /mnt/hgfs/merged_dataset/val/images/*.jpg 2>/dev/null | wc -l)
echo "训练集: $TRAIN_COUNT 张图片"
echo "验证集: $VAL_COUNT 张图片"

if [ "$TRAIN_COUNT" -lt 1000 ]; then
    echo "警告: 训练集图片数量不足，请先运行数据合并脚本"
    exit 1
fi

# 删除旧的缓存文件
echo "删除缓存文件..."
find /mnt/hgfs/merged_dataset/ -name "*.cache" -type f -delete 2>/dev/null || true

# 训练命令
echo "开始训练..."
echo "模型: yolo11n.pt"
echo "数据集: $DATA_YAML"
echo "输出目录: desk_safety/yolo11n_desk_v5"
echo ""

yolo detect train \
    model=yolo11n.pt \
    data=$DATA_YAML \
    epochs=300 \
    batch=16 \
    imgsz=640 \
    device=0 \
    workers=8 \
    project=desk_safety \
    name=yolo11n_desk_v5 \
    exist_ok=true \
    pretrained=true \
    optimizer=auto \
    lr0=0.001 \
    lrf=0.01 \
    momentum=0.937 \
    weight_decay=0.0005 \
    warmup_epochs=3.0 \
    warmup_momentum=0.8 \
    warmup_bias_lr=0.1 \
    box=7.5 \
    cls=0.5 \
    cls_pw=2.0 \
    dfl=1.5 \
    hsv_h=0.015 \
    hsv_s=0.7 \
    hsv_v=0.4 \
    degrees=0.0 \
    translate=0.1 \
    scale=0.5 \
    shear=0.0 \
    perspective=0.0 \
    flipud=0.0 \
    fliplr=0.5 \
    mosaic=1.0 \
    mixup=0.15 \
    copy_paste=0.1 \
    erasing=0.4 \
    close_mosaic=15 \
    patience=50 \
    save=true \
    save_period=-1 \
    cache=false \
    amp=true \
    val=true \
    plots=true \
    verbose=true

echo ""
echo "=========================================="
echo "训练完成！"
echo "=========================================="
echo "最佳模型: /mnt/hgfs/runs/detect/desk_safety/yolo11n_desk_v5/weights/best.pt"
echo ""
echo "查看训练结果:"
echo "yolo detect val model=/mnt/hgfs/runs/detect/desk_safety/yolo11n_desk_v5/weights/best.pt data=$DATA_YAML"
