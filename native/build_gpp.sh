#!/bin/bash
# build_gpp.sh - 使用g++直接编译C++推理库
#
# 用法: ./build_gpp.sh [clean]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BUILD_DIR="build"
OUTPUT="librknn_infer.so"

# 清理
if [ "$1" = "clean" ]; then
    echo "Cleaning build directory..."
    rm -rf "$BUILD_DIR" "$OUTPUT"
fi

# 创建build目录
mkdir -p "$BUILD_DIR"

echo "Compiling..."
echo "  Source files:"
echo "    - rknn_infer.cpp"
echo "    - mpp_jpeg_decoder.cpp"
echo "    - v4l2_camera.cpp"

# 编译
g++ -O2 -Wall -shared -fPIC -std=c++17 \
    -I./include \
    -I/usr/include \
    -I/usr/include/rockchip \
    -I/usr/include/rga \
    -o "$BUILD_DIR/$OUTPUT" \
    rknn_infer.cpp \
    mpp_jpeg_decoder.cpp \
    v4l2_camera.cpp \
    -lrknnrt \
    -lrockchip_mpp \
    -lrga \
    -lpthread

echo ""
echo "Build completed!"
echo "Library: $SCRIPT_DIR/$BUILD_DIR/$OUTPUT"
echo ""
echo "To install:"
echo "  cp $SCRIPT_DIR/$BUILD_DIR/$OUTPUT $SCRIPT_DIR/"
echo "  ldconfig"
