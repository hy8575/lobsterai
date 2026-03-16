"""
QQC回测运行脚本
================
检测数据、创建目录、执行回测、生成报告

作者: OpenClaw
日期: 2026-03-16
"""

import os
import sys
from pathlib import Path
from datetime import datetime


def check_data_directory():
    """检测数据目录是否存在"""
    print("=" * 80)
    print("检查数据目录")
    print("=" * 80)
    
    data_paths = ['./data', r'E:\openclaw\data']
    found_path = None
    
    for path in data_paths:
        if os.path.exists(path):
            print(f"✓ 找到数据目录: {path}")
            
            # 检查数据文件
            files = [
                'hs300_constituents.csv',
                'stock_prices.csv',
                'financial_data.csv'
            ]
            
            for file in files:
                file_path = os.path.join(path, file)
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    print(f"  ✓ {file} ({file_size:.2f} MB)")
                else:
                    print(f"  ✗ {file} (不存在)")
            
            found_path = path
            break
    else:
        print("⚠ 未找到数据目录，将使用演示数据")
        print("  如需使用真实数据，请将数据文件放置在以下目录之一：")
        for path in data_paths:
            print(f"    - {path}")
    
    print()
    return found_path


def create_results_directory():
    """创建结果目录"""
    print("=" * 80)
    print("创建结果目录")
    print("=" * 80)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_dir = f'./results/qqc_backtest_{timestamp}'
    
    os.makedirs(results_dir, exist_ok=True)
    print(f"✓ 创建结果目录: {results_dir}")
    print()
    
    return results_dir


def run_backtest(results_dir):
    """执行回测"""
    print("=" * 80)
    print("执行回测")
    print("=" * 80)
    
    try:
        # 导入主脚本
        import qqc_backtest_cursor
        
        # 修改输出目录
        qqc_backtest_cursor.Config.RESULTS_DIR = results_dir
        
        # 执行回测
        results, metrics = qqc_backtest_cursor.main()
        
        print("\n✓ 回测执行成功")
        return results, metrics
        
    except Exception as e:
        print(f"\n✗ 回测执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def generate_summary_report(results_dir, metrics):
    """生成汇总报告"""
    if metrics is None:
        return
    
    print("\n" + "=" * 80)
    print("生成汇总报告")
    print("=" * 80)
    
    report_path = os.path.join(results_dir, 'summary_report.txt')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("QQC沪深300指数增强回测报告\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("回测配置\n")
        f.write("-" * 80 + "\n")
        f.write("回测区间: 2011-01-01 至 2020-12-31\n")
        f.write("调仓频率: 月度\n")
        f.write("交易成本: 单边 0.3%\n")
        f.write("基准指数: 沪深300（市值加权）\n\n")
        
        f.write("因子体系\n")
        f.write("-" * 80 + "\n")
        f.write("QQC六大类因子:\n")
        f.write("  1. 盈利能力: ROE, ROA, 销售净利率\n")
        f.write("  2. 成长能力: 营收增长率, 利润增长率\n")
        f.write("  3. 营运效率: 总资产周转率, 应收账款周转率\n")
        f.write("  4. 盈余质量: 经营现金流/净利润, 应计项目\n")
        f.write("  5. 安全性: 资产负债率, 流动比率\n")
        f.write("  6. 公司治理: 治理代理指标\n\n")
        
        f.write("辅助因子:\n")
        f.write("  - 估值: PE, PB\n")
        f.write("  - 动量: 1月/3月/6月收益率\n")
        f.write("  - 换手率: 20日平均换手\n\n")
        
        f.write("组合约束\n")
        f.write("-" * 80 + "\n")
        f.write("  - QQC因子权重 ≥ 50%\n")
        f.write("  - 行业偏离 ≤ 5%\n")
        f.write("  - 个股偏离 ≤ 1%\n")
        f.write("  - 市值暴露 ≤ 5%\n\n")
        
        f.write("回测结果\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"年化收益率:     {metrics['annual_return']:>8.2%}\n")
        f.write(f"基准年化收益:   {metrics['benchmark_annual_return']:>8.2%}\n")
        f.write(f"年化超额收益:   {metrics['excess_return']:>8.2%}\n")
        f.write(f"跟踪误差:       {metrics['tracking_error']:>8.2%}\n")
        f.write(f"信息比率:       {metrics['information_ratio']:>8.2f}\n")
        f.write(f"最大回撤:       {metrics['max_drawdown']:>8.2%}\n")
        f.write(f"月度胜率:       {metrics['win_rate']:>8.2%}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"✓ 汇总报告已保存: {report_path}")


def generate_plots(results_dir, results):
    """生成图表"""
    if results is None:
        return
    
    print("\n" + "=" * 80)
    print("生成图表")
    print("=" * 80)
    
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # 非交互模式
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False
        
        portfolio_df = results['portfolio']
        benchmark_df = results['benchmark']
        
        # 创建图表
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('QQC沪深300指数增强回测结果', fontsize=16, fontweight='bold')
        
        # 1. 净值曲线
        ax1 = axes[0, 0]
        ax1.plot(portfolio_df['date'], portfolio_df['value'], label='QQC策略', linewidth=2)
        ax1.plot(benchmark_df['date'], benchmark_df['value'], label='沪深300基准', linewidth=2, alpha=0.7)
        ax1.set_title('净值曲线对比')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('净值')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 超额收益
        ax2 = axes[0, 1]
        excess_values = portfolio_df['value'].values / benchmark_df['value'].values
        ax2.plot(portfolio_df['date'], excess_values, label='相对净值', linewidth=2, color='green')
        ax2.axhline(y=1.0, color='red', linestyle='--', alpha=0.5)
        ax2.set_title('相对净值曲线')
        ax2.set_xlabel('日期')
        ax2.set_ylabel('相对净值')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 月度收益分布
        ax3 = axes[1, 0]
        ax3.hist(portfolio_df['return'], bins=30, alpha=0.7, label='策略收益', edgecolor='black')
        ax3.axvline(x=portfolio_df['return'].mean(), color='red', linestyle='--', 
                   label=f'均值: {portfolio_df["return"].mean():.2%}')
        ax3.set_title('月度收益分布')
        ax3.set_xlabel('收益率')
        ax3.set_ylabel('频数')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 滚动信息比率
        ax4 = axes[1, 1]
        excess_returns = portfolio_df['return'].values - benchmark_df['return'].values
        window = 12  # 12个月滚动
        rolling_ir = []
        dates_ir = []
        
        for i in range(window, len(excess_returns)):
            window_returns = excess_returns[i-window:i]
            ir = window_returns.mean() / (window_returns.std() + 1e-6) * (12 ** 0.5)
            rolling_ir.append(ir)
            dates_ir.append(portfolio_df['date'].iloc[i])
        
        ax4.plot(dates_ir, rolling_ir, linewidth=2, color='purple')
        ax4.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax4.set_title('滚动12月信息比率')
        ax4.set_xlabel('日期')
        ax4.set_ylabel('信息比率')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图表
        plot_path = os.path.join(results_dir, 'backtest_results.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ 图表已保存: {plot_path}")
        
    except Exception as e:
        print(f"⚠ 图表生成失败: {e}")


def main():
    """主函数"""
    print("\n")
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + "QQC沪深300指数增强回测系统".center(76) + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)
    print()
    
    # 1. 检查数据目录
    data_path = check_data_directory()
    
    # 2. 创建结果目录
    results_dir = create_results_directory()
    
    # 3. 执行回测
    results, metrics = run_backtest(results_dir)
    
    # 4. 生成报告
    if results is not None:
        generate_summary_report(results_dir, metrics)
        generate_plots(results_dir, results)
    
    # 5. 完成
    print("\n" + "=" * 80)
    print("执行完成")
    print("=" * 80)
    
    if results is not None:
        print(f"\n所有结果已保存到: {results_dir}")
        print("\n输出文件:")
        print("  - summary_report.txt    : 汇总报告")
        print("  - metrics.json          : 绩效指标")
        print("  - portfolio_values.csv  : 策略净值序列")
        print("  - benchmark_values.csv  : 基准净值序列")
        print("  - backtest_results.png  : 回测结果图表")
    else:
        print("\n⚠ 回测未成功完成，请检查错误信息")
    
    print()


if __name__ == '__main__':
    main()
