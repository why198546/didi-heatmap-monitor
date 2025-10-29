# 滴滴热力图监控和预测系统

这是一个专为滴滴司机设计的智能热力图监控和预测系统，通过自动化截图分析和机器学习技术，帮助司机预测最佳接单区域。

## 🎯 项目特色

- **自动化监控**: 通过ADB控制Android手机，自动截取滴滴热力图
- **智能拼接**: 将多张截图智能拼接成完整的拉萨市地图
- **AI识别**: 使用计算机视觉技术识别橙色六边形热点区域
- **预测分析**: 基于历史数据和机器学习模型预测未来热点分布
- **实时展示**: Web仪表板实时显示当前热力图和预测结果

## 🏗️ 系统架构

```
├── src/                    # 源代码
│   ├── adb/               # Android设备控制
│   ├── image/             # 图像处理和分析
│   ├── gps/               # GPS位置管理
│   ├── database/          # 数据存储
│   ├── ml/                # 机器学习预测
│   └── web/               # Web仪表板
├── config/                # 配置文件
├── data/                  # 数据存储
├── web/                   # Web前端
└── tests/                 # 测试文件
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Android手机（已安装滴滴出行APP）
- ADB工具
- 电脑与手机的USB连接

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd DiDi
   ```

2. **创建虚拟环境**
   ```bash
   # 创建虚拟环境
   python3 -m venv .venv
   
   # 激活虚拟环境 (Linux/macOS)
   source .venv/bin/activate
   # 或使用便捷脚本
   source activate_venv.sh
   
   # 激活虚拟环境 (Windows)
   .venv\Scripts\activate
   ```

3. **安装依赖**
   ```bash
   # 确保虚拟环境已激活
   pip install -r requirements.txt
   ```

4. **配置ADB**
   - 在Android手机上启用开发者选项和USB调试
   - 安装ADB工具并配置环境变量
   - 连接手机到电脑，确认ADB连接正常

5. **配置系统**
   ```bash
   # 复制配置文件并根据实际情况修改
   cp config/settings.py.example config/settings.py
   ```

5. **初始化数据库**
   ```bash
   python main.py --mode once
   ```

### 运行方式

#### 1. 单次监控
```bash
python main.py --mode once
```

#### 2. 持续监控（默认5分钟间隔）
```bash
python main.py --mode monitor --interval 5
```

#### 3. 启动Web仪表板
```bash
python main.py --mode web
```

#### 4. 同时运行监控和Web服务
```bash
# 终端1：启动监控
python main.py --mode monitor

# 终端2：启动Web服务
python main.py --mode web
```

## 📋 功能详解

### 1. ADB自动控制
- **设备连接**: 自动检测并连接Android设备
- **屏幕截图**: 定时捕获滴滴APP界面
- **GPS获取**: 获取设备当前GPS位置
- **手势模拟**: 模拟滑动操作覆盖整个拉萨区域

### 2. 图像处理
- **区域拼接**: 将多张截图拼接成完整地图
- **UI过滤**: 自动去除状态栏、按钮等UI元素
- **六边形检测**: 识别橙色和深橙色的热点六边形
- **坐标转换**: 将像素坐标转换为地理坐标

### 3. 数据管理
- **SQLite存储**: 本地数据库存储历史热力图数据
- **时间序列**: 按时间维度组织数据
- **统计分析**: 提供各种统计指标
- **数据清理**: 自动清理过期数据

### 4. 机器学习预测
- **特征工程**: 时间、位置、天气等多维特征
- **随机森林**: 使用随机森林回归模型
- **增量学习**: 随着数据积累持续优化模型
- **置信度评估**: 为每个预测提供置信度分数

### 5. Web仪表板
- **实时显示**: 显示当前热力图状态
- **交互地图**: 基于Leaflet的交互式地图
- **趋势图表**: 历史数据趋势可视化
- **预测面板**: 未来30分钟、1小时的预测结果

## ⚙️ 配置说明

主要配置项在 `config/settings.py` 中：

```python
# ADB设置
ADB_PATH = "/usr/local/bin/adb"  # ADB工具路径
DEVICE_ID = None  # 设备ID，None表示自动检测

# 地图设置
MAP_ZOOM_LEVEL = 14  # 地图缩放级别
SCREEN_WIDTH = 1080  # 手机屏幕宽度
SCREEN_HEIGHT = 2340  # 手机屏幕高度

# 拉萨范围
LHASA_BOUNDS = {
    'north': 29.7000,
    'south': 29.6000,
    'east': 91.2000,
    'west': 91.0500
}

# 监控间隔
MONITORING_CONFIG = {
    'capture_interval': 5 * 60,  # 5分钟
    'max_retry_attempts': 3,
    'retry_delay': 30
}
```

## 📊 数据模型

### 热力图数据表
```sql
CREATE TABLE heatmap_data (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    latitude REAL,
    longitude REAL,
    hexagon_count INTEGER,
    hexagons_data TEXT,  -- JSON格式
    is_holiday BOOLEAN,
    day_of_week INTEGER,
    hour_of_day INTEGER
);
```

### 六边形详细数据表
```sql
CREATE TABLE hexagon_details (
    id INTEGER PRIMARY KEY,
    heatmap_id INTEGER,
    center_lat REAL,
    center_lng REAL,
    area_m2 REAL,
    confidence REAL,
    color_type TEXT
);
```

## 🔧 故障排除

### 常见问题

1. **ADB连接失败**
   - 检查手机是否开启USB调试
   - 确认ADB工具已正确安装
   - 尝试重新连接USB线

2. **截图识别不准确**
   - 检查手机屏幕分辨率设置
   - 调整UI边距配置
   - 确保滴滴APP界面完整显示

3. **GPS位置获取失败**
   - 确认手机GPS已开启
   - 检查定位权限设置
   - 在室外环境测试

4. **预测准确率低**
   - 增加数据收集时间
   - 检查特征工程设置
   - 调整模型参数

### 日志分析

系统日志保存在 `data/logs/didi_monitor.log`：

```bash
# 查看最新日志
tail -f data/logs/didi_monitor.log

# 搜索错误信息
grep "ERROR" data/logs/didi_monitor.log
```

## 📈 性能优化

### 提升截图速度
- 优化滑动距离和等待时间
- 使用多线程处理图像
- 调整图像压缩比例

### 提升预测准确率
- 收集更多历史数据
- 添加天气、事件等外部特征
- 尝试不同的机器学习算法

### 降低资源占用
- 定期清理旧数据
- 优化数据库索引
- 使用图像缓存机制

## 🛡️ 安全注意事项

1. **隐私保护**: 系统仅在本地处理数据，不上传到外部服务器
2. **合规使用**: 请确保使用本工具符合滴滴服务条款
3. **数据安全**: 定期备份重要数据
4. **设备安全**: 避免在驾驶时操作手机

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目仅供学习和研究使用，请遵守相关法律法规和服务条款。

## 📞 支持

如有问题或建议，请通过以下方式联系：

- 提交GitHub Issue
- 发送邮件至：[your-email@example.com]

---

**免责声明**: 本工具仅用于技术研究和学习目的，使用者需自行承担使用风险，并确保合规使用。