"""
中金公司研报《量化多因子系列（2）：非线性假设下的情景分析因子模型》复现
Scenario Analysis Factor Model under Non-linear Assumptions
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# =============================================================================
# 第一部分：数据获取和预处理
# =============================================================================

class DataLoader:
    """数据加载器 - 模拟数据生成（实际使用时替换为真实数据源）"""
    
    def __init__(self, start_date: str, end_date: str):
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.trade_dates = self._generate_trade_dates()
        
    def _generate_trade_dates(self) -> pd.DatetimeIndex:
        """生成交易日历（简化版，每月最后一个交易日）"""
        dates = pd.date_range(self.start_date, self.end_date, freq='ME')
        return dates
    
    def load_stock_data(self) -> pd.DataFrame:
        """
        生成模拟股票数据
        实际使用时替换为：聚宽、Tushare、Wind等真实数据源
        """
        np.random.seed(42)
        
        # 生成股票池（模拟A股全市场）
        n_stocks = 800  # 模拟800只股票
        stock_ids = [f'STOCK_{i:04d}' for i in range(n_stocks)]
        
        data_list = []
        
        for date in self.trade_dates:
            for stock_id in stock_ids:
                # 模拟基础数据
                data_list.append({
                    'date': date,
                    'stock_id': stock_id,
                    'close': np.random.lognormal(2, 0.5),
                    'volume': np.random.lognormal(15, 1),
                    'market_cap': np.random.lognormal(22, 1.5),  # 总市值
                    'turnover': np.random.uniform(0.01, 0.3),  # 换手率
                    'pb': np.random.uniform(0.5, 10),  # 市净率
                    'roe_ttm': np.random.normal(0.08, 0.05),  # ROE_TTM
                })
        
        df = pd.DataFrame(data_list)
        df['date'] = pd.to_datetime(df['date'])
        return df
    
    def load_returns(self, stock_data: pd.DataFrame) -> pd.DataFrame:
        """计算月度收益率"""
        df = stock_data.copy()
        df = df.sort_values(['stock_id', 'date'])
        df['next_return'] = df.groupby('stock_id')['close'].pct_change().shift(-1)
        return df


# =============================================================================
# 第二部分：情景特征计算
# =============================================================================

class ScenarioFeatures:
    """情景特征因子计算"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data.copy()
        
    def calculate_size(self) -> pd.Series:
        """
        规模因子 (Size)
        Ln_MC: 总市值对数
        """
        return np.log(self.data['market_cap'])
    
    def calculate_liquidity(self, lookback_months: List[int] = [1, 3, 6]) -> pd.Series:
        """
        流动性因子 (Liquidity)
        VSTD = 成交额 / 收益率波动
        多期等权平均
        """
        # 模拟计算（实际应使用历史数据计算）
        liquidity_scores = []
        for months in lookback_months:
            # 模拟VSTD计算
            vstd = self.data['volume'] / (self.data['turnover'] + 0.001)
            liquidity_scores.append(vstd)
        
        # 等权平均
        return pd.concat(liquidity_scores, axis=1).mean(axis=1)
    
    def calculate_cheapness(self) -> pd.Series:
        """
        估值因子 (Cheapness)
        BP_LR: 市净率倒数（账面市值比）
        """
        return 1.0 / self.data['pb']
    
    def calculate_profit(self) -> pd.Series:
        """
        盈利因子 (Profit)
        过去三年ROE_TTM均值
        """
        # 模拟三年均值（实际应使用历史数据）
        return self.data['roe_ttm']
    
    def calculate_growth(self) -> pd.Series:
        """
        成长因子 (Growth)
        OP_SD与NP_SD等权（8个季度数据）
        营业利润增长率标准差与净利润增长率标准差
        """
        # 模拟计算（实际应使用8个季度数据计算增长率标准差）
        op_sd = np.abs(np.random.normal(0, 0.1, len(self.data)))
        np_sd = np.abs(np.random.normal(0, 0.1, len(self.data)))
        return (op_sd + np_sd) / 2
    
    def get_all_scenario_features(self) -> pd.DataFrame:
        """获取所有情景特征"""
        features = pd.DataFrame({
            'date': self.data['date'],
            'stock_id': self.data['stock_id'],
            'Size': self.calculate_size(),
            'Liquidity': self.calculate_liquidity(),
            'Cheapness': self.calculate_cheapness(),
            'Profit': self.calculate_profit(),
            'Growth': self.calculate_growth(),
            'next_return': self.data['next_return']
        })
        return features


# =============================================================================
# 第三部分：Alpha因子计算
# =============================================================================

class AlphaFactors:
    """Alpha因子计算"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data.copy()
    
    def calculate_quality(self) -> pd.Series:
        """
        质量因子 (Quality)
        综合盈利稳定性、财务健康度等
        """
        # 模拟质量评分
        return np.random.normal(0, 1, len(self.data))
    
    def calculate_con_value(self) -> pd.Series:
        """
        预期估值因子 (Con_Value)
        基于一致预期的估值指标
        """
        return np.random.normal(0, 1, len(self.data))
    
    def calculate_con_change(self) -> pd.Series:
        """
        预期调整因子 (Con_Change)
        一致预期的变化
        """
        return np.random.normal(0, 1, len(self.data))
    
    def calculate_momentum(self) -> pd.Series:
        """
        动量因子 (Momentum)
        过去12个月收益率（剔除最近1个月）
        """
        return np.random.normal(0, 1, len(self.data))
    
    def calculate_turnover(self) -> pd.Series:
        """
        换手率因子 (Turnover)
        换手率相关指标
        """
        return -self.data['turnover']  # 负向因子
    
    def get_all_alpha_factors(self) -> pd.DataFrame:
        """获取所有Alpha因子"""
        factors = pd.DataFrame({
            'date': self.data['date'],
            'stock_id': self.data['stock_id'],
            'Quality': self.calculate_quality(),
            'Con_Value': self.calculate_con_value(),
            'Con_Change': self.calculate_con_change(),
            'Momentum': self.calculate_momentum(),
            'Turnover': self.calculate_turnover()
        })
        return factors


# =============================================================================
# 第四部分：分组IC分析
# =============================================================================

class GroupICAnalyzer:
    """分组IC分析器"""
    
    def __init__(self, scenario_features: pd.DataFrame, alpha_factors: pd.DataFrame):
        self.scenario = scenario_features
        self.alpha = alpha_factors
        self.scenario_names = ['Size', 'Liquidity', 'Cheapness', 'Profit', 'Growth']
        self.alpha_names = ['Quality', 'Con_Value', 'Con_Change', 'Momentum', 'Turnover']
        
    def group_by_median(self, date: pd.Timestamp, scenario: str) -> Tuple[pd.Series, pd.Series]:
        """
        按情景特征中位数分组
        返回: (high_group_mask, low_group_mask)
        """
        date_data = self.scenario[self.scenario['date'] == date]
        if len(date_data) == 0:
            return None, None
        
        median_val = date_data[scenario].median()
        high_mask = date_data[scenario] >= median_val
        low_mask = date_data[scenario] < median_val
        
        return high_mask, low_mask
    
    def calculate_ic(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算IC（信息系数，Spearman秩相关）"""
        if len(factor_values) < 10:
            return np.nan
        return factor_values.corr(returns, method='spearman')
    
    def calculate_group_ics(self, date: pd.Timestamp) -> Dict[str, Dict[str, float]]:
        """
        计算某日期各情景分组下的Alpha因子IC
        返回: {scenario: {alpha_factor: ic, 'group': 'high'/'low'}}
        """
        results = {}
        
        # 合并数据
        merged = pd.merge(
            self.scenario[self.scenario['date'] == date],
            self.alpha[self.alpha['date'] == date],
            on=['date', 'stock_id']
        )
        
        if len(merged) == 0:
            return results
        
        for scenario in self.scenario_names:
            results[scenario] = {'high': {}, 'low': {}}
            
            median_val = merged[scenario].median()
            high_mask = merged[scenario] >= median_val
            low_mask = merged[scenario] < median_val
            
            for alpha in self.alpha_names:
                # High组IC
                if high_mask.sum() > 5:
                    ic_high = self.calculate_ic(
                        merged.loc[high_mask, alpha],
                        merged.loc[high_mask, 'next_return']
                    )
                    results[scenario]['high'][alpha] = ic_high
                
                # Low组IC
                if low_mask.sum() > 5:
                    ic_low = self.calculate_ic(
                        merged.loc[low_mask, alpha],
                        merged.loc[low_mask, 'next_return']
                    )
                    results[scenario]['low'][alpha] = ic_low
        
        return results


# =============================================================================
# 第五部分：最优化IR权重计算
# =============================================================================

class IROptimizer:
    """IR最优化权重计算器"""
    
    def __init__(self, lookback_months: int = 12):
        self.lookback = lookback_months
        
    def calculate_ic_mean_cov(self, ic_series: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算IC均值向量和协方差矩阵
        ic_series: DataFrame with columns = alpha_factors, rows = dates
        """
        # 清理数据
        ic_clean = ic_series.dropna()
        if len(ic_clean) < 6:
            return None, None
        
        ic_mean = ic_clean.mean().values.copy()
        ic_cov = ic_clean.cov().values.copy()
        
        # 正则化协方差矩阵
        ic_cov += np.eye(len(ic_cov)) * 0.01
        
        return ic_mean, ic_cov
    
    def optimize_weights(self, ic_mean: np.ndarray, ic_cov: np.ndarray) -> np.ndarray:
        """
        最优化IR权重: v ∝ Σ_IC^(-1) · IC̄
        """
        try:
            inv_cov = np.linalg.inv(ic_cov)
            raw_weights = inv_cov @ ic_mean
            
            # 归一化权重
            weights = raw_weights / np.sum(np.abs(raw_weights))
            return weights
        except:
            # 失败时使用等权
            n = len(ic_mean)
            return np.ones(n) / n
    
    def get_optimal_weights(self, ic_history: pd.DataFrame) -> np.ndarray:
        """基于历史IC获取最优权重"""
        ic_mean, ic_cov = self.calculate_ic_mean_cov(ic_history)
        if ic_mean is None:
            n = len(ic_history.columns)
            return np.ones(n) / n
        return self.optimize_weights(ic_mean, ic_cov)


# =============================================================================
# 第六部分：回测引擎
# =============================================================================

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, 
                 scenario_features: pd.DataFrame,
                 alpha_factors: pd.DataFrame,
                 n_holdings: int = 200,
                 fee_rate: float = 0.002,
                 rebalance_freq: str = 'M'):
        self.scenario = scenario_features
        self.alpha = alpha_factors
        self.n_holdings = n_holdings
        self.fee_rate = fee_rate
        self.rebalance_freq = rebalance_freq
        
        self.dates = sorted(self.scenario['date'].unique())
        self.group_analyzer = GroupICAnalyzer(scenario_features, alpha_factors)
        self.optimizer = IROptimizer(lookback_months=12)
        
        # 存储结果
        self.portfolio_returns = []
        self.ic_history = []
        self.weights_history = []
        
    def calculate_composite_score(self, 
                                   alpha_data: pd.DataFrame,
                                   weights: np.ndarray) -> pd.Series:
        """计算Alpha因子复合得分"""
        alpha_cols = ['Quality', 'Con_Value', 'Con_Change', 'Momentum', 'Turnover']
        scores = alpha_data[alpha_cols].values @ weights
        return pd.Series(scores, index=alpha_data.index)
    
    def run_backtest(self) -> pd.DataFrame:
        """运行回测"""
        print("开始回测...")
        
        # 存储IC历史
        ic_records = []
        
        for i, date in enumerate(self.dates):
            if i < 12:  # 前12个月用于计算初始权重
                continue
            
            # 计算当日各组IC
            group_ics = self.group_analyzer.calculate_group_ics(date)
            
            # 简化：使用全市场IC（实际应分情景优化）
            merged = pd.merge(
                self.scenario[self.scenario['date'] == date],
                self.alpha[self.alpha['date'] == date],
                on=['date', 'stock_id']
            )
            
            if len(merged) == 0:
                continue
            
            # 计算各Alpha因子IC
            ic_row = {'date': date}
            for alpha in ['Quality', 'Con_Value', 'Con_Change', 'Momentum', 'Turnover']:
                ic = self.group_analyzer.calculate_ic(
                    merged[alpha], merged['next_return']
                )
                ic_row[alpha] = ic
            ic_records.append(ic_row)
            
            # 滚动12个月优化权重
            if len(ic_records) >= 12:
                ic_df = pd.DataFrame(ic_records[-12:]).set_index('date')
                weights = self.optimizer.get_optimal_weights(ic_df)
            else:
                weights = np.ones(5) / 5
            
            self.weights_history.append({
                'date': date,
                'Quality': weights[0],
                'Con_Value': weights[1],
                'Con_Change': weights[2],
                'Momentum': weights[3],
                'Turnover': weights[4]
            })
            
            # 计算复合得分并选股
            merged['score'] = self.calculate_composite_score(merged, weights)
            top_stocks = merged.nlargest(self.n_holdings, 'score')
            
            # 计算组合收益
            if 'next_return' in top_stocks.columns:
                portfolio_return = top_stocks['next_return'].mean()
                # 扣除交易费用
                portfolio_return -= self.fee_rate
                
                self.portfolio_returns.append({
                    'date': date,
                    'return': portfolio_return,
                    'n_stocks': len(top_stocks)
                })
            
            if i % 12 == 0:
                print(f"  处理到: {date.strftime('%Y-%m')}, 累计收益: {sum([r['return'] for r in self.portfolio_returns]):.2%}")
        
        print("回测完成!")
        return pd.DataFrame(self.portfolio_returns)


# =============================================================================
# 第七部分：绩效分析
# =============================================================================

class PerformanceAnalyzer:
    """绩效分析器"""
    
    def __init__(self, returns_df: pd.DataFrame):
        self.returns = returns_df.copy()
        if 'date' in self.returns.columns:
            self.returns['date'] = pd.to_datetime(self.returns['date'])
            self.returns = self.returns.set_index('date')
    
    def calculate_cumulative_return(self) -> pd.Series:
        """计算累计收益"""
        return (1 + self.returns['return']).cumprod() - 1
    
    def calculate_annual_return(self) -> float:
        """计算年化收益"""
        total_return = (1 + self.returns['return']).prod() - 1
        n_years = len(self.returns) / 12
        return (1 + total_return) ** (1 / n_years) - 1
    
    def calculate_volatility(self) -> float:
        """计算年化波动率"""
        return self.returns['return'].std() * np.sqrt(12)
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.03) -> float:
        """计算夏普比率"""
        excess_return = self.calculate_annual_return() - risk_free_rate
        return excess_return / self.calculate_volatility()
    
    def calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        cumulative = self.calculate_cumulative_return()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / (1 + running_max)
        return drawdown.min()
    
    def calculate_win_rate(self) -> float:
        """计算胜率"""
        return (self.returns['return'] > 0).mean()
    
    def get_summary(self) -> Dict[str, float]:
        """获取绩效摘要"""
        return {
            '年化收益率': self.calculate_annual_return(),
            '年化波动率': self.calculate_volatility(),
            '夏普比率': self.calculate_sharpe_ratio(),
            '最大回撤': self.calculate_max_drawdown(),
            '胜率': self.calculate_win_rate(),
            '总收益率': (1 + self.returns['return']).prod() - 1
        }
    
    def print_report(self):
        """打印绩效报告"""
        summary = self.get_summary()
        print("\n" + "="*50)
        print("绩效分析报告")
        print("="*50)
        for key, value in summary.items():
            if key in ['年化收益率', '年化波动率', '最大回撤', '胜率', '总收益率']:
                print(f"{key}: {value:.2%}")
            else:
                print(f"{key}: {value:.2f}")
        print("="*50)


# =============================================================================
# 第八部分：可视化
# =============================================================================

class Visualizer:
    """可视化工具"""
    
    def __init__(self, output_dir: str = './cursor_opus_results'):
        self.output_dir = output_dir
        import os
        os.makedirs(output_dir, exist_ok=True)
    
    def plot_cumulative_return(self, returns_df: pd.DataFrame, filename: str = 'cumulative_return.png'):
        """绘制累计收益曲线"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        returns_df['date'] = pd.to_datetime(returns_df['date'])
        returns_df = returns_df.set_index('date')
        cumulative = (1 + returns_df['return']).cumprod()
        
        ax.plot(cumulative.index, cumulative.values, linewidth=2, label='策略累计收益')
        ax.axhline(y=1, color='r', linestyle='--', alpha=0.5, label='基准线')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('累计净值', fontsize=12)
        ax.set_title('情景分析因子模型 - 累计收益曲线', fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/{filename}', dpi=150)
        print(f"保存图表: {self.output_dir}/{filename}")
        plt.close()
    
    def plot_weights_evolution(self, weights_history: List[Dict], filename: str = 'weights_evolution.png'):
        """绘制权重变化"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        weights_df = pd.DataFrame(weights_history)
        weights_df['date'] = pd.to_datetime(weights_df['date'])
        weights_df = weights_df.set_index('date')
        
        for col in ['Quality', 'Con_Value', 'Con_Change', 'Momentum', 'Turnover']:
            ax.plot(weights_df.index, weights_df[col], label=col, linewidth=1.5)
        
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('权重', fontsize=12)
        ax.set_title('Alpha因子权重变化', fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/{filename}', dpi=150)
        print(f"保存图表: {self.output_dir}/{filename}")
        plt.close()
    
    def plot_monthly_returns(self, returns_df: pd.DataFrame, filename: str = 'monthly_returns.png'):
        """绘制月度收益分布"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        returns_df['date'] = pd.to_datetime(returns_df['date'])
        colors = ['green' if r > 0 else 'red' for r in returns_df['return']]
        
        ax.bar(range(len(returns_df)), returns_df['return'] * 100, color=colors, alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('收益率 (%)', fontsize=12)
        ax.set_title('月度收益分布', fontsize=14)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/{filename}', dpi=150)
        print(f"保存图表: {self.output_dir}/{filename}")
        plt.close()
    
    def plot_drawdown(self, returns_df: pd.DataFrame, filename: str = 'drawdown.png'):
        """绘制回撤曲线"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        returns_df['date'] = pd.to_datetime(returns_df['date'])
        returns_df = returns_df.set_index('date')
        cumulative = (1 + returns_df['return']).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max * 100
        
        ax.fill_between(drawdown.index, drawdown.values, 0, color='red', alpha=0.3)
        ax.plot(drawdown.index, drawdown.values, color='red', linewidth=1)
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('回撤 (%)', fontsize=12)
        ax.set_title('最大回撤分析', fontsize=14)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/{filename}', dpi=150)
        print(f"保存图表: {self.output_dir}/{filename}")
        plt.close()


# =============================================================================
# 主程序
# =============================================================================

def main():
    """主函数"""
    print("="*60)
    print("中金公司研报复现：非线性假设下的情景分析因子模型")
    print("="*60)
    
    # 1. 数据加载
    print("\n[1/8] 加载数据...")
    loader = DataLoader('2011-01-01', '2021-01-31')
    stock_data = loader.load_stock_data()
    stock_data = loader.load_returns(stock_data)
    print(f"  数据范围: {stock_data['date'].min()} 至 {stock_data['date'].max()}")
    print(f"  股票数量: {stock_data['stock_id'].nunique()}")
    print(f"  记录数量: {len(stock_data)}")
    
    # 2. 情景特征计算
    print("\n[2/8] 计算情景特征因子...")
    scenario_calc = ScenarioFeatures(stock_data)
    scenario_features = scenario_calc.get_all_scenario_features()
    print(f"  情景特征: Size, Liquidity, Cheapness, Profit, Growth")
    print(f"  特征数量: {len(scenario_features)}")
    
    # 3. Alpha因子计算
    print("\n[3/8] 计算Alpha因子...")
    alpha_calc = AlphaFactors(stock_data)
    alpha_factors = alpha_calc.get_all_alpha_factors()
    print(f"  Alpha因子: Quality, Con_Value, Con_Change, Momentum, Turnover")
    print(f"  因子数量: {len(alpha_factors)}")
    
    # 4. 分组IC分析
    print("\n[4/8] 分组IC分析...")
    group_analyzer = GroupICAnalyzer(scenario_features, alpha_factors)
    sample_date = scenario_features['date'].unique()[15]
    group_ics = group_analyzer.calculate_group_ics(sample_date)
    print(f"  示例日期: {sample_date}")
    print(f"  分组数: 5个情景 × 2组 = 10组")
    
    # 5. 回测引擎
    print("\n[5/8] 运行回测...")
    engine = BacktestEngine(
        scenario_features=scenario_features,
        alpha_factors=alpha_factors,
        n_holdings=200,
        fee_rate=0.002
    )
    returns_df = engine.run_backtest()
    print(f"  回测月份: {len(returns_df)}")
    
    # 6. 绩效分析
    print("\n[6/8] 绩效分析...")
    analyzer = PerformanceAnalyzer(returns_df)
    analyzer.print_report()
    
    # 7. 可视化
    print("\n[7/8] 生成可视化图表...")
    visualizer = Visualizer(output_dir='/home/node/.openclaw/workspace/cursor_opus_results')
    visualizer.plot_cumulative_return(returns_df)
    visualizer.plot_weights_evolution(engine.weights_history)
    visualizer.plot_monthly_returns(returns_df)
    visualizer.plot_drawdown(returns_df)
    
    # 8. 保存结果
    print("\n[8/8] 保存结果...")
    returns_df.to_csv('/home/node/.openclaw/workspace/cursor_opus_results/returns.csv', index=False)
    pd.DataFrame(engine.weights_history).to_csv('/home/node/.openclaw/workspace/cursor_opus_results/weights.csv', index=False)
    
    summary = analyzer.get_summary()
    with open('/home/node/.openclaw/workspace/cursor_opus_results/summary.txt', 'w') as f:
        f.write("中金公司研报复现 - 情景分析因子模型\n")
        f.write("="*50 + "\n")
        for key, value in summary.items():
            if key in ['年化收益率', '年化波动率', '最大回撤', '胜率', '总收益率']:
                f.write(f"{key}: {value:.2%}\n")
            else:
                f.write(f"{key}: {value:.2f}\n")
    
    print("\n" + "="*60)
    print("回测完成！结果已保存到 cursor_opus_results/ 目录")
    print("="*60)
    
    return returns_df, engine.weights_history, analyzer


if __name__ == '__main__':
    returns_df, weights_history, analyzer = main()
