# ADB工具安装和配置指南

## macOS系统安装ADB

### 方法1: 使用Homebrew (推荐)
```bash
# 安装Homebrew (如果还没有安装)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装Android Platform Tools (包含ADB)
brew install android-platform-tools

# 验证安装
adb version
```

### 方法2: 手动下载安装
1. 访问 [Android开发者网站](https://developer.android.com/studio/releases/platform-tools)
2. 下载 Platform Tools for macOS
3. 解压到 `/usr/local/bin/` 或其他PATH目录
4. 添加到PATH环境变量

### 方法3: 通过Android Studio
1. 安装Android Studio
2. 在SDK Manager中安装Platform Tools
3. 添加SDK platform-tools目录到PATH

## Windows系统安装ADB

### 使用Chocolatey
```cmd
# 安装Chocolatey (管理员权限)
@"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"

# 安装ADB
choco install adb
```

### 手动安装
1. 下载Platform Tools for Windows
2. 解压到 `C:\adb\` 目录
3. 添加到系统环境变量PATH

## Linux系统安装ADB

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install android-tools-adb
```

### CentOS/RHEL/Fedora
```bash
# CentOS/RHEL
sudo yum install android-tools

# Fedora
sudo dnf install android-tools
```

## Android设备配置

### 1. 启用开发者选项
1. 打开**设置** → **关于手机**
2. 连续点击**版本号**7次启用开发者选项
3. 返回设置，找到**开发者选项**

### 2. 启用USB调试
1. 进入**开发者选项**
2. 开启**USB调试**
3. 开启**USB安装**（如果有的话）
4. 开启**USB调试（安全设置）**（某些设备）

### 3. 连接测试
```bash
# 连接设备后执行
adb devices

# 应该显示类似输出:
# List of devices attached
# XXXXXXXXXX    device
```

### 4. 授权设备
- 首次连接时设备会显示授权对话框
- 勾选"始终允许这台计算机进行调试"
- 点击"确定"

## 常见问题解决

### 问题1: 设备未识别
```bash
# 重启adb服务
adb kill-server
adb start-server
adb devices
```

### 问题2: 权限问题 (Linux)
```bash
# 添加udev规则
sudo vim /etc/udev/rules.d/51-android.rules

# 添加内容 (替换XXXX为厂商ID):
SUBSYSTEM=="usb", ATTR{idVendor}=="XXXX", MODE="0666", GROUP="plugdev"

# 重新加载规则
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 问题3: macOS权限问题
- 系统偏好设置 → 安全性与隐私 → 隐私
- 选择"辅助功能"或"完全磁盘访问权限"
- 添加终端应用程序权限

## 验证安装

运行测试脚本验证ADB配置：
```bash
# 在项目根目录执行
source activate_venv.sh
python -c "
from src.adb.device_controller import AndroidController
controller = AndroidController()
if controller.device_id:
    print('✅ ADB配置成功，设备已连接')
else:
    print('❌ 未检测到设备，请检查连接和USB调试设置')
"
```

## 主要ADB命令

```bash
# 查看连接的设备
adb devices

# 截图并保存到电脑
adb shell screencap -p /sdcard/screenshot.png
adb pull /sdcard/screenshot.png ./

# 模拟点击 (x, y坐标)
adb shell input tap 500 1000

# 模拟滑动
adb shell input swipe 500 1000 500 500 1000

# 获取设备信息
adb shell getprop ro.product.model
adb shell wm size

# 安装/卸载应用
adb install app.apk
adb uninstall com.package.name
```

## 安全提示

⚠️ **重要安全提醒**:
- 仅在可信任的计算机上启用USB调试
- 不要在公共场所连接未知USB端口
- 定期检查已授权的调试设备列表
- 使用完毕后可以关闭USB调试功能

## 故障排除

如果遇到问题，请按以下步骤排查：

1. **检查USB线缆** - 使用原装或质量良好的数据线
2. **更换USB端口** - 尝试不同的USB接口
3. **重启设备** - 重启手机和电脑
4. **重装驱动** - 更新或重装设备驱动程序
5. **检查设置** - 确认开发者选项和USB调试都已启用

需要更多帮助请参考：
- [Android开发者官方文档](https://developer.android.com/studio/command-line/adb)
- [ADB用户指南](https://developer.android.com/studio/command-line/adb)