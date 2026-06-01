#!/usr/bin/env python3
"""
将多边形分割标签转换为 YOLO 检测格式（边界框）

输入格式（多边形）:  class_id x1 y1 x2 y2 x3 y3 ...
输出格式（检测框）:  class_id x_center y_center width height
"""

import os
import sys
from pathlib import Path

LABEL_DIRS = [
    Path("/mnt/hgfs/coco/labels/train2017"),
    Path("/mnt/hgfs/coco/labels/val2017"),
    Path("/mnt/hgfs/coco/labels/test2017"),
]


def polygon_to_bbox(parts):
    """将多边形坐标转为边界框 [x_center, y_center, width, height]"""
    class_id = int(parts[0])
    coords = [float(x) for x in parts[1:]]
    # 坐标是 x1,y1,x2,y2,... 的形式
    xs = coords[0::2]  # 所有 x 坐标
    ys = coords[1::2]  # 所有 y 坐标
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2
    width = x_max - x_min
    height = y_max - y_min
    # 裁剪到 [0, 1]
    x_center = max(0, min(1, x_center))
    y_center = max(0, min(1, y_center))
    width = max(0, min(1, width))
    height = max(0, min(1, height))
    return f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"


def fix_label_file(filepath):
    """修复单个标签文件，返回 (原格式是否为多边形, 是否修改了)"""
    with open(filepath) as f:
        lines = f.readlines()

    new_lines = []
    was_polygon = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue  # 跳过格式错误的行
        if len(parts) == 5:
            # 已经是检测格式，检查 class_id 是否合法
            try:
                cls_id = int(parts[0])
                if 0 <= cls_id <= 80:
                    new_lines.append(line)
                continue
            except ValueError:
                continue
        else:
            # 多边形格式，转换为边界框
            was_polygon = True
            try:
                bbox_line = polygon_to_bbox(parts)
                new_lines.append(bbox_line)
            except (ValueError, IndexError):
                continue

    if was_polygon and new_lines:
        with open(filepath, 'w') as f:
            f.write('\n'.join(new_lines) + '\n')
        return True, True
    elif was_polygon and not new_lines:
        return True, False  # 多边形但转换失败
    return False, False


def main():
    total_files = 0
    polygon_files = 0
    fixed_files = 0
    failed_files = 0

    for label_dir in LABEL_DIRS:
        if not label_dir.exists():
            print(f"[跳过] {label_dir} 不存在")
            continue

        print(f"[处理] {label_dir}")
        dir_total = 0
        dir_polygon = 0
        dir_fixed = 0

        for fname in sorted(os.listdir(label_dir)):
            if not fname.endswith('.txt'):
                continue
            filepath = label_dir / fname
            dir_total += 1
            was_polygon, was_fixed = fix_label_file(filepath)
            if was_polygon:
                dir_polygon += 1
                if was_fixed:
                    dir_fixed += 1
                else:
                    failed_files += 1

        total_files += dir_total
        polygon_files += dir_polygon
        fixed_files += dir_fixed
        print(f"  总计: {dir_total} 文件, 多边形: {dir_polygon}, 已修复: {dir_fixed}")

    print(f"\n{'=' * 50}")
    print(f"汇总:")
    print(f"  扫描文件: {total_files}")
    print(f"  多边形标签: {polygon_files}")
    print(f"  已修复: {fixed_files}")
    print(f"  修复失败: {failed_files}")
    print(f"  正常格式: {total_files - polygon_files}")

    # 验证修复结果
    print(f"\n[验证] 抽样检查修复后的文件...")
    bad_after = 0
    check_count = 0
    for label_dir in LABEL_DIRS:
        if not label_dir.exists():
            continue
        for fname in os.listdir(label_dir):
            if not fname.endswith('.txt'):
                continue
            filepath = label_dir / fname
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    check_count += 1
                    if len(parts) != 5:
                        bad_after += 1
                        if bad_after <= 3:
                            print(f"  仍有问题: {fname} -> {line[:60]}")
                        break

    print(f"  检查 {check_count} 行, 格式错误: {bad_after}")
    if bad_after == 0:
        print("  所有标签格式正确!")
    else:
        print(f"  警告: 仍有 {bad_after} 个文件格式不对!")

    return 0 if bad_after == 0 else 1


if __name__ == '__main__':
    sys.exit(main())