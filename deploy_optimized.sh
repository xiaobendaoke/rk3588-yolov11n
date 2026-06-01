#!/bin/bash
# deploy_optimized.sh - 部署优化后的代码到板子
#
# 用法: ./deploy_optimized.sh [board_ip]

set -e

BOARD_IP="${1:-192.168.88.2}"
BOARD_USER="root"
BOARD_PASS="root"
DEPLOY_DIR="/opt/desk-safety"

echo "=========================================="
echo "Deploying optimized desk-safety to board"
echo "Board: $BOARD_IP"
echo "=========================================="

# 1. 同步代码到板子
echo ""
echo "[1/4] Syncing code to board..."
sshpass -p "$BOARD_PASS" rsync -avz --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='node_modules' \
    --exclude='data' \
    --exclude='logs' \
    ./ "$BOARD_USER@$BOARD_IP:$DEPLOY_DIR/"

# 2. 在板子上编译C++库
echo ""
echo "[2/4] Building C++ library on board..."
sshpass -p "$BOARD_PASS" ssh "$BOARD_USER@$BOARD_IP" << 'EOF'
cd /opt/desk-safety/native
chmod +x build.sh
./build.sh clean
EOF

# 3. 安装编译好的库
echo ""
echo "[3/4] Installing library..."
sshpass -p "$BOARD_PASS" ssh "$BOARD_USER@$BOARD_IP" << 'EOF'
cp /opt/desk-safety/native/build/librknn_infer.so /opt/desk-safety/native/
ldconfig
EOF

# 4. 测试
echo ""
echo "[4/4] Running tests..."
sshpass -p "$BOARD_PASS" ssh "$BOARD_USER@$BOARD_IP" << 'EOF'
cd /opt/desk-safety
source .venv/bin/activate 2>/dev/null || true
python3 -c "
import sys
sys.path.insert(0, '.')
from app.infer.native_engine import NativeInferenceEngine
print('NativeInferenceEngine imported successfully')
"
EOF

echo ""
echo "=========================================="
echo "Deployment completed!"
echo ""
echo "To run on board:"
echo "  ssh $BOARD_USER@$BOARD_IP"
echo "  cd $DEPLOY_DIR"
echo "  python3 -m app.main --config ./configs/config.yaml"
echo ""
echo "To run consistency test:"
echo "  ssh $BOARD_USER@$BOARD_IP"
echo "  cd $DEPLOY_DIR"
echo "  python3 tests/test_yolo11_consistency.py"
echo "=========================================="
