# Desk Safety 部署指南

## 前提条件

1. 板子已开机并连接到网络
2. 通过USB串口连接到板子
3. 板子可以访问互联网（用于下载依赖和克隆代码）

## 部署步骤

### 方法一：使用自动化脚本（推荐）

1. **将部署脚本传输到板子**

   由于使用USB串口，你需要手动将脚本内容复制到板子上。在板子上执行：

   ```bash
   # 创建脚本文件
   nano /tmp/deploy.sh
   ```

   然后将 `deploy_to_board.sh` 的内容复制到板子上。

2. **运行部署脚本**

   ```bash
   chmod +x /tmp/deploy.sh
   sudo /tmp/deploy.sh
   ```

3. **配置摄像头和模型**

   编辑配置文件：

   ```bash
   cd /opt/desk-safety
   nano configs/config.yaml
   ```

   根据你的设备修改以下配置：
   - `camera_device`: 摄像头设备路径（通过 `v4l2-ctl --list-devices` 查看）
   - `model_path`: RKNN 模型文件路径
   - 其他参数根据需要调整

4. **启动服务**

   ```bash
   sudo systemctl start desk-safety.service
   sudo systemctl status desk-safety.service
   ```

5. **访问Web界面**

   打开浏览器，访问：`http://<板子IP>:8080`

### 方法二：手动部署

如果自动化脚本不适用，可以按照以下步骤手动部署：

1. **安装系统依赖**

   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip python3-venv git v4l-utils
   ```

2. **克隆代码**

   ```bash
   sudo mkdir -p /opt/desk-safety
   sudo chown $USER:$USER /opt/desk-safety
   git clone https://github.com/xiaobendaoke/rk3588-yolov8n.git /opt/desk-safety
   ```

3. **创建虚拟环境并安装依赖**

   ```bash
   cd /opt/desk-safety
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **配置**

   ```bash
   cp configs/config.example.yaml configs/config.yaml
   nano configs/config.yaml
   ```

5. **手动测试**

   ```bash
   cd /opt/desk-safety
   source .venv/bin/activate
   python -m app.main --config configs/config.yaml
   ```

6. **安装systemd服务**

   ```bash
   sudo cp systemd/desk-safety.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable desk-safety.service
   sudo systemctl start desk-safety.service
   ```

## 验证部署

### 检查服务状态

```bash
sudo systemctl status desk-safety.service
```

### 查看日志

```bash
# 实时查看日志
sudo journalctl -u desk-safety.service -f

# 或查看项目日志
tail -f /opt/desk-safety/logs/desk-safety.log
```

### 检查Web界面

1. 获取板子IP地址：
   ```bash
   hostname -I
   ```

2. 在浏览器中访问：`http://<板子IP>:8080`

### 检查摄像头

```bash
# 列出摄像头设备
v4l2-ctl --list-devices

# 测试摄像头
v4l2-ctl --device=/dev/video0 --info
```

## 故障排除

### 服务启动失败

1. 检查日志：
   ```bash
   sudo journalctl -u desk-safety.service -n 100
   ```

2. 检查配置文件：
   ```bash
   cd /opt/desk-safety
   source .venv/bin/activate
   python -c "from app.config import load_settings; load_settings('configs/config.yaml')"
   ```

### 摄像头无法访问

1. 检查设备权限：
   ```bash
   ls -la /dev/video*
   sudo chmod 666 /dev/video0
   ```

2. 检查摄像头是否被占用：
   ```bash
   sudo lsof /dev/video0
   ```

### Web界面无法访问

1. 检查端口是否被占用：
   ```bash
   sudo netstat -tlnp | grep 8080
   ```

2. 检查防火墙：
   ```bash
   sudo ufw status
   sudo ufw allow 8080
   ```

## 更新部署

当有新的代码更新时，执行以下命令：

```bash
cd /opt/desk-safety
git fetch origin
git reset --hard origin/main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart desk-safety.service
```

## 卸载

```bash
sudo systemctl stop desk-safety.service
sudo systemctl disable desk-safety.service
sudo rm /etc/systemd/system/desk-safety.service
sudo systemctl daemon-reload
sudo rm -rf /opt/desk-safety
```
