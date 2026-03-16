"""
QQC回测执行脚本
====================
检测数据目录、下载数据（可选）、执行回测、生成报告

使用方法:
    python run_backtest.py [--download] [--data-path PATH] [--results-path PATH]

参数:
    --download: 尝试使用akshare下载最新数据
    --data-path: 指定数据目录（默认: ./data）
    --results-path: 指定结果输出目录（默认: ./results）

作者: Cursor AI Agent
日期: 2026-03-16
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import subprocess

def check_dependencies():
    """检查依赖包"""
    required_packages = {
        'numpy': 'numpy',
        'pandas': 'pandas',
        'matplotlib': 'matplotlib',
        'akshare': 'akshare (可选，用于下载数据)',
        'cvxpy': 'cvxpy (可选，用于优化求解)'
    }
    
    missing = []
    optional_missing = []
    
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {description}")
        except ImportError:
            if '可选' in description:
                optional_missing.append(description)
                print(f"⚠ {description} - 未安装（可选）")
            else:
                missing.append(package)
                print(f"✗ {description} - 未安装")
    
    if missing:
        print(f"\n错误: 缺少必需的依赖包: {', '.join(missing)}")
        print("请运行: pip install " + ' '.join(missing))
        return False
    
    if optional_missing:
        print(f"\n提示: 以下可选包未安装，将使用简化功能:")
        for pkg in optional_missing:
            print(f"  - {pkg}")
    
    return True


def check_data_directory(data_path):
    """检查数据目录是否存在"""
    data_path = Path(data_path)
    
    if not data_path.exists():
        print(f"\n数据目录不存在: {data_path}")
        print("正在创建目录...")
        data_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 已创建数据目录: {data_path}")
        return False
    
    print(f"✓ 数据目录存在: {data_path}")
    
    # 检查数据文件
    data_files = list(data_path.glob('*.csv'))
    if data_files:
        print(f"  找到 {len(data_files)} 个数据文件")
        return True
    else:
        print(f"  数据目录为空")
        return False


def download_data_akshare(data_path):
    """使用akshare下载数据"""
    print("\n" + "="*70)
    print("尝试使用akshare下载数据...")
    print("="*70)
    
    try:
        import akshare as ak
        import pandas as pd
        
        data_path = Path(data_path)
        
        # 1. 下载沪深300成分股
        print("\n[1/3] 下载沪深300成分股...")
        try:
            df = ak.index_stock_cons_weight_csindex(symbol="000300")
            if df is not None and len(df) > 0:
                # 提取股票代码
                code_cols = ['成分券代码', 'code', '股票代码', 'symbol']
                stocks = []
                for col in code_cols:
                    if col in df.columns:
                        stocks = df[col].astype(str).str.zfill(6).tolist()
                        break
                
                if stocks:
                    save_df = pd.DataFrame({'code': stocks})
                    save_path = data_path / 'hs300_constituents.csv'
                    save_df.to_csv(save_path, index=False)
                    print(f"  ✓ 已保存 {len(stocks)} 只成分股到: {save_path}")
                else:
                    print("  ✗ 无法提取股票代码")
        except Exception as e:
            print(f"  ✗ 下载成分股失败: {e}")
        
        # 2. 下载沪深300指数数据
        print("\n[2/3] 下载沪深300指数数据...")
        try:
            df = ak.index_zh_a_hist(
                symbol="000300",
                period="daily",
                start_date="20110101",
                end_date="20201231"
            )
            if df is not None and len(df) > 0:
                save_path = data_path / 'index_000300.csv'
                df.to_csv(save_path, index=False)
                print(f"  ✓ 已保存指数数据 {len(df)} 条到: {save_path}")
        except Exception as e:
            print(f"  ✗ 下载指数数据失败: {e}")
        
        # 3. 下载部分个股数据（演示用，下载前10只）
        print("\n[3/3] 下载部分个股数据（前10只用于演示）...")
        constituents_file = data_path / 'hs300_constituents.csv'
        if constituents_file.exists():
            constituents = pd.read_csv(constituents_file)
            stocks = constituents['code'].astype(str).str.zfill(6).tolist()[:10]
            
            for i, stock in enumerate(stocks):
                try:
                    print(f"  下载 {stock} ({i+1}/{len(stocks)})...", end=' ')
                    df = ak.stock_zh_a_hist(
                        symbol=stock,
                        period="daily",
                        start_date="20110101",
                        end_date="20201231",
                        adjust="qfq"
                    )
                    if df is not None and len(df) > 0:
                        save_path = data_path / f'stock_{stock}.csv'
                        df.to_csv(save_path, index=False)
                        print(f"✓ ({len(df)}条)")
                    else:
                        print("✗ 无数据")
                except Exception as e:
                    print(f"✗ {e}")
        
        print("\n" + "="*70)
        print("数据下载完成")
        print("="*70)
        return True
        
    except ImportError:
        print("\n✗ akshare未安装，跳过数据下载")
        print("  如需下载数据，请安装: pip install akshare")
        return False
    except Exception as e:
        print(f"\n✗ 数据下载失败: {e}")
        return False


def create_results_directory(results_path):
    """创建结果目录"""
    results_path = Path(results_path)
    
    if not results_path.exists():
        results_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 已创建结果目录: {results_path}")
    else:
        print(f"✓ 结果目录存在: {results_path}")
    
    return results_path


def run_backtest(data_path, results_path):
    """运行回测"""
    print("\n" + "="*70)
    print("开始运行回测...")
    print("="*70)
    
    # 导入回测模块
    try:
        # 添加当前目录到Python路径
        current_dir = Path(__file__).parent
        sys.path.insert(0, str(current_dir))
        
        # 导入回测模块
        import qqc_backtest_cursor
        
        # 更新配置
        qqc_backtest_cursor.Config.DATA_PATHS = [
            str(data_path),
            "./data",
            "E:\\openclaw\\data"
        ]
        qqc_backtest_cursor.Config.RESULTS_PATH = str(results_path)
        
        # 创建回测引擎
        config = qqc_backtest_cursor.Config()
        engine = qqc_backtest_cursor.BacktestEngine(config)
        
        # 运行回测
        results = engine.run()
        
        if results:
            # 打印结果
            engine.print_results()
            
            # 保存结果
            engine.save_results()
            
            print("\n" + "="*70)
            print("回测完成！")
            print("="*70)
            print(f"结果已保存到: {results_path}")
            
            # 列出结果文件
            result_files = list(Path(results_path).glob('*'))
            if result_files:
                print("\n生成的文件:")
                for file in result_files:
                    print(f"  - {file.name}")
            
            return True
        else:
            print("\n✗ 回测失败，未生成结果")
            return False
            
    except Exception as e:
        print(f"\n✗ 回测执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_report(results_path):
    """生成回测报告（可选）"""
    results_path = Path(results_path)
    
    # 检查结果文件
    nav_file = results_path / 'nav_curve.csv'
    metrics_file = results_path / 'performance_metrics.json'
    
    if not nav_file.exists() or not metrics_file.exists():
        print("\n⚠ 结果文件不完整，跳过报告生成")
        return
    
    try:
        import pandas as pd
        import json
        
        # 读取绩效指标
        with open(metrics_file, 'r', encoding='utf-8') as f:
            metrics = json.load(f)
        
        # 生成Markdown报告
        report_file = results_path / 'backtest_report.md'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# QQC沪深300指数增强策略回测报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 绩效指标\n\n")
            f.write("| 指标 | 数值 |\n")
            f.write("|------|------|\n")
            f.write(f"| 年化收益率 | {metrics.get('annual_return', 0)*100:.2f}% |\n")
            f.write(f"| 基准年化收益 | {metrics.get('benchmark_annual_return', 0)*100:.2f}% |\n")
            f.write(f"| 年化超额收益 | {metrics.get('annual_excess_return', 0)*100:.2f}% |\n")
            f.write(f"| 跟踪误差 | {metrics.get('tracking_error', 0)*100:.2f}% |\n")
            f.write(f"| 信息比率 | {metrics.get('information_ratio', 0):.2f} |\n")
            f.write(f"| 最大回撤 | {metrics.get('max_drawdown', 0)*100:.2f}% |\n")
            f.write(f"| 月度胜率 | {metrics.get('monthly_win_rate', 0)*100:.2f}% |\n")
            f.write(f"| 累计收益 | {metrics.get('total_return', 0)*100:.2f}% |\n")
            f.write(f"| 基准累计收益 | {metrics.get('benchmark_total_return', 0)*100:.2f}% |\n\n")
            
            f.write("## 图表\n\n")
            f.write("![回测结果](backtest_results.png)\n\n")
            
            f.write("## 数据文件\n\n")
            f.write("- `nav_curve.csv`: 净值曲线数据\n")
            f.write("- `performance_metrics.json`: 绩效指标\n")
            f.write("- `backtest_results.png`: 回测结果图表\n")
        
        print(f"\n✓ 报告已生成: {report_file}")
        
    except Exception as e:
        print(f"\n⚠ 报告生成失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='QQC沪深300指数增强策略回测',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 直接运行回测（使用本地数据）
    python run_backtest.py
    
    # 下载数据后运行回测
    python run_backtest.py --download
    
    # 指定数据和结果路径
    python run_backtest.py --data-path ./my_data --results-path ./my_results
        """
    )
    
    parser.add_argument('--download', action='store_true',
                       help='尝试使用akshare下载最新数据')
    parser.add_argument('--data-path', type=str, default='./data',
                       help='数据目录路径（默认: ./data）')
    parser.add_argument('--results-path', type=str, default='./results',
                       help='结果输出目录（默认: ./results）')
    parser.add_argument('--skip-check', action='store_true',
                       help='跳过依赖检查')
    
    args = parser.parse_args()
    
    print("="*70)
    print("QQC沪深300指数增强策略回测系统")
    print("="*70)
    print(f"数据路径: {args.data_path}")
    print(f"结果路径: {args.results_path}")
    print("="*70)
    
    # 1. 检查依赖
    if not args.skip_check:
        print("\n[步骤 1/5] 检查依赖包...")
        if not check_dependencies():
            sys.exit(1)
    
    # 2. 检查数据目录
    print("\n[步骤 2/5] 检查数据目录...")
    has_data = check_data_directory(args.data_path)
    
    # 3. 下载数据（可选）
    if args.download or not has_data:
        print("\n[步骤 3/5] 下载数据...")
        download_data_akshare(args.data_path)
    else:
        print("\n[步骤 3/5] 跳过数据下载（使用本地数据）")
    
    # 4. 创建结果目录
    print("\n[步骤 4/5] 创建结果目录...")
    create_results_directory(args.results_path)
    
    # 5. 运行回测
    print("\n[步骤 5/5] 执行回测...")
    success = run_backtest(args.data_path, args.results_path)
    
    # 6. 生成报告（可选）
    if success:
        print("\n[可选] 生成报告...")
        generate_report(args.results_path)
    
    print("\n" + "="*70)
    if success:
        print("✓ 所有步骤完成！")
    else:
        print("✗ 回测执行失败")
    print("="*70)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
