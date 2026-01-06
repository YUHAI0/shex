#!/usr/bin/env python3
"""
Shex PyPI 发布脚本
自动构建并发布到 PyPI
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent


def get_version() -> str:
    """读取版本号"""
    version_file = ROOT / "VERSION"
    return version_file.read_text(encoding="utf-8").strip()


def get_token() -> str:
    """从 .pypitoken 文件读取 token"""
    token_file = ROOT / ".pypitoken"
    if not token_file.exists():
        print("错误: 未找到 .pypitoken 文件")
        print(f"请在 {token_file} 创建文件并写入 PyPI API Token")
        sys.exit(1)
    
    token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        print("错误: .pypitoken 文件为空")
        sys.exit(1)
    
    return token


def clean():
    """清理构建目录"""
    dirs_to_clean = ["build", "dist", "*.egg-info"]
    
    for pattern in dirs_to_clean:
        if "*" in pattern:
            for path in ROOT.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path)
                    print(f"已删除: {path}")
        else:
            path = ROOT / pattern
            if path.exists():
                shutil.rmtree(path)
                print(f"已删除: {path}")


def build_package():
    """构建包"""
    print("\n构建包...")
    result = subprocess.run(
        [sys.executable, "-m", "build"],
        cwd=ROOT
    )
    if result.returncode != 0:
        print("构建失败")
        sys.exit(1)
    print("构建成功")


def upload(token: str):
    """上传到 PyPI"""
    print("\n上传到 PyPI...")
    result = subprocess.run(
        [
            sys.executable, "-m", "twine", "upload",
            "--username", "__token__",
            "--password", token,
            "dist/*"
        ],
        cwd=ROOT
    )
    if result.returncode != 0:
        print("上传失败")
        sys.exit(1)
    print("上传成功")


def main():
    """主函数"""
    version = get_version()
    print(f"Shex v{version} 发布脚本")
    print("=" * 40)
    
    # 检查依赖
    try:
        import build
        import twine
    except ImportError:
        print("安装构建依赖...")
        subprocess.run([sys.executable, "-m", "pip", "install", "build", "twine"])
    
    # 读取 token
    token = get_token()
    
    # 清理
    print("\n清理旧构建...")
    clean()
    
    # 构建
    build_package()
    
    # 上传
    upload(token)
    
    print("\n" + "=" * 40)
    print(f"✅ shex v{version} 发布成功!")
    print("安装命令: pip install shex")


if __name__ == "__main__":
    main()
