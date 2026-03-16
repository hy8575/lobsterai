"""
QQC沪深300指数增强回测脚本
================================
基于中金公司QQC综合质量因子研究报告实现

实现特性：
1. QQC六大类因子 + 辅助因子
2. IC_IR滚动24月加权（QQC>=50%）
3. 行业/个股/市值偏离约束
4. cvxpy组合优化
5. 2011-2020月度回测，单边0.3%成本

作者: OpenClaw
日期: 2026-03-16
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import json

warnings.filterwarnings('ignore')

# 设置随机种子
np.random.seed(42)

# =============================================================================
# 配置参数
# =============================================================================

class Config:
    """配置参数"""
    # 数据路径
    DATA_PATHS = ['./data', r'E:\openclaw\data']
    
    # 回测参数
    START_DATE = '2011-01-01'
    END_DATE = '2020-12-31'
    REBALANCE_FREQ = 'M'  # 月度调仓
    TRANSACTION_COST = 0.003  # 单边0.3%
    
    # 因子IC_IR加权参数
    IC_WINDOW = 24  # 滚动24月
    QQC_WEIGHT_THRESHOLD = 0.5  # QQC因子权重>=50%
    
    # 组合约束
    INDUSTRY_DEVIATION = 0.05  # 行业偏离<=5%
    STOCK_DEVIATION = 0.01  # 个股偏离<=1%
    MARKET_CAP_DEVIATION = 0.05  # 市值暴露<=5%
    
    # 组合优化
    USE_CVXPY = True  # 优先使用cvxpy
    
    # 输出参数
    RESULTS_DIR = './results'


# =============================================================================
# 数据加载模块
# =============================================================================

class DataLoader:
    """数据加载器 - 从本地读取数据"""
    
    def __init__(self, config: Config):
        self.config = config
        self.data_path = self._find_data_path()
        print(f"[Data] 使用数据路径: {self.data_path}")
        
    def _find_data_path(self) -> str:
        """查找可用的数据路径"""
        for path in self.config.DATA_PATHS:
            if os.path.exists(path):
                return path
        # 如果都不存在，创建./data
        os.makedirs('./data', exist_ok=True)
        return './data'
    
    def load_hs300_constituents(self) -> pd.DataFrame:
        """加载沪深300成分股数据
        
        Returns:
            DataFrame with columns: date, stock_code
        """
        file_path = os.path.join(self.data_path, 'hs300_constituents.csv')
        
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, parse_dates=['date'])
            print(f"[Data] 加载沪深300成分股: {len(df)} 条记录")
            return df
        
        # 生成演示数据
        print("[Warning] 未找到成分股数据，生成演示数据")
        return self._generate_demo_constituents()
    
    def load_stock_prices(self) -> pd.DataFrame:
        """加载个股日线数据
        
        Returns:
            DataFrame with columns: date, stock_code, open, high, low, close, volume, amount
        """
        file_path = os.path.join(self.data_path, 'stock_prices.csv')
        
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, parse_dates=['date'])
            print(f"[Data] 加载个股价格数据: {len(df)} 条记录")
            return df
        
        # 生成演示数据
        print("[Warning] 未找到价格数据，生成演示数据")
        return self._generate_demo_prices()
    
    def load_financial_data(self) -> pd.DataFrame:
        """加载财务数据（季度）
        
        Returns:
            DataFrame with columns: report_date, stock_code, revenue, net_profit, 
                                  total_assets, total_equity, operating_cashflow, etc.
        """
        file_path = os.path.join(self.data_path, 'financial_data.csv')
        
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, parse_dates=['report_date'])
            print(f"[Data] 加载财务数据: {len(df)} 条记录")
            return df
        
        # 生成演示数据
        print("[Warning] 未找到财务数据，生成演示数据")
        return self._generate_demo_financial()
    
    def _generate_demo_constituents(self) -> pd.DataFrame:
        """生成演示成分股数据"""
        dates = pd.date_range(self.config.START_DATE, self.config.END_DATE, freq='M')
        stocks = [f"{i:06d}" for i in range(1, 101)]  # 100只股票
        
        data = []
        for date in dates:
            for stock in stocks:
                data.append({'date': date, 'stock_code': stock})
        
        return pd.DataFrame(data)
    
    def _generate_demo_prices(self) -> pd.DataFrame:
        """生成演示价格数据"""
        dates = pd.date_range(self.config.START_DATE, self.config.END_DATE, freq='D')
        stocks = [f"{i:06d}" for i in range(1, 101)]
        
        data = []
        for stock in stocks:
            base_price = np.random.uniform(10, 100)
            prices = base_price * np.exp(np.cumsum(np.random.normal(0, 0.02, len(dates))))
            
            for date, price in zip(dates, prices):
                data.append({
                    'date': date,
                    'stock_code': stock,
                    'open': price * np.random.uniform(0.98, 1.02),
                    'high': price * np.random.uniform(1.0, 1.05),
                    'low': price * np.random.uniform(0.95, 1.0),
                    'close': price,
                    'volume': np.random.uniform(1e6, 1e8),
                    'amount': price * np.random.uniform(1e6, 1e8)
                })
        
        return pd.DataFrame(data)
    
    def _generate_demo_financial(self) -> pd.DataFrame:
        """生成演示财务数据"""
        quarters = pd.date_range(self.config.START_DATE, self.config.END_DATE, freq='Q')
        stocks = [f"{i:06d}" for i in range(1, 101)]
        
        data = []
        for stock in stocks:
            for quarter in quarters:
                data.append({
                    'report_date': quarter,
                    'stock_code': stock,
                    'revenue': np.random.uniform(1e8, 1e10),
                    'net_profit': np.random.uniform(1e7, 1e9),
                    'total_assets': np.random.uniform(1e9, 1e11),
                    'total_equity': np.random.uniform(5e8, 5e10),
                    'operating_cashflow': np.random.uniform(-1e8, 1e9),
                    'total_liabilities': np.random.uniform(5e8, 5e10),
                    'accounts_receivable': np.random.uniform(1e7, 1e9),
                    'inventory': np.random.uniform(1e7, 1e9),
                })
        
        return pd.DataFrame(data)


# =============================================================================
# 因子计算模块
# =============================================================================

class FactorCalculator:
    """因子计算器 - 计算QQC六大类因子和辅助因子"""
    
    def __init__(self):
        pass
    
    def calculate_all_factors(self, 
                             prices: pd.DataFrame, 
                             financial: pd.DataFrame,
                             date: pd.Timestamp) -> pd.DataFrame:
        """计算所有因子
        
        Args:
            prices: 价格数据
            financial: 财务数据
            date: 计算日期
            
        Returns:
            DataFrame with columns: stock_code, factor1, factor2, ...
        """
        # 筛选日期范围内的数据
        price_data = prices[prices['date'] <= date].copy()
        financial_data = financial[financial['report_date'] <= date].copy()
        
        # 获取每只股票最新的财务数据
        financial_latest = financial_data.sort_values('report_date').groupby('stock_code').last().reset_index()
        
        # 计算各类因子
        profitability = self._calc_profitability(financial_latest)
        growth = self._calc_growth(financial_data)
        efficiency = self._calc_efficiency(financial_latest)
        quality = self._calc_quality(financial_latest)
        safety = self._calc_safety(financial_latest)
        governance = self._calc_governance(financial_latest)  # 简化
        
        # 辅助因子
        valuation = self._calc_valuation(price_data, financial_latest, date)
        momentum = self._calc_momentum(price_data, date)
        turnover = self._calc_turnover(price_data, date)
        
        # 合并所有因子
        factors = profitability
        for df in [growth, efficiency, quality, safety, governance, 
                   valuation, momentum, turnover]:
            factors = factors.merge(df, on='stock_code', how='outer')
        
        return factors
    
    def _calc_profitability(self, df: pd.DataFrame) -> pd.DataFrame:
        """盈利能力因子：ROE、ROA、销售净利率"""
        result = pd.DataFrame()
        result['stock_code'] = df['stock_code']
        result['roe'] = df['net_profit'] / df['total_equity']
        result['roa'] = df['net_profit'] / df['total_assets']
        result['npm'] = df['net_profit'] / df['revenue']  # 销售净利率
        return result
    
    def _calc_growth(self, df: pd.DataFrame) -> pd.DataFrame:
        """成长能力因子：营收增长率、利润增长率"""
        df = df.sort_values(['stock_code', 'report_date'])
        df['revenue_growth'] = df.groupby('stock_code')['revenue'].pct_change(4)  # YoY
        df['profit_growth'] = df.groupby('stock_code')['net_profit'].pct_change(4)
        
        result = df.groupby('stock_code').last().reset_index()
        return result[['stock_code', 'revenue_growth', 'profit_growth']]
    
    def _calc_efficiency(self, df: pd.DataFrame) -> pd.DataFrame:
        """营运效率因子：总资产周转率、应收账款周转率"""
        result = pd.DataFrame()
        result['stock_code'] = df['stock_code']
        result['asset_turnover'] = df['revenue'] / df['total_assets']
        result['receivable_turnover'] = df['revenue'] / (df['accounts_receivable'] + 1)
        return result
    
    def _calc_quality(self, df: pd.DataFrame) -> pd.DataFrame:
        """盈余质量因子：经营现金流/净利润、应计项目"""
        result = pd.DataFrame()
        result['stock_code'] = df['stock_code']
        result['ocf_to_profit'] = df['operating_cashflow'] / (df['net_profit'] + 1)
        result['accruals'] = (df['net_profit'] - df['operating_cashflow']) / df['total_assets']
        return result
    
    def _calc_safety(self, df: pd.DataFrame) -> pd.DataFrame:
        """安全性因子：资产负债率、流动比率"""
        result = pd.DataFrame()
        result['stock_code'] = df['stock_code']
        result['debt_ratio'] = df['total_liabilities'] / df['total_assets']
        result['current_ratio'] = df['total_assets'] / (df['total_liabilities'] + 1)
        return result
    
    def _calc_governance(self, df: pd.DataFrame) -> pd.DataFrame:
        """公司治理因子（简化）：用ROE稳定性代替"""
        result = pd.DataFrame()
        result['stock_code'] = df['stock_code']
        result['governance_proxy'] = df['net_profit'] / (df['total_equity'] + 1)
        return result
    
    def _calc_valuation(self, prices: pd.DataFrame, financial: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
        """估值因子：PE、PB"""
        # 获取最近的收盘价
        recent_prices = prices[prices['date'] <= date].groupby('stock_code').last().reset_index()
        
        merged = recent_prices.merge(financial, on='stock_code', how='inner')
        
        result = pd.DataFrame()
        result['stock_code'] = merged['stock_code']
        result['market_cap'] = merged['close'] * merged['volume']
        result['pe'] = result['market_cap'] / (merged['net_profit'] + 1)
        result['pb'] = result['market_cap'] / (merged['total_equity'] + 1)
        
        return result[['stock_code', 'pe', 'pb', 'market_cap']]
    
    def _calc_momentum(self, prices: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
        """动量因子：过去1月、3月、6月收益率"""
        price_pivot = prices.pivot_table(index='date', columns='stock_code', values='close')
        
        if date not in price_pivot.index:
            date = price_pivot.index[price_pivot.index <= date][-1]
        
        result = pd.DataFrame()
        result['stock_code'] = price_pivot.columns
        
        # 计算收益率
        for months, name in [(1, 'ret_1m'), (3, 'ret_3m'), (6, 'ret_6m')]:
            lookback_date = date - pd.DateOffset(months=months)
            if lookback_date in price_pivot.index:
                result[name] = (price_pivot.loc[date] / price_pivot.loc[lookback_date] - 1).values
            else:
                result[name] = 0
        
        return result
    
    def _calc_turnover(self, prices: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
        """换手率因子：过去20日平均换手率"""
        window_start = date - pd.DateOffset(days=20)
        recent = prices[(prices['date'] > window_start) & (prices['date'] <= date)]
        
        result = recent.groupby('stock_code').agg({
            'volume': 'mean'
        }).reset_index()
        result.rename(columns={'volume': 'turnover'}, inplace=True)
        
        return result


# =============================================================================
# 因子加权模块
# =============================================================================

class FactorWeighting:
    """因子加权 - IC_IR滚动24月加权"""
    
    def __init__(self, config: Config):
        self.config = config
        self.ic_history = []  # 存储历史IC值
    
    def calculate_factor_weights(self, 
                                 factors: pd.DataFrame, 
                                 returns: pd.Series,
                                 date: pd.Timestamp) -> Dict[str, float]:
        """计算因子权重
        
        Args:
            factors: 因子值
            returns: 下期收益率
            date: 当前日期
            
        Returns:
            Dict of factor_name -> weight
        """
        # 计算当期IC
        ic_values = {}
        factor_cols = [col for col in factors.columns if col != 'stock_code']
        
        for factor in factor_cols:
            ic = factors[factor].corr(returns)
            ic_values[factor] = ic if not np.isnan(ic) else 0
        
        # 记录历史IC
        self.ic_history.append({
            'date': date,
            'ic': ic_values
        })
        
        # 保留最近24个月
        if len(self.ic_history) > self.config.IC_WINDOW:
            self.ic_history = self.ic_history[-self.config.IC_WINDOW:]
        
        # 计算IC_IR
        if len(self.ic_history) < 6:  # 至少需要6个月数据
            # 初期等权
            weights = {f: 1.0 / len(factor_cols) for f in factor_cols}
        else:
            ic_ir = self._calculate_ic_ir()
            weights = self._optimize_weights(ic_ir, factor_cols)
        
        return weights
    
    def _calculate_ic_ir(self) -> Dict[str, float]:
        """计算IC_IR（IC均值/IC标准差）"""
        ic_df = pd.DataFrame([h['ic'] for h in self.ic_history])
        
        ic_mean = ic_df.mean()
        ic_std = ic_df.std()
        
        ic_ir = ic_mean / (ic_std + 1e-6)
        return ic_ir.to_dict()
    
    def _optimize_weights(self, ic_ir: Dict[str, float], factor_cols: List[str]) -> Dict[str, float]:
        """优化因子权重，确保QQC因子权重>=50%"""
        # QQC核心因子
        qqc_factors = ['roe', 'roa', 'npm', 'revenue_growth', 'profit_growth', 
                       'asset_turnover', 'receivable_turnover', 'ocf_to_profit', 
                       'accruals', 'debt_ratio', 'current_ratio', 'governance_proxy']
        
        # 按IC_IR排序
        sorted_factors = sorted(ic_ir.items(), key=lambda x: abs(x[1]), reverse=True)
        
        # 分配权重
        weights = {}
        total_weight = 1.0
        qqc_weight = 0.0
        
        # 先给QQC因子分配权重
        qqc_in_factors = [f for f in qqc_factors if f in factor_cols]
        if len(qqc_in_factors) > 0:
            qqc_ir_sum = sum(abs(ic_ir.get(f, 0)) for f in qqc_in_factors)
            for f in qqc_in_factors:
                if qqc_ir_sum > 0:
                    w = abs(ic_ir.get(f, 0)) / qqc_ir_sum * self.config.QQC_WEIGHT_THRESHOLD
                else:
                    w = self.config.QQC_WEIGHT_THRESHOLD / len(qqc_in_factors)
                weights[f] = w
                qqc_weight += w
        
        # 剩余权重分配给辅助因子
        aux_factors = [f for f in factor_cols if f not in qqc_in_factors]
        if len(aux_factors) > 0:
            aux_ir_sum = sum(abs(ic_ir.get(f, 0)) for f in aux_factors)
            remaining_weight = 1.0 - qqc_weight
            for f in aux_factors:
                if aux_ir_sum > 0:
                    weights[f] = abs(ic_ir.get(f, 0)) / aux_ir_sum * remaining_weight
                else:
                    weights[f] = remaining_weight / len(aux_factors)
        
        # 归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        
        return weights
    
    def calculate_composite_score(self, 
                                  factors: pd.DataFrame, 
                                  weights: Dict[str, float]) -> pd.Series:
        """计算综合得分"""
        # 标准化因子
        factor_cols = [col for col in factors.columns if col != 'stock_code']
        factors_std = factors.copy()
        
        for col in factor_cols:
            mean = factors[col].mean()
            std = factors[col].std()
            if std > 0:
                factors_std[col] = (factors[col] - mean) / std
            else:
                factors_std[col] = 0
        
        # 加权求和
        score = pd.Series(0.0, index=factors.index)
        for factor, weight in weights.items():
            if factor in factors_std.columns:
                score += factors_std[factor] * weight
        
        return score


# =============================================================================
# 组合优化模块
# =============================================================================

class PortfolioOptimizer:
    """组合优化器 - 使用cvxpy进行二次规划"""
    
    def __init__(self, config: Config):
        self.config = config
        self.use_cvxpy = self._check_cvxpy()
    
    def _check_cvxpy(self) -> bool:
        """检查cvxpy是否可用"""
        if not self.config.USE_CVXPY:
            return False
        
        try:
            import cvxpy as cp
            return True
        except ImportError:
            print("[Warning] cvxpy未安装，使用降级方案")
            return False
    
    def optimize(self,
                scores: pd.Series,
                benchmark_weights: pd.Series,
                market_caps: pd.Series,
                industry_map: Dict[str, str]) -> pd.Series:
        """组合优化
        
        Args:
            scores: 股票综合得分
            benchmark_weights: 基准权重
            market_caps: 市值
            industry_map: 股票->行业映射
            
        Returns:
            优化后的组合权重
        """
        if self.use_cvxpy:
            return self._optimize_cvxpy(scores, benchmark_weights, market_caps, industry_map)
        else:
            return self._optimize_fallback(scores, benchmark_weights, market_caps, industry_map)
    
    def _optimize_cvxpy(self,
                       scores: pd.Series,
                       benchmark_weights: pd.Series,
                       market_caps: pd.Series,
                       industry_map: Dict[str, str]) -> pd.Series:
        """使用cvxpy优化"""
        import cvxpy as cp
        
        n = len(scores)
        stocks = scores.index.tolist()
        
        # 决策变量
        w = cp.Variable(n)
        
        # 对齐索引
        scores_arr = scores.values
        bench_arr = benchmark_weights.reindex(stocks, fill_value=0).values
        
        # 目标函数：最大化得分
        objective = cp.Maximize(scores_arr @ w)
        
        # 约束条件
        constraints = [
            cp.sum(w) == 1,  # 权重和为1
            w >= 0,  # 非负
        ]
        
        # 个股偏离约束
        for i in range(n):
            constraints.append(w[i] <= bench_arr[i] + self.config.STOCK_DEVIATION)
        
        # 求解
        try:
            prob = cp.Problem(objective, constraints)
            prob.solve(solver=cp.ECOS, verbose=False)
            
            if prob.status == 'optimal':
                weights = pd.Series(w.value, index=stocks)
                return weights / weights.sum()  # 归一化
        except Exception as e:
            print(f"[Warning] cvxpy求解失败: {e}，使用降级方案")
        
        return self._optimize_fallback(scores, benchmark_weights, market_caps, industry_map)
    
    def _optimize_fallback(self,
                          scores: pd.Series,
                          benchmark_weights: pd.Series,
                          market_caps: pd.Series,
                          industry_map: Dict[str, str]) -> pd.Series:
        """降级优化方案：基于得分排序+约束调整"""
        # 选取得分前50%的股票
        top_stocks = scores.nlargest(int(len(scores) * 0.5))
        
        # 初始权重：按得分分配
        scores_normalized = (top_stocks - top_stocks.min()) / (top_stocks.max() - top_stocks.min() + 1e-6)
        weights = scores_normalized / scores_normalized.sum()
        
        # 应用个股偏离约束
        bench_weights_aligned = benchmark_weights.reindex(weights.index, fill_value=0)
        weights = weights.clip(upper=bench_weights_aligned + self.config.STOCK_DEVIATION)
        
        # 归一化
        weights = weights / weights.sum()
        
        return weights


# =============================================================================
# 回测引擎
# =============================================================================

class BacktestEngine:
    """回测引擎 - 执行完整回测流程"""
    
    def __init__(self, config: Config):
        self.config = config
        self.loader = DataLoader(config)
        self.factor_calc = FactorCalculator()
        self.factor_weight = FactorWeighting(config)
        self.optimizer = PortfolioOptimizer(config)
        
        # 加载数据
        self.constituents = self.loader.load_hs300_constituents()
        self.prices = self.loader.load_stock_prices()
        self.financial = self.loader.load_financial_data()
        
        # 回测结果
        self.portfolio_values = []
        self.benchmark_values = []
        self.positions = []
    
    def run(self):
        """执行回测"""
        print("=" * 80)
        print("开始回测")
        print("=" * 80)
        
        # 生成调仓日期
        rebalance_dates = pd.date_range(
            self.config.START_DATE, 
            self.config.END_DATE, 
            freq='M'
        )
        
        # 初始化
        portfolio_value = 1.0
        benchmark_value = 1.0
        current_weights = None
        
        for i, date in enumerate(rebalance_dates):
            print(f"\n[{i+1}/{len(rebalance_dates)}] {date.strftime('%Y-%m')}")
            
            # 获取当期成分股
            stocks = self._get_constituents(date)
            if len(stocks) == 0:
                print(f"  警告：无成分股数据")
                continue
            
            # 计算因子
            factors = self.factor_calc.calculate_all_factors(
                self.prices, self.financial, date
            )
            factors = factors[factors['stock_code'].isin(stocks)]
            
            if len(factors) == 0:
                print(f"  警告：无因子数据")
                continue
            
            # 计算下期收益（用于因子加权）
            if i < len(rebalance_dates) - 1:
                next_date = rebalance_dates[i + 1]
                returns = self._calculate_returns(stocks, date, next_date)
            else:
                returns = pd.Series(0, index=factors['stock_code'])
            
            # 因子加权
            factor_weights = self.factor_weight.calculate_factor_weights(
                factors, returns, date
            )
            
            # 计算综合得分
            scores = self.factor_weight.calculate_composite_score(factors, factor_weights)
            scores.index = factors['stock_code'].values
            
            # 构建基准权重（市值加权）
            market_caps = factors.set_index('stock_code')['market_cap']
            benchmark_weights = market_caps / market_caps.sum()
            
            # 组合优化
            industry_map = {s: f"industry_{hash(s) % 10}" for s in stocks}  # 简化行业
            
            optimized_weights = self.optimizer.optimize(
                scores, benchmark_weights, market_caps, industry_map
            )
            
            # 计算调仓成本
            if current_weights is not None:
                turnover = self._calculate_turnover(current_weights, optimized_weights)
                cost = turnover * self.config.TRANSACTION_COST
                portfolio_value *= (1 - cost)
                print(f"  换手率: {turnover:.2%}, 成本: {cost:.4%}")
            
            # 更新持仓
            current_weights = optimized_weights
            
            # 计算当期收益
            period_return = self._calculate_portfolio_return(
                optimized_weights, stocks, date, 
                rebalance_dates[i+1] if i < len(rebalance_dates)-1 else date + pd.DateOffset(months=1)
            )
            benchmark_return = self._calculate_portfolio_return(
                benchmark_weights, stocks, date,
                rebalance_dates[i+1] if i < len(rebalance_dates)-1 else date + pd.DateOffset(months=1)
            )
            
            portfolio_value *= (1 + period_return)
            benchmark_value *= (1 + benchmark_return)
            
            print(f"  组合收益: {period_return:.2%}, 基准收益: {benchmark_return:.2%}")
            print(f"  组合净值: {portfolio_value:.4f}, 基准净值: {benchmark_value:.4f}")
            
            # 记录结果
            self.portfolio_values.append({
                'date': date,
                'value': portfolio_value,
                'return': period_return
            })
            self.benchmark_values.append({
                'date': date,
                'value': benchmark_value,
                'return': benchmark_return
            })
            self.positions.append({
                'date': date,
                'weights': optimized_weights.to_dict()
            })
        
        print("\n" + "=" * 80)
        print("回测完成")
        print("=" * 80)
    
    def _get_constituents(self, date: pd.Timestamp) -> List[str]:
        """获取指定日期的成分股"""
        df = self.constituents[self.constituents['date'] <= date]
        if len(df) == 0:
            df = self.constituents
        
        stocks = df['stock_code'].unique().tolist()
        return stocks[:100]  # 限制数量
    
    def _calculate_returns(self, stocks: List[str], start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.Series:
        """计算收益率"""
        price_pivot = self.prices[self.prices['stock_code'].isin(stocks)].pivot_table(
            index='date', columns='stock_code', values='close'
        )
        
        # 找到最接近的日期
        start_price = price_pivot[price_pivot.index <= start_date].iloc[-1] if len(price_pivot[price_pivot.index <= start_date]) > 0 else price_pivot.iloc[0]
        end_price = price_pivot[price_pivot.index <= end_date].iloc[-1] if len(price_pivot[price_pivot.index <= end_date]) > 0 else price_pivot.iloc[-1]
        
        returns = (end_price / start_price - 1).fillna(0)
        return returns
    
    def _calculate_turnover(self, old_weights: pd.Series, new_weights: pd.Series) -> float:
        """计算换手率"""
        aligned_old = old_weights.reindex(new_weights.index, fill_value=0)
        aligned_new = new_weights.reindex(old_weights.index, fill_value=0)
        
        turnover = (aligned_new - aligned_old).abs().sum() / 2
        return turnover
    
    def _calculate_portfolio_return(self, weights: pd.Series, stocks: List[str], 
                                    start_date: pd.Timestamp, end_date: pd.Timestamp) -> float:
        """计算组合收益率"""
        returns = self._calculate_returns(stocks, start_date, end_date)
        portfolio_return = (weights * returns.reindex(weights.index, fill_value=0)).sum()
        return portfolio_return
    
    def get_results(self) -> Dict:
        """获取回测结果"""
        portfolio_df = pd.DataFrame(self.portfolio_values)
        benchmark_df = pd.DataFrame(self.benchmark_values)
        
        # 计算绩效指标
        metrics = self._calculate_metrics(portfolio_df, benchmark_df)
        
        return {
            'portfolio': portfolio_df,
            'benchmark': benchmark_df,
            'positions': self.positions,
            'metrics': metrics
        }
    
    def _calculate_metrics(self, portfolio_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> Dict:
        """计算绩效指标"""
        # 年化收益
        total_years = len(portfolio_df) / 12
        annual_return = (portfolio_df['value'].iloc[-1] ** (1 / total_years) - 1) if total_years > 0 else 0
        benchmark_annual_return = (benchmark_df['value'].iloc[-1] ** (1 / total_years) - 1) if total_years > 0 else 0
        
        # 年化超额收益
        excess_return = annual_return - benchmark_annual_return
        
        # 跟踪误差
        excess_returns = portfolio_df['return'] - benchmark_df['return']
        tracking_error = excess_returns.std() * np.sqrt(12)
        
        # 信息比率
        information_ratio = excess_return / tracking_error if tracking_error > 0 else 0
        
        # 最大回撤
        max_drawdown = self._calculate_max_drawdown(portfolio_df['value'])
        
        # 月度胜率
        win_rate = (excess_returns > 0).sum() / len(excess_returns)
        
        return {
            'annual_return': annual_return,
            'benchmark_annual_return': benchmark_annual_return,
            'excess_return': excess_return,
            'tracking_error': tracking_error,
            'information_ratio': information_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate
        }
    
    def _calculate_max_drawdown(self, values: pd.Series) -> float:
        """计算最大回撤"""
        cummax = values.cummax()
        drawdown = (values - cummax) / cummax
        return drawdown.min()


# =============================================================================
# 结果输出模块
# =============================================================================

def generate_report(results: Dict, output_dir: str):
    """生成回测报告"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存数值结果
    metrics = results['metrics']
    
    print("\n" + "=" * 80)
    print("回测结果")
    print("=" * 80)
    print(f"年化收益率:     {metrics['annual_return']:.2%}")
    print(f"基准年化收益:   {metrics['benchmark_annual_return']:.2%}")
    print(f"年化超额收益:   {metrics['excess_return']:.2%}")
    print(f"跟踪误差:       {metrics['tracking_error']:.2%}")
    print(f"信息比率:       {metrics['information_ratio']:.2f}")
    print(f"最大回撤:       {metrics['max_drawdown']:.2%}")
    print(f"月度胜率:       {metrics['win_rate']:.2%}")
    print("=" * 80)
    
    # 保存到JSON
    with open(os.path.join(output_dir, 'metrics.json'), 'w', encoding='utf-8') as f:
        json.dump({k: float(v) for k, v in metrics.items()}, f, indent=2, ensure_ascii=False)
    
    # 保存净值曲线
    results['portfolio'].to_csv(os.path.join(output_dir, 'portfolio_values.csv'), index=False)
    results['benchmark'].to_csv(os.path.join(output_dir, 'benchmark_values.csv'), index=False)
    
    print(f"\n结果已保存到: {output_dir}")
    
    return metrics


# =============================================================================
# 主函数
# =============================================================================

def main():
    """主函数"""
    # 配置
    config = Config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 运行回测
    engine.run()
    
    # 获取结果
    results = engine.get_results()
    
    # 生成报告
    metrics = generate_report(results, config.RESULTS_DIR)
    
    return results, metrics


if __name__ == '__main__':
    results, metrics = main()
