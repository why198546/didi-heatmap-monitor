# 使用指南 - DiDi热力图监控系统

## 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone https://github.com/why198546/didi-heatmap-monitor.git
cd didi-heatmap-monitor

# 激活虚拟环境
source activate_venv.sh

# 验证环境
python -c "from src.image.hexagon_detector import HexagonDetector; print('✅ 环境配置正确')"
```

### 2. ADB设置
按照 [ADB安装指南](ADB_SETUP.md) 安装和配置ADB工具。

### 3. 运行模式

#### 模式1: 单次分析
```bash
python main.py --mode once
```
- 适用于: 测试系统功能
- 执行: 单次截图分析
- 输出: 热点区域信息

#### 模式2: 持续监控
```bash
python main.py --mode monitor --interval 5
```
- 适用于: 实时监控热力图变化
- 执行: 每5分钟自动分析一次
- 输出: 持续的热点数据记录

#### 模式3: Web仪表板
```bash
python main.py --mode web
```
- 适用于: 可视化查看数据
- 访问: http://localhost:5000
- 功能: 实时热力图、历史数据、预测分析

## VS Code集成使用

### 使用VS Code任务
1. 按 `Cmd+Shift+P` (macOS) 或 `Ctrl+Shift+P` (Windows/Linux)
2. 输入 "Tasks: Run Task"
3. 选择需要的任务:
   - **运行滴滴热力图监控系统** - 启动持续监控
   - **启动Web仪表板** - 打开Web界面
   - **单次运行热力图捕获** - 测试单次分析
   - **系统初始化检查** - 验证环境配置
   - **检查ADB连接** - 测试设备连接

### 调试和开发
```bash
# 测试核心模块
python -c "
from src.database.data_manager import DataManager
dm = DataManager()
dm.initialize_database()
print('数据库初始化完成')
"

# 测试图像处理
python -c "
from src.image.hexagon_detector import HexagonDetector
detector = HexagonDetector()
print('图像检测器初始化完成')
"
```

## 配置说明

### 主要配置文件: `config/settings.py`

```python
class Config:
    # ADB工具路径 (根据实际安装位置调整)
    ADB_PATH = "/usr/local/bin/adb"
    
    # 拉萨市地图边界 (可根据需要调整范围)
    MAP_BOUNDS = {
        'north': 29.7,
        'south': 29.6,
        'east': 91.2,
        'west': 91.0
    }
    
    # 截图和分析设置
    SCREENSHOT_DELAY = 2.0  # 截图间隔
    SWIPE_DURATION = 1000   # 滑动时长
    
    # 热点检测参数
    HEXAGON_MIN_AREA = 100  # 最小热点面积
    HEXAGON_MAX_AREA = 5000 # 最大热点面积
```

### GPS模板配置
将滴滴APP中的蓝色定位点图标保存到:
- `config/templates/blue_dot.png`
- `config/templates/blue_dot_pin.png`

## 数据存储

### 数据库结构
```sql
-- 热力图数据表
CREATE TABLE heatmap_data (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    latitude REAL,
    longitude REAL,
    intensity INTEGER,
    screenshot_path TEXT
);

-- 预测结果表  
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    predicted_zones TEXT,
    confidence_score REAL
);
```

### 文件组织
```
data/
├── screenshots/     # 原始截图
├── processed/       # 处理后的图像
├── cache/          # 临时缓存
├── backup/         # 数据备份
└── logs/           # 运行日志
```

## Web仪表板使用

### 访问界面
启动Web模式后访问: http://localhost:5000

### 主要功能
1. **实时热力图** - 显示当前热点分布
2. **历史数据** - 查看过去的热力图记录
3. **预测分析** - AI预测下一时段热点
4. **统计图表** - 热点趋势和模式分析
5. **设备状态** - ADB连接和系统状态

### API接口
```bash
# 获取当前热力图数据
curl http://localhost:5000/api/heatmap/current

# 获取预测数据
curl http://localhost:5000/api/predictions/next

# 获取历史统计
curl http://localhost:5000/api/statistics/daily
```

## 故障排除

### 常见问题

#### 1. 程序无法启动
```bash
# 检查Python环境
python --version
which python

# 重新激活虚拟环境
source activate_venv.sh

# 检查依赖安装
pip list | grep opencv
```

#### 2. ADB连接失败
```bash
# 检查ADB状态
adb devices

# 重启ADB服务
adb kill-server
adb start-server

# 检查设备权限
adb shell id
```

#### 3. 截图分析失败
- 确保滴滴APP已打开到热力图界面
- 检查屏幕亮度和清晰度
- 验证GPS模板文件是否正确

#### 4. Web界面无法访问
```bash
# 检查端口占用
lsof -i :5000

# 更换端口启动
python main.py --mode web --port 8080
```

### 日志分析
查看详细日志信息:
```bash
# 查看最新日志
tail -f data/logs/didi_monitor.log

# 搜索错误信息
grep "ERROR" data/logs/didi_monitor.log

# 查看特定时间段日志
grep "2025-10-30" data/logs/didi_monitor.log
```

## 性能优化

### 系统要求
- **CPU**: 双核2.0GHz以上
- **内存**: 4GB RAM最低，8GB推荐
- **存储**: 2GB可用空间
- **网络**: 稳定的网络连接

### 优化建议
1. **定期清理数据**: 使用"清理旧数据"任务
2. **调整截图间隔**: 根据需要修改监控频率
3. **优化图像处理**: 调整检测参数提高效率
4. **数据库优化**: 定期重建索引和清理

## 高级用法

### 自定义检测区域
修改 `config/settings.py` 中的 `MAP_BOUNDS` 设置其他城市范围。

### 机器学习模型调优
```python
# 在src/ml/predictor.py中调整模型参数
self.model = RandomForestRegressor(
    n_estimators=200,     # 增加树的数量
    max_depth=15,         # 调整树的深度
    random_state=42
)
```

### 扩展API功能
在 `src/web/dashboard.py` 中添加新的API端点：

```python
@app.route('/api/custom/analysis')
def custom_analysis():
    # 自定义分析逻辑
    return jsonify({"status": "success"})
```

## 安全和隐私

### 数据安全
- 所有数据存储在本地，不上传到外部服务器
- 定期备份重要数据到安全位置
- 使用加密存储敏感配置信息

### 隐私保护
- 截图数据仅用于热力图分析
- 不收集个人身份信息
- 遵守相关法律法规和平台使用条款

## 更新和维护

### 系统更新
```bash
# 更新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 数据库升级
python -c "from src.database.data_manager import DataManager; DataManager().initialize_database()"
```

### 备份数据
```bash
# 备份数据库
cp data/didi_heatmap.db data/backup/backup_$(date +%Y%m%d).db

# 备份配置
cp -r config/ data/backup/config_backup/
```

## 技术支持

如需技术支持，请提供以下信息：
1. 系统版本 (macOS/Windows/Linux)
2. Python版本
3. 错误日志内容
4. 设备连接状态
5. 复现步骤

项目地址: https://github.com/why198546/didi-heatmap-monitor
问题反馈: 在GitHub Issues中提交问题报告