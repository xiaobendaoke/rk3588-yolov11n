#!/bin/bash
# Desk Safety 部署脚本
# 在板子上通过串口执行此脚本

set -e  # 出错时停止

echo "=========================================="
echo "Desk Safety 部署脚本"
echo "=========================================="

# 配置
PROJECT_DIR="/opt/desk-safety"
GIT_REPO="https://github.com/xiaobendaoke/rk3588-yolov8n.git"

# 检查是否为root用户
if [ "$(id -u)" -ne 0 ]; then
    echo "错误：请使用sudo或root用户运行此脚本"
    exit 1
fi

echo "步骤 1: 安装系统依赖..."
apt-get update
apt-get install -y python3 python3-pip python3-venv git v4l-utils

echo "步骤 2: 创建项目目录..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

echo "步骤 3: 克隆或更新代码..."
if [ -d ".git" ]; then
    echo "项目已存在，更新代码..."
    git fetch origin
    git reset --hard origin/main
    git pull origin main
else
    echo "克隆项目..."
    git clone $GIT_REPO .
fi

echo "步骤 4: 创建Python虚拟环境..."
python3 -m venv .venv
source .venv/bin/activate

echo "步骤 5: 安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

echo "步骤 6: 创建必要目录..."
mkdir -p logs data/snapshots

echo "步骤 7: 复制配置文件..."
if [ ! -f "configs/config.yaml" ]; then
    echo "创建配置文件..."
    cp configs/config.example.yaml configs/config.yaml
    echo "请编辑 configs/config.yaml 配置摄像头和模型路径"
fi

echo "步骤 8: 检查摄像头设备..."
echo "可用的摄像头设备："
v4l2-ctl --list-devices 2>/dev/null || echo "v4l2-ctl 未安装或无设备"

echo "步骤 9: 安装systemd服务..."
cp systemd/desk-safety.service /etc/systemd/system/
systemctl daemon-reload

echo "步骤 10: 启用服务..."
systemctl enable desk-safety.service

echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "后续步骤："
echo "1. 编辑配置文件: nano $PROJECT_DIR/configs/config.yaml"
echo "2. 启动服务: systemctl start desk-safety.service"
echo "3. 检查状态: systemctl status desk-safety.service"
echo "4. 查看日志: journalctl -u desk-safety.service -f"
echo "5. 访问Web界面: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "手动测试命令："
echo "  cd $PROJECT_DIR"
echo "  source .venv/bin/activate"
echo "  python -m app.main --config configs/config.yaml"
