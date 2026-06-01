#!/usr/bin/env python3
"""
将 cutter 标签和图片从自定义数据集复制到 COCO 数据集
"""

import os
import shutil
from pathlib import Path

# 路径配置
CUSTOM_DIR = Path("/mnt/hgfs/Detecting working desk.v1i.yolov11")
COCO_DIR = Path("/mnt/hgfs/coco")

# 类别映射：自定义数据集中的 cutter 索引是 3，COCO 中是 80
CUTTER_CLASS_CUSTOM = 3
CUTTER_CLASS_COCO = 80


def process_split(split_name, coco_split_name):
    """处理一个数据集分割（train/valid/test）"""
    print(f"\n处理 {split_name} 分割...")
    
    src_lbl_dir = CUSTOM_DIR / split_name / 'labels'
    src_img_dir = CUSTOM_DIR / split_name / 'images'
    
    # 目标目录
    dst_lbl_dir = COCO_DIR / 'labels' / coco_split_name
    dst_img_dir = COCO_DIR / coco_split_name / 'images'
    
    if not src_lbl_dir.exists():
        print(f"  源标签目录不存在: {src_lbl_dir}")
        return 0, 0
    
    # 确保目标目录存在
    dst_lbl_dir.mkdir(parents=True, exist_ok=True)
    dst_img_dir.mkdir(parents=True, exist_ok=True)
    
    cutter_files = 0
    
    # 遍历所有标签文件
    for lbl_file in src_lbl_dir.iterdir():
        if not lbl_file.name.endswith('.txt'):
            continue
        
        # 检查是否包含 cutter 类
        has_cutter = False
        with open(lbl_file) as f:
            for line in f:
                line = line.strip()
                if line and line.startswith(f'{CUTTER_CLASS_CUSTOM} '):
                    has_cutter = True
                    break
        
        if not has_cutter:
            continue
            
        cutter_files += 1
        
        # 读取标签内容并转换类别索引
        with open(lbl_file) as f:
            content = f.read()
        
        # 将类别索引从 3 改为 80
        new_content = content.replace(f'{CUTTER_CLASS_CUSTOM} ', f'{CUTTER_CLASS_COCO} ')
        
        # 写入目标标签文件
        dst_lbl = dst_lbl_dir / lbl_file.name
        with open(dst_lbl, 'w') as f:
            f.write(new_content)
        
        # 查找并复制对应的图片
        stem = lbl_file.stem
        img_found = False
        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
            img_file = src_img_dir / f"{stem}{ext}"
            if img_file.exists():
                dst_img = dst_img_dir / img_file.name
                shutil.copy2(img_file, dst_img)
                img_found = True
                break
        
        if not img_found:
            print(f"  警告: 找不到图片 {stem}")
    
    print(f"  cutter 文件: {cutter_files}")
    return cutter_files


def main():
    print("=" * 60)
    print("复制 cutter 标签和图片到 COCO 数据集")
    print("=" * 60)
    
    # 处理训练集
    train_cutter = process_split('train', 'train2017')
    
    # 处理验证集
    val_cutter = process_split('valid', 'val2017')
    
    # 处理测试集（如果有）
    test_cutter = process_split('test', 'test2017')
    
    print("\n" + "=" * 60)
    print("汇总:")
    print(f"  训练集: {train_cutter} 个 cutter 标签")
    print(f"  验证集: {val_cutter} 个 cutter 标签")
    print(f"  测试集: {test_cutter} 个 cutter 标签")
    print(f"  总计: {train_cutter + val_cutter + test_cutter} 个 cutter 标签")
    print("=" * 60)


if __name__ == '__main__':
    main()
