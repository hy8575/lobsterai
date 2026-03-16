#!/usr/bin/env python3
"""
QQC回测运行脚本
==============
检测数据目录、创建结果目录、执行回测并生成报告

使用方法:
    python run_backtest.py

作者: OpenClaw
日期: 2026-03-16
"""

import os
import sys
import subprocess
from pathlib import Path
import platform


def check_dependencies():
    """检查依赖包"""
    print("检查Python依赖包...")
    
    required_packages = [
        'numpy',
        'pandas',
        'matplotlib',
    ]
    
    optional_packages = [
        'cvxpy',
    ]
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (必需)")
            missing_required.append(package)
    
    for package in optional_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ○ {package} (可选)")
            missing_optional.append(package)
    
    if missing_required:
        print(f"\n错误: 缺少必需的依赖包: {', '.join(missing_required)}")
        print("请运行以下命令安装:")
        print(f"  pip install {' '.join(missing_required)}")
        return False
    
    if missing_optional:
        print(f"\n提示: 缺少可选依赖包: {', '.join(missing_optional)}")
        print("这些包可以提升性能，建议安装:")
        print(f"  pip install {' '.join(missing_optional)}")
    
    return True


def check_data_directories():
    """检查并创建数据目录"""
    print("\n检查数据目录...")
    
    # 可能的数据路径
    possible_paths = [
        './data',
        r'E:\openclaw\data',
        '/workspace/data',
    ]
    
    data_path = None
    
    for path in possible_paths:
        p = Path(path)
        if p.exists():
            data_path = p
            print(f"  ✓ 找到数据目录: {path}")
            break
    
    if data_path is None:
        # 创建默认数据目录
        data_path = Path('./data')
        data_path.mkdir(parents=True, exist_ok=True)
        print(f"  ○ 创建数据目录: {data_path}")
        print("  ! 注意: 数据目录为空，回测将使用模拟数据")
    
    # 列出数据文件
    data_files = list(data_path.glob('*.csv'))
    if data_files:
        print(f"  发现 {len(data_files)} 个数据文件")
    else:
        print("  数据目录为空，将使用模拟数据运行回测")
    
    return data_path


def create_results_directory():
    """创建结果目录"""
    print("\n创建结果目录...")
    
    result_path = Path('./results')
    result_path.mkdir(parents=True, exist_ok=True)
    
    print(f"  ✓ 结果目录: {result_path}")
    
    return result_path


def run_backtest():
    """运行回测脚本"""
    print("\n" + "="*80)
    print("开始执行QQC回测...")
    print("="*80 + "\n")
    
    # 检查回测脚本是否存在
    backtest_script = Path('./qqc_backtest_cursor.py')
    
    if not backtest_script.exists():
        print(f"错误: 找不到回测脚本 {backtest_script}")
        return False
    
    # 执行回测
    try:
        result = subprocess.run(
            [sys.executable, str(backtest_script)],
            check=True,
            text=True,
            capture_output=False
        )
        
        print("\n" + "="*80)
        print("回测执行成功!")
        print("="*80)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n错误: 回测执行失败 (退出码 {e.returncode})")
        return False
    except Exception as e:
        print(f"\n错误: {e}")
        return False


def display_results():
    """显示结果文件"""
    print("\n生成的结果文件:")
    
    result_path = Path('./results')
    
    if not result_path.exists():
        print("  没有找到结果目录")
        return
    
    result_files = [
        'qqc_backtest_report.txt',
        'qqc_backtest_results.png',
        'nav_series.csv',
        'metrics.json'
    ]
    
    for filename in result_files:
        filepath = result_path / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  ✓ {filename} ({size:,} bytes)")
        else:
            print(f"  ✗ {filename} (未生成)")
    
    # 显示报告内容
    report_file = result_path / 'qqc_backtest_report.txt'
    if report_file.exists():
        print("\n" + "="*80)
        print("回测报告预览:")
        print("="*80)
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 显示前50行
            lines = content.split('\n')[:50]
            print('\n'.join(lines))
            if len(content.split('\n')) > 50:
                print("\n... (报告已截断，查看完整报告请打开文件)")


def open_results():
    """尝试打开结果文件"""
    result_path = Path('./results')
    
    # 尝试打开图表
    chart_file = result_path / 'qqc_backtest_results.png'
    
    if chart_file.exists():
        print(f"\n尝试打开结果图表: {chart_file}")
        
        system = platform.system()
        
        try:
            if system == 'Windows':
                os.startfile(str(chart_file))
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', str(chart_file)])
            else:  # Linux
                subprocess.run(['xdg-open', str(chart_file)])
            
            print("  ✓ 图表已打开")
        except Exception as e:
            print(f"  ! 无法自动打开图表: {e}")
            print(f"  请手动打开: {chart_file}")


def main():
    """主函数"""
    print("\n" + "="*80)
    print(" " * 25 + "QQC回测运行脚本")
    print("="*80 + "\n")
    
    # 1. 检查依赖
    if not check_dependencies():
        print("\n请先安装必需的依赖包，然后重新运行此脚本")
        return 1
    
    # 2. 检查数据目录
    data_path = check_data_directories()
    
    # 3. 创建结果目录
    result_path = create_results_directory()
    
    # 4. 运行回测
    success = run_backtest()
    
    if not success:
        print("\n回测执行失败，请检查错误信息")
        return 1
    
    # 5. 显示结果
    display_results()
    
    # 6. 尝试打开结果
    try:
        open_results()
    except:
        pass
    
    print("\n" + "="*80)
    print("所有任务完成!")
    print(f"结果保存在: {result_path.absolute()}")
    print("="*80 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
