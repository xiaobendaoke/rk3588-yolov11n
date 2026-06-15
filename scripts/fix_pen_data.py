#!/usr/bin/env python3
"""从 Open Images V7 下载 pen 类别的数据。

使用正确的 MID /m/0k1tl (Pen) 从已下载的标注文件中筛选，
然后下载对应图片并转换为 YOLO 格式。
"""

import csv
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


# pen 的正确 MID
PEN_MID = "/m/0k1tl"
PEN_CLASS_ID = 16  # 在当前 data.yaml 中的 class ID

# Open Images downloader 路径
DOWNLOADER_PATH = "/mnt/hgfs/open_images_v7/downloader.py"

# 标注文件路径
TRAIN_ANN = "/mnt/hgfs/open_images_v7/dataset/train-annotations.csv"
VAL_ANN = "/mnt/hgfs/open_images_v7/dataset/val-annotations.csv"

# 输出目录
OUTPUT_DIR = Path("/mnt/hgfs/open_images_v7/dataset/pen_data")


def filter_pen_annotations(ann_path: str, max_images: int = 500) -> dict:
    """从标注文件中筛选 pen 类别的标注。"""
    print(f"  处理: {os.path.basename(ann_path)}")

    annotations = defaultdict(list)
    count = 0

    with open(ann_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("LabelName") != PEN_MID:
                continue

            image_id = row.get("ImageID", "")
            xmin = float(row.get("XMin", 0))
            xmax = float(row.get("XMax", 0))
            ymin = float(row.get("YMin", 0))
            ymax = float(row.get("YMax", 0))

            # 跳过无效标注
            if xmax <= xmin or ymax <= ymin:
                continue
            if row.get("IsGroupOf", "0") == "1":
                continue

            annotations[image_id].append({
                "XMin": xmin,
                "XMax": xmax,
                "YMin": ymin,
                "YMax": ymax,
            })
            count += 1

    # 限制图片数量
    limited = dict(list(annotations.items())[:max_images])
    total_anns = sum(len(v) for v in limited.values())

    print(f"    标注总数: {count}")
    print(f"    筛选图片数: {len(limited)}")
    print(f"    筛选标注数: {total_anns}")

    return limited


def create_image_list(annotations: dict, output_path: str, split: str) -> None:
    """创建图片列表文件。"""
    with open(output_path, "w") as f:
        for image_id in sorted(annotations.keys()):
            f.write(f"{split}/{image_id}\n")
    print(f"  图片列表已保存: {output_path} ({len(annotations)} 张)")


def download_images(image_list_path: str, output_dir: str) -> int:
    """使用 Open Images downloader 下载图片。"""
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        sys.executable, DOWNLOADER_PATH,
        image_list_path,
        f"--download_folder={output_dir}",
        "--num_process=5",
    ]

    print(f"  下载图片到: {output_dir}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 统计下载的图片数
    downloaded = len(list(Path(output_dir).glob("*.jpg")))
    print(f"  下载完成: {downloaded} 张")
    return downloaded


def convert_to_yolo(annotations: dict, images_dir: str, class_id: int) -> int:
    """将标注转换为 YOLO 格式。"""
    converted = 0

    for image_id, anns in annotations.items():
        img_path = os.path.join(images_dir, f"{image_id}.jpg")
        if not os.path.exists(img_path):
            continue

        txt_path = os.path.splitext(img_path)[0] + ".txt"
        lines = []

        for ann in anns:
            x_center = (ann["XMin"] + ann["XMax"]) / 2
            y_center = (ann["YMin"] + ann["YMax"]) / 2
            width = ann["XMax"] - ann["XMin"]
            height = ann["YMax"] - ann["YMin"]

            # 验证坐标有效性
            if width <= 0 or height <= 0:
                continue
            if width * height < 0.0001:  # 过滤极小 bbox
                continue

            lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

        if lines:
            with open(txt_path, "w") as f:
                f.write("\n".join(lines))
            converted += 1

    return converted


def copy_to_merged_dataset(annotations: dict, images_dir: str, split: str) -> int:
    """将下载的图片和标注复制到合并数据集目录。"""
    import shutil

    merged_dir = Path("/mnt/hgfs/merged_dataset")
    target_img = merged_dir / split / "images"
    target_lbl = merged_dir / split / "labels"

    copied = 0
    for image_id in annotations.keys():
        src_img = Path(images_dir) / f"{image_id}.jpg"
        src_lbl = Path(images_dir) / f"{image_id}.txt"

        if src_img.exists() and src_lbl.exists():
            shutil.copy2(src_img, target_img / src_img.name)
            shutil.copy2(src_lbl, target_lbl / src_lbl.name)
            copied += 1

    return copied


def main():
    print("=" * 60)
    print("Pen 数据下载脚本")
    print("=" * 60)

    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    train_img_dir = str(OUTPUT_DIR / "train" / "images")
    val_img_dir = str(OUTPUT_DIR / "val" / "images")

    # 1. 筛选标注
    print("\n[1/4] 筛选 pen 标注...")
    print(f"  MID: {PEN_MID}")

    train_ann = filter_pen_annotations(TRAIN_ANN, max_images=500)
    val_ann = filter_pen_annotations(VAL_ANN, max_images=50)

    # 保存标注信息
    with open(OUTPUT_DIR / "train_annotations.json", "w") as f:
        json.dump(train_ann, f)
    with open(OUTPUT_DIR / "val_annotations.json", "w") as f:
        json.dump(val_ann, f)

    # 2. 创建图片列表
    print("\n[2/4] 创建图片列表...")
    train_list = str(OUTPUT_DIR / "train_images.txt")
    val_list = str(OUTPUT_DIR / "val_images.txt")
    create_image_list(train_ann, train_list, "train")
    create_image_list(val_ann, val_list, "validation")

    # 3. 下载图片
    print("\n[3/4] 下载图片...")
    train_downloaded = download_images(train_list, train_img_dir)
    val_downloaded = download_images(val_list, val_img_dir)

    # 4. 转换为 YOLO 格式
    print("\n[4/4] 转换为 YOLO 格式...")
    train_converted = convert_to_yolo(train_ann, train_img_dir, PEN_CLASS_ID)
    val_converted = convert_to_yolo(val_ann, val_img_dir, PEN_CLASS_ID)

    # 复制到合并数据集
    print("\n复制到合并数据集...")
    train_copied = copy_to_merged_dataset(train_ann, train_img_dir, "train")
    val_copied = copy_to_merged_dataset(val_ann, val_img_dir, "val")

    # 统计
    print("\n" + "=" * 60)
    print("完成！")
    print(f"  训练集: {train_converted} 张已转换, {train_copied} 张已复制")
    print(f"  验证集: {val_converted} 张已转换, {val_copied} 张已复制")
    print("=" * 60)


if __name__ == "__main__":
    main()
