#!/usr/bin/env python
"""
Shex 开发启动脚本
直接运行: python main.py [args]
"""

import sys
import os

# 将当前目录添加到 Python 路径，以便正确导入 shex 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shex.main import main

if __name__ == "__main__":
    main()
