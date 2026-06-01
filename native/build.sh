#!/bin/bash
# build.sh - 编译C++推理库
# 用法: ./build.sh [clean]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BUILD_DIR="build"

# 清理
if [ "$1" = "clean" ]; then
    echo "Cleaning build directory..."
    rm -rf "$BUILD_DIR"
fi

# 创建build目录
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# 运行cmake
echo "Running cmake..."
cmake .. -DCMAKE_BUILD_TYPE=Release

# 编译
echo "Building..."
make -j$(nproc)

echo ""
echo "Build completed!"
echo "Library: $SCRIPT_DIR/$BUILD_DIR/librknn_infer.so"
echo ""
echo "To install to /opt/desk-safety/native:"
echo "  sudo cp $SCRIPT_DIR/$BUILD_DIR/librknn_infer.so /opt/desk-safety/native/"
