#!/bin/bash
# YOLO11 81类检测模型训练脚本 - 优化版
# 使用优化后的超参数和修复后的数据集

set -e

echo "=========================================="
echo "开始训练 YOLO11 81类检测模型 (优化版)"
echo "=========================================="

# 检查数据集
echo "检查数据集..."
if [ ! -f "/mnt/hgfs/coco/data.yaml" ]; then
    echo "错误: data.yaml 不存在"
    exit 1
fi

# 检查 cutter 标签
CUTTER_COUNT=$(find /mnt/hgfs/coco/labels/train2017/ -name "*images-45*" -o -name "*images-48*" -o -name "*IMG_071*" | wc -l)
echo "训练集中 cutter 标签文件数: $CUTTER_COUNT"

if [ "$CUTTER_COUNT" -eq 0 ]; then
    echo "警告: 训练集中没有 cutter 标签，请先运行 fix_cutter_labels_v2.py"
    exit 1
fi

# 删除旧的缓存文件
echo "删除缓存文件..."
find /mnt/hgfs/coco/ -name "*.cache" -type f -delete 2>/dev/null || true

# 训练命令
echo "开始训练..."
echo "模型: yolo11n.pt"
echo "数据集: /mnt/hgfs/coco/data.yaml"
echo "输出目录: desk_safety/yolo11n_81cls_v2"
echo ""

yolo detect train \
    model=yolo11n.pt \
    data=/mnt/hgfs/coco/data.yaml \
    epochs=200 \
    batch=16 \
    imgsz=640 \
    device=0 \
    workers=12 \
    project=desk_safety \
    name=yolo11n_81cls_v2 \
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
    cls_pw=1.0 \
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
    erasing=0.4 \
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
echo "最佳模型: /mnt/hgfs/runs/detect/desk_safety/yolo11n_81cls_v2/weights/best.pt"
echo ""
echo "查看训练结果:"
echo "yolo detect val model=/mnt/hgfs/runs/detect/desk_safety/yolo11n_81cls_v2/weights/best.pt data=/mnt/hgfs/coco/data.yaml"
