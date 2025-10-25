#!/usr/bin/env python3
"""
后端服务接口测试运行脚本
用于运行所有后端API接口的测试
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
import time


def setup_environment():
    """设置测试环境"""
    # 确保在正确的目录
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    
    # 添加backend目录到Python路径
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    print(f"✓ 设置工作目录: {backend_dir}")
    print(f"✓ Python路径已更新")


def check_dependencies():
    """检查测试依赖"""
    required_packages = [
        ("pytest", "pytest"),
        ("pytest-asyncio", "pytest_asyncio"), 
        ("httpx", "httpx"),
        ("fastapi", "fastapi"),
        ("sqlalchemy", "sqlalchemy"),
        ("pillow", "PIL")
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install " + " ".join(missing_packages))
        return False
    
    print("✓ 所有依赖包已安装")
    return True


def run_pytest(test_files=None, verbose=False, coverage=False):
    """运行pytest测试"""
    cmd = ["python", "-m", "pytest"]
    
    if test_files:
        cmd.extend(test_files)
    else:
        cmd.append("tests/")
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=backend", "--cov-report=html", "--cov-report=term"])
    
    # 添加其他有用的选项
    cmd.extend([
        "--tb=short",  # 简短的错误回溯
        "--strict-markers",  # 严格标记模式
        "-x",  # 遇到第一个失败就停止
    ])
    
    print(f"运行命令: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
        return False
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        return False


def run_specific_tests():
    """运行特定类型的测试"""
    test_categories = {
        "auth": "tests/test_auth.py",
        "chat": "tests/test_chat.py", 
        "upload": "tests/test_upload.py",
        "all": None
    }
    
    print("可用的测试类别:")
    for category, file_path in test_categories.items():
        if category == "all":
            print(f"  {category}: 运行所有测试")
        else:
            print(f"  {category}: {file_path}")
    
    while True:
        choice = input("\n请选择要运行的测试类别 (auth/chat/upload/all): ").strip().lower()
        
        if choice in test_categories:
            if choice == "all":
                return run_pytest()
            else:
                return run_pytest([test_categories[choice]], verbose=True)
        else:
            print("❌ 无效选择，请重新输入")


def generate_test_report():
    """生成测试报告"""
    print("\n" + "="*50)
    print("生成详细测试报告...")
    print("="*50)
    
    cmd = [
        "python", "-m", "pytest", 
        "tests/",
        "-v",
        "--tb=long",
        "--cov=backend",
        "--cov-report=html:htmlcov",
        "--cov-report=term-missing",
        "--junit-xml=test_results.xml"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✓ 测试报告已生成:")
        print("  - HTML覆盖率报告: htmlcov/index.html")
        print("  - JUnit XML报告: test_results.xml")
        return True
    except subprocess.CalledProcessError:
        print("❌ 生成测试报告失败")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="后端服务接口测试运行器")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("-c", "--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("-r", "--report", action="store_true", help="生成详细测试报告")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互式选择测试")
    parser.add_argument("--auth", action="store_true", help="只运行认证测试")
    parser.add_argument("--chat", action="store_true", help="只运行聊天测试")
    parser.add_argument("--upload", action="store_true", help="只运行上传测试")
    
    args = parser.parse_args()
    
    print("🚀 后端服务接口测试运行器")
    print("="*50)
    
    # 设置环境
    setup_environment()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 确保测试数据库不存在
    test_db_path = Path("test_database.db")
    if test_db_path.exists():
        test_db_path.unlink()
        print("✓ 清理旧的测试数据库")
    
    success = False
    
    try:
        if args.report:
            success = generate_test_report()
        elif args.interactive:
            success = run_specific_tests()
        elif args.auth:
            success = run_pytest(["tests/test_auth.py"], args.verbose, args.coverage)
        elif args.chat:
            success = run_pytest(["tests/test_chat.py"], args.verbose, args.coverage)
        elif args.upload:
            success = run_pytest(["tests/test_upload.py"], args.verbose, args.coverage)
        else:
            # 默认运行所有测试
            success = run_pytest(verbose=args.verbose, coverage=args.coverage)
        
        print("\n" + "="*50)
        if success:
            print("✅ 所有测试通过!")
        else:
            print("❌ 部分测试失败")
        print("="*50)
        
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
        success = False
    
    finally:
        # 清理测试数据库
        if test_db_path.exists():
            test_db_path.unlink()
            print("✓ 清理测试数据库")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()