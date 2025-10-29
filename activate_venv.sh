#!/bin/bash

# 激活DiDi热力图监控系统虚拟环境
# 使用方法: source activate_venv.sh

echo "🚀 激活DiDi热力图监控系统虚拟环境..."

# 检查虚拟环境是否存在
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python3 -m venv .venv"
    return 1
fi

# 激活虚拟环境
source .venv/bin/activate

echo "✅ 虚拟环境已激活!"
echo "📦 Python路径: $(which python)"
echo "📦 Python版本: $(python --version)"
echo ""
echo "🔧 可用命令:"
echo "  python main.py --mode monitor    # 启动监控系统"
echo "  python main.py --mode web        # 启动Web仪表板"
echo "  python main.py --mode once       # 单次截图分析"
echo "  deactivate                       # 退出虚拟环境"
echo ""