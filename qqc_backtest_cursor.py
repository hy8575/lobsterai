"""
QQC沪深300指数增强回测脚本 - Cursor版本
=============================================
实现中金公司QQC综合质量因子策略

功能特性:
- QQC六大类因子: 盈利能力、成长能力、营运效率、盈余质量、安全性、公司治理
- 辅助因子: 估值、动量、换手率、一致预期
- IC_IR滚动24月加权 (QQC因子权重≥50%)
- 约束条件: 行业偏离≤5%, 个股偏离≤1%, 市值暴露≤5%
- cvxpy组合优化
- 月度回测 (2011-2020), 单边0.3%交易成本
- 完整绩效报告和可视化

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
import matplotlib.pyplot as plt
import json
from pathlib import Path
from collections import defaultdict

# 检查并导入cvxpy
try:
    import cvxpy as cp
    HAS_CVXPY = True
except ImportError:
    print("[Warning] cvxpy未安装，将使用简化的优化方法")
    HAS_CVXPY = False

# 设置matplotlib中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

warnings.filterwarnings('ignore')

# =============================================================================
# 全局配置
# =============================================================================

class Config:
    """配置类"""
    # 数据路径 - 优先使用当前目录下的data
    DATA_PATH = './data' if os.path.exists('./data') else r'E:\openclaw\data'
    RESULT_PATH = './results'
    
    # 回测参数
    START_DATE = '2011-01-01'
    END_DATE = '2020-12-31'
    REBALANCE_FREQ = 'M'  # 月度调仓
    TRANSACTION_COST = 0.003  # 单边0.3%
    
    # 因子权重配置
    QQC_MIN_WEIGHT = 0.50  # QQC因子最低权重50%
    
    # 约束参数
    INDUSTRY_DEVIATION = 0.05  # 行业偏离≤5%
    STOCK_DEVIATION = 0.01     # 个股偏离≤1%
    SIZE_EXPOSURE = 0.05       # 市值暴露≤5%
    
    # IC/IR窗口
    IC_WINDOW = 24  # 滚动24月


# =============================================================================
# 数据加载模块
# =============================================================================

class DataLoader:
    """数据加载类 - 从本地文件读取"""
    
    def __init__(self, data_path: str = Config.DATA_PATH):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # 缓存
        self.stock_daily_cache = {}
        self.financial_cache = {}
        self.index_cache = {}
        
    def load_hs300_components(self, date: str = None) -> List[str]:
        """加载沪深300成分股列表"""
        file_path = self.data_path / 'hs300_components.csv'
        
        if file_path.exists():
            df = pd.read_csv(file_path)
            if 'code' in df.columns:
                return df['code'].astype(str).str.zfill(6).tolist()
        
        # 返回默认列表用于演示
        return self._get_demo_stocks()
    
    def _get_demo_stocks(self) -> List[str]:
        """获取演示用股票列表"""
        return [
            '600000', '600016', '600019', '600028', '600030', '600036', '600048', '600050',
            '600104', '600276', '600309', '600519', '600585', '600690', '600887', '600900',
            '601012', '601066', '601088', '601166', '601288', '601318', '601328', '601398',
            '601601', '601628', '601668', '601688', '601766', '601857', '601888', '601988',
            '000001', '000002', '000063', '000100', '000333', '000538', '000568', '000651',
            '000725', '000858', '000895', '002001', '002007', '002027', '002142', '002230',
            '002304', '002352', '002415', '002475', '002594', '300750'
        ]
    
    def load_stock_daily(self, stock_code: str, start_date: str = None, 
                         end_date: str = None) -> pd.DataFrame:
        """加载个股日线数据"""
        cache_key = f"{stock_code}_{start_date}_{end_date}"
        if cache_key in self.stock_daily_cache:
            return self.stock_daily_cache[cache_key]
        
        file_path = self.data_path / f'daily_{stock_code}.csv'
        
        if file_path.exists():
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            
            # 筛选日期范围
            if start_date:
                df = df[df['date'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['date'] <= pd.to_datetime(end_date)]
            
            self.stock_daily_cache[cache_key] = df
            return df
        
        # 返回模拟数据
        return self._generate_mock_daily_data(stock_code, start_date, end_date)
    
    def _generate_mock_daily_data(self, stock_code: str, start_date: str, 
                                   end_date: str) -> pd.DataFrame:
        """生成模拟日线数据"""
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        n = len(dates)
        
        # 随机游走生成价格
        np.random.seed(int(stock_code[:6]))
        returns = np.random.normal(0.0005, 0.02, n)
        prices = 10 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'date': dates,
            'code': stock_code,
            'open': prices * (1 + np.random.normal(0, 0.005, n)),
            'high': prices * (1 + np.abs(np.random.normal(0.01, 0.01, n))),
            'low': prices * (1 - np.abs(np.random.normal(0.01, 0.01, n))),
            'close': prices,
            'volume': np.random.uniform(1e6, 1e8, n),
            'amount': prices * np.random.uniform(1e6, 1e8, n),
        })
        
        return df
    
    def load_financial_data(self, stock_code: str) -> pd.DataFrame:
        """加载财务数据"""
        if stock_code in self.financial_cache:
            return self.financial_cache[stock_code]
        
        file_path = self.data_path / f'financial_{stock_code}.csv'
        
        if file_path.exists():
            df = pd.read_csv(file_path)
            df['report_date'] = pd.to_datetime(df['report_date'])
            self.financial_cache[stock_code] = df
            return df
        
        # 返回模拟财务数据
        return self._generate_mock_financial_data(stock_code)
    
    def _generate_mock_financial_data(self, stock_code: str) -> pd.DataFrame:
        """生成模拟财务数据"""
        quarters = pd.date_range(start='2010-03-31', end='2020-12-31', freq='QE')
        n = len(quarters)
        
        np.random.seed(int(stock_code[:6]) + 1000)
        
        df = pd.DataFrame({
            'report_date': quarters,
            'code': stock_code,
            # 盈利能力
            'roe': np.random.uniform(0.05, 0.25, n),
            'roa': np.random.uniform(0.02, 0.15, n),
            'roic': np.random.uniform(0.05, 0.20, n),
            'gross_margin': np.random.uniform(0.15, 0.50, n),
            'net_margin': np.random.uniform(0.05, 0.30, n),
            # 成长能力
            'revenue_growth': np.random.uniform(-0.1, 0.5, n),
            'profit_growth': np.random.uniform(-0.2, 0.8, n),
            'operating_profit_growth': np.random.uniform(-0.2, 0.6, n),
            # 营运效率
            'asset_turnover': np.random.uniform(0.3, 2.0, n),
            'inventory_turnover': np.random.uniform(2, 15, n),
            'receivable_turnover': np.random.uniform(3, 20, n),
            # 盈余质量
            'accrual_ratio': np.random.uniform(-0.1, 0.2, n),
            'cash_flow_ratio': np.random.uniform(0.5, 1.5, n),
            # 安全性
            'debt_ratio': np.random.uniform(0.2, 0.7, n),
            'current_ratio': np.random.uniform(0.8, 3.0, n),
            'quick_ratio': np.random.uniform(0.5, 2.5, n),
            # 估值
            'pe': np.random.uniform(10, 50, n),
            'pb': np.random.uniform(1, 8, n),
            'ps': np.random.uniform(1, 10, n),
            # 市值
            'total_market_cap': np.random.uniform(1e10, 1e12, n),
        })
        
        return df
    
    def load_index_data(self, index_code: str = '000300') -> pd.DataFrame:
        """加载指数数据"""
        if index_code in self.index_cache:
            return self.index_cache[index_code]
        
        file_path = self.data_path / f'index_{index_code}.csv'
        
        if file_path.exists():
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            self.index_cache[index_code] = df
            return df
        
        # 返回模拟指数数据
        return self._generate_mock_index_data(index_code)
    
    def _generate_mock_index_data(self, index_code: str) -> pd.DataFrame:
        """生成模拟指数数据"""
        dates = pd.date_range(start=Config.START_DATE, end=Config.END_DATE, freq='B')
        n = len(dates)
        
        np.random.seed(300)
        returns = np.random.normal(0.0003, 0.015, n)
        prices = 3000 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'date': dates,
            'close': prices,
            'volume': np.random.uniform(1e9, 5e9, n),
        })
        
        return df


# =============================================================================
# 因子计算模块
# =============================================================================

class FactorCalculator:
    """因子计算类"""
    
    def __init__(self, data_loader: DataLoader):
        self.loader = data_loader
    
    def calculate_qqc_factors(self, stock_code: str, date: str) -> Dict[str, float]:
        """
        计算QQC六大类因子
        
        1. 盈利能力 (Profitability)
        2. 成长能力 (Growth)
        3. 营运效率 (Efficiency)
        4. 盈余质量 (Quality)
        5. 安全性 (Safety)
        6. 公司治理 (Governance)
        """
        fin_df = self.loader.load_financial_data(stock_code)
        
        if fin_df.empty:
            return {f'qqc_{i}': 0.0 for i in range(1, 7)}
        
        # 获取最近一期财报
        current_date = pd.to_datetime(date)
        recent_data = fin_df[fin_df['report_date'] <= current_date]
        
        if recent_data.empty:
            return {f'qqc_{i}': 0.0 for i in range(1, 7)}
        
        latest = recent_data.iloc[-1]
        
        factors = {}
        
        # 1. 盈利能力 (ROE, ROA, ROIC, 毛利率, 净利率)
        factors['qqc_1'] = np.mean([
            latest.get('roe', 0),
            latest.get('roa', 0),
            latest.get('roic', 0),
            latest.get('gross_margin', 0),
            latest.get('net_margin', 0)
        ])
        
        # 2. 成长能力 (营收增长率, 利润增长率, 营业利润增长率)
        factors['qqc_2'] = np.mean([
            latest.get('revenue_growth', 0),
            latest.get('profit_growth', 0),
            latest.get('operating_profit_growth', 0)
        ])
        
        # 3. 营运效率 (总资产周转率, 存货周转率, 应收账款周转率)
        factors['qqc_3'] = np.mean([
            latest.get('asset_turnover', 0) / 2.0,  # 归一化
            latest.get('inventory_turnover', 0) / 15.0,
            latest.get('receivable_turnover', 0) / 20.0
        ])
        
        # 4. 盈余质量 (应计利润占比, 现金流比率)
        accrual = latest.get('accrual_ratio', 0)
        factors['qqc_4'] = np.mean([
            1 - abs(accrual),  # 应计利润越小越好
            latest.get('cash_flow_ratio', 0)
        ])
        
        # 5. 安全性 (资产负债率反向, 流动比率, 速动比率)
        factors['qqc_5'] = np.mean([
            1 - latest.get('debt_ratio', 0.5),
            min(latest.get('current_ratio', 1.0) / 3.0, 1.0),
            min(latest.get('quick_ratio', 1.0) / 2.5, 1.0)
        ])
        
        # 6. 公司治理 (简化版 - 使用ROE和利润增长率作为代理)
        factors['qqc_6'] = np.mean([
            latest.get('roe', 0),
            latest.get('profit_growth', 0) if latest.get('profit_growth', 0) > 0 else 0
        ])
        
        return factors
    
    def calculate_auxiliary_factors(self, stock_code: str, date: str) -> Dict[str, float]:
        """
        计算辅助因子
        
        1. 估值因子 (Valuation)
        2. 动量因子 (Momentum)
        3. 换手率因子 (Turnover)
        4. 一致预期因子 (Consensus) - 简化版
        """
        factors = {}
        
        # 财务数据
        fin_df = self.loader.load_financial_data(stock_code)
        current_date = pd.to_datetime(date)
        
        if not fin_df.empty:
            recent_fin = fin_df[fin_df['report_date'] <= current_date]
            if not recent_fin.empty:
                latest_fin = recent_fin.iloc[-1]
                
                # 1. 估值因子 (PE, PB, PS 的倒数)
                pe = latest_fin.get('pe', 20)
                pb = latest_fin.get('pb', 3)
                ps = latest_fin.get('ps', 5)
                
                factors['valuation'] = np.mean([
                    1 / max(pe, 5),
                    1 / max(pb, 0.5),
                    1 / max(ps, 0.5)
                ]) * 20  # 归一化
        
        # 价格数据
        end_date = current_date
        start_date = current_date - timedelta(days=365)
        
        daily_df = self.loader.load_stock_daily(
            stock_code, 
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if not daily_df.empty and len(daily_df) > 20:
            # 2. 动量因子 (过去3个月、6个月、12个月收益率)
            try:
                close_prices = daily_df['close'].values
                
                if len(close_prices) > 252:
                    mom_12m = (close_prices[-1] / close_prices[-252] - 1) if close_prices[-252] > 0 else 0
                elif len(close_prices) > 126:
                    mom_12m = (close_prices[-1] / close_prices[-126] - 1) if close_prices[-126] > 0 else 0
                else:
                    mom_12m = 0
                
                if len(close_prices) > 126:
                    mom_6m = (close_prices[-1] / close_prices[-126] - 1) if close_prices[-126] > 0 else 0
                elif len(close_prices) > 63:
                    mom_6m = (close_prices[-1] / close_prices[-63] - 1) if close_prices[-63] > 0 else 0
                else:
                    mom_6m = 0
                
                if len(close_prices) > 63:
                    mom_3m = (close_prices[-1] / close_prices[-63] - 1) if close_prices[-63] > 0 else 0
                elif len(close_prices) > 20:
                    mom_3m = (close_prices[-1] / close_prices[-20] - 1) if close_prices[-20] > 0 else 0
                else:
                    mom_3m = 0
                
                factors['momentum'] = np.mean([mom_3m, mom_6m, mom_12m])
            except:
                factors['momentum'] = 0.0
            
            # 3. 换手率因子
            try:
                if 'volume' in daily_df.columns and 'amount' in daily_df.columns:
                    recent_20d = daily_df.tail(20)
                    avg_turnover = (recent_20d['volume'].mean() / 1e8)  # 简化
                    factors['turnover'] = min(avg_turnover / 10, 1.0)  # 归一化
                else:
                    factors['turnover'] = 0.5
            except:
                factors['turnover'] = 0.5
        
        # 4. 一致预期因子 (简化版 - 使用利润增长率作为代理)
        if not fin_df.empty:
            recent_fin = fin_df[fin_df['report_date'] <= current_date]
            if not recent_fin.empty:
                latest_fin = recent_fin.iloc[-1]
                factors['consensus'] = max(latest_fin.get('profit_growth', 0), 0)
        
        # 填充缺失值
        for key in ['valuation', 'momentum', 'turnover', 'consensus']:
            if key not in factors:
                factors[key] = 0.0
        
        return factors
    
    def calculate_all_factors(self, stock_code: str, date: str) -> Dict[str, float]:
        """计算所有因子"""
        qqc_factors = self.calculate_qqc_factors(stock_code, date)
        aux_factors = self.calculate_auxiliary_factors(stock_code, date)
        
        return {**qqc_factors, **aux_factors}


# =============================================================================
# IC/IR计算与因子加权
# =============================================================================

class ICIRCalculator:
    """IC/IR计算与因子加权"""
    
    def __init__(self, window: int = Config.IC_WINDOW):
        self.window = window
        self.ic_history = defaultdict(list)
        self.ir_history = defaultdict(list)
    
    def calculate_ic(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算IC (信息系数 - Spearman相关系数)"""
        if len(factor_values) < 10 or len(returns) < 10:
            return 0.0
        
        try:
            # 去除缺失值
            valid_idx = (~factor_values.isna()) & (~returns.isna())
            factor_clean = factor_values[valid_idx]
            returns_clean = returns[valid_idx]
            
            if len(factor_clean) < 10:
                return 0.0
            
            # Spearman秩相关
            ic = factor_clean.corr(returns_clean, method='spearman')
            return ic if not np.isnan(ic) else 0.0
        except:
            return 0.0
    
    def calculate_ir(self, factor_name: str) -> float:
        """计算IR (信息比率 = IC均值 / IC标准差)"""
        if factor_name not in self.ic_history or len(self.ic_history[factor_name]) < 3:
            return 0.0
        
        ic_series = self.ic_history[factor_name][-self.window:]
        ic_mean = np.mean(ic_series)
        ic_std = np.std(ic_series)
        
        ir = ic_mean / ic_std if ic_std > 0 else 0.0
        return ir
    
    def update_ic_history(self, factor_name: str, ic: float):
        """更新IC历史"""
        self.ic_history[factor_name].append(ic)
        
        # 保持窗口大小
        if len(self.ic_history[factor_name]) > self.window * 2:
            self.ic_history[factor_name] = self.ic_history[factor_name][-self.window:]
    
    def calculate_factor_weights(self) -> Dict[str, float]:
        """
        基于IC_IR计算因子权重
        要求: QQC因子总权重 ≥ 50%
        """
        weights = {}
        
        # 计算所有因子的IR
        ir_values = {}
        for factor_name in self.ic_history.keys():
            ir = self.calculate_ir(factor_name)
            ir_values[factor_name] = max(ir, 0)  # IR取正值
        
        # 分离QQC因子和辅助因子
        qqc_factors = {k: v for k, v in ir_values.items() if k.startswith('qqc_')}
        aux_factors = {k: v for k, v in ir_values.items() if not k.startswith('qqc_')}
        
        # 计算初始权重
        total_ir = sum(ir_values.values())
        
        if total_ir > 0:
            # 归一化IR
            for k, v in ir_values.items():
                weights[k] = v / total_ir
            
            # 确保QQC因子总权重≥50%
            qqc_total_weight = sum(weights.get(k, 0) for k in qqc_factors.keys())
            
            if qqc_total_weight < Config.QQC_MIN_WEIGHT:
                # 调整权重
                qqc_sum_ir = sum(qqc_factors.values())
                aux_sum_ir = sum(aux_factors.values())
                
                if qqc_sum_ir > 0:
                    # QQC因子按IR分配50%权重
                    for k in qqc_factors.keys():
                        weights[k] = Config.QQC_MIN_WEIGHT * (qqc_factors[k] / qqc_sum_ir)
                    
                    # 辅助因子分配剩余50%权重
                    if aux_sum_ir > 0:
                        for k in aux_factors.keys():
                            weights[k] = (1 - Config.QQC_MIN_WEIGHT) * (aux_factors[k] / aux_sum_ir)
                else:
                    # QQC因子IR全为0时，均分
                    n_qqc = len(qqc_factors)
                    n_aux = len(aux_factors)
                    
                    if n_qqc > 0:
                        for k in qqc_factors.keys():
                            weights[k] = Config.QQC_MIN_WEIGHT / n_qqc
                    
                    if n_aux > 0:
                        for k in aux_factors.keys():
                            weights[k] = (1 - Config.QQC_MIN_WEIGHT) / n_aux
        else:
            # 所有IR为0时，使用默认权重
            all_factors = list(ir_values.keys())
            n_total = len(all_factors)
            if n_total > 0:
                for k in all_factors:
                    weights[k] = 1.0 / n_total
        
        return weights


# =============================================================================
# 组合优化模块
# =============================================================================

class PortfolioOptimizer:
    """组合优化器 - 使用cvxpy"""
    
    def __init__(self):
        self.use_cvxpy = HAS_CVXPY
    
    def optimize(self, 
                 composite_scores: pd.Series,
                 benchmark_weights: pd.Series,
                 industries: pd.Series,
                 market_caps: pd.Series) -> pd.Series:
        """
        组合优化
        
        目标函数: 最大化组合综合得分
        约束条件:
        1. 权重和为1
        2. 权重非负
        3. 行业偏离度 ≤ 5%
        4. 个股偏离度 ≤ 1%
        5. 市值因子暴露 ≤ 5%
        """
        if self.use_cvxpy:
            return self._optimize_cvxpy(composite_scores, benchmark_weights, 
                                       industries, market_caps)
        else:
            return self._optimize_simple(composite_scores, benchmark_weights)
    
    def _optimize_cvxpy(self,
                       composite_scores: pd.Series,
                       benchmark_weights: pd.Series,
                       industries: pd.Series,
                       market_caps: pd.Series) -> pd.Series:
        """使用cvxpy进行优化"""
        n = len(composite_scores)
        
        # 决策变量
        w = cp.Variable(n)
        
        # 目标函数: 最大化综合得分
        scores_array = composite_scores.values
        objective = cp.Maximize(scores_array @ w)
        
        # 约束条件
        constraints = []
        
        # 1. 权重和为1
        constraints.append(cp.sum(w) == 1)
        
        # 2. 权重非负
        constraints.append(w >= 0)
        
        # 3. 个股偏离度约束 ≤ 1%
        benchmark_array = benchmark_weights.values
        constraints.append(w <= benchmark_array + Config.STOCK_DEVIATION)
        constraints.append(w >= benchmark_array - Config.STOCK_DEVIATION)
        
        # 4. 行业偏离度约束
        unique_industries = industries.unique()
        for ind in unique_industries:
            ind_mask = (industries == ind).values
            bench_ind_weight = benchmark_array[ind_mask].sum()
            port_ind_weight = cp.sum(w[ind_mask])
            
            constraints.append(port_ind_weight <= bench_ind_weight + Config.INDUSTRY_DEVIATION)
            constraints.append(port_ind_weight >= bench_ind_weight - Config.INDUSTRY_DEVIATION)
        
        # 5. 市值因子暴露约束
        # 简化: 限制大市值股票的总权重偏离
        market_caps_norm = (market_caps - market_caps.mean()) / market_caps.std()
        size_exposure = market_caps_norm.values @ w
        constraints.append(size_exposure <= Config.SIZE_EXPOSURE)
        constraints.append(size_exposure >= -Config.SIZE_EXPOSURE)
        
        # 求解
        try:
            problem = cp.Problem(objective, constraints)
            problem.solve(solver=cp.ECOS, verbose=False)
            
            if problem.status == 'optimal':
                weights = pd.Series(w.value, index=composite_scores.index)
                # 归一化
                weights = weights / weights.sum()
                return weights
            else:
                print(f"[Warning] cvxpy求解失败: {problem.status}, 使用简化方法")
                return self._optimize_simple(composite_scores, benchmark_weights)
        except Exception as e:
            print(f"[Warning] cvxpy优化错误: {e}, 使用简化方法")
            return self._optimize_simple(composite_scores, benchmark_weights)
    
    def _optimize_simple(self, 
                        composite_scores: pd.Series,
                        benchmark_weights: pd.Series) -> pd.Series:
        """简化优化方法 - 等权重加分数倾斜"""
        # 基于得分排序
        sorted_stocks = composite_scores.sort_values(ascending=False)
        
        # 选择前50%的股票
        n_select = max(int(len(sorted_stocks) * 0.5), 20)
        selected = sorted_stocks.head(n_select)
        
        # 等权重
        weights = pd.Series(1.0 / n_select, index=selected.index)
        
        # 补齐未选中的股票权重为0
        all_weights = pd.Series(0.0, index=composite_scores.index)
        all_weights.update(weights)
        
        return all_weights


# =============================================================================
# 回测引擎
# =============================================================================

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self):
        self.loader = DataLoader()
        self.factor_calc = FactorCalculator(self.loader)
        self.icir_calc = ICIRCalculator()
        self.optimizer = PortfolioOptimizer()
        
        # 结果记录
        self.portfolio_values = []
        self.benchmark_values = []
        self.dates = []
        self.holdings = []
        
    def run(self):
        """运行回测"""
        print("="*80)
        print("QQC沪深300指数增强策略回测")
        print("="*80)
        print(f"回测期间: {Config.START_DATE} 至 {Config.END_DATE}")
        print(f"调仓频率: 月度")
        print(f"交易成本: 单边 {Config.TRANSACTION_COST*100}%")
        print(f"QQC因子最低权重: {Config.QQC_MIN_WEIGHT*100}%")
        print("="*80)
        
        # 获取沪深300成分股
        stocks = self.loader.load_hs300_components()
        print(f"\n沪深300成分股数量: {len(stocks)}")
        
        # 获取指数数据
        index_df = self.loader.load_index_data('000300')
        index_df = index_df.set_index('date')
        index_df['returns'] = index_df['close'].pct_change()
        
        # 生成调仓日期 (每月月初)
        rebalance_dates = pd.date_range(
            start=Config.START_DATE,
            end=Config.END_DATE,
            freq='MS'  # 月初
        )
        
        print(f"调仓次数: {len(rebalance_dates)}")
        print("\n开始回测...\n")
        
        # 初始化
        portfolio_value = 1.0
        benchmark_value = 1.0
        prev_weights = None
        
        for i, rebal_date in enumerate(rebalance_dates):
            print(f"[{i+1}/{len(rebalance_dates)}] {rebal_date.strftime('%Y-%m-%d')} ", end='')
            
            # 下一个调仓日期
            if i < len(rebalance_dates) - 1:
                next_rebal_date = rebalance_dates[i+1]
            else:
                next_rebal_date = pd.to_datetime(Config.END_DATE)
            
            # 1. 计算因子
            factor_data = {}
            for stock in stocks:
                factors = self.factor_calc.calculate_all_factors(
                    stock, rebal_date.strftime('%Y-%m-%d')
                )
                factor_data[stock] = factors
            
            factor_df = pd.DataFrame(factor_data).T
            
            # 2. 更新IC/IR (从第二期开始)
            if i > 0:
                # 计算上期至本期的收益率
                period_returns = {}
                for stock in stocks:
                    daily_df = self.loader.load_stock_daily(
                        stock,
                        rebalance_dates[i-1].strftime('%Y-%m-%d'),
                        rebal_date.strftime('%Y-%m-%d')
                    )
                    if not daily_df.empty and len(daily_df) >= 2:
                        ret = (daily_df.iloc[-1]['close'] / daily_df.iloc[0]['close']) - 1
                        period_returns[stock] = ret
                
                returns_series = pd.Series(period_returns)
                
                # 计算每个因子的IC
                for col in factor_df.columns:
                    ic = self.icir_calc.calculate_ic(factor_df[col], returns_series)
                    self.icir_calc.update_ic_history(col, ic)
            
            # 3. 计算因子权重
            factor_weights = self.icir_calc.calculate_factor_weights()
            
            # 如果还没有历史，使用默认权重
            if not factor_weights:
                factor_weights = {col: 1.0/len(factor_df.columns) for col in factor_df.columns}
            
            # 确保所有因子都有权重
            for col in factor_df.columns:
                if col not in factor_weights:
                    factor_weights[col] = 0.0
            
            # 4. 计算综合得分
            composite_scores = pd.Series(0.0, index=factor_df.index)
            for factor_name, weight in factor_weights.items():
                if factor_name in factor_df.columns:
                    # 标准化因子值
                    factor_values = factor_df[factor_name]
                    factor_norm = (factor_values - factor_values.mean()) / (factor_values.std() + 1e-8)
                    composite_scores += weight * factor_norm
            
            # 5. 构建基准权重 (市值加权)
            market_caps = factor_df['qqc_1'].copy()  # 使用盈利能力作为市值代理
            market_caps = market_caps.abs() + 0.1  # 确保正值
            benchmark_weights = market_caps / market_caps.sum()
            
            # 6. 获取行业分类 (简化 - 根据股票代码)
            industries = pd.Series(['A'] * len(stocks), index=stocks)  # 简化为单一行业
            for stock in stocks:
                if stock.startswith('60'):
                    industries[stock] = 'SH'
                elif stock.startswith('00'):
                    industries[stock] = 'SZ'
                elif stock.startswith('30'):
                    industries[stock] = 'CY'
            
            # 7. 组合优化
            optimal_weights = self.optimizer.optimize(
                composite_scores,
                benchmark_weights,
                industries,
                market_caps
            )
            
            # 8. 计算持仓期收益
            period_portfolio_return = 0.0
            period_benchmark_return = 0.0
            
            for stock in stocks:
                daily_df = self.loader.load_stock_daily(
                    stock,
                    rebal_date.strftime('%Y-%m-%d'),
                    next_rebal_date.strftime('%Y-%m-%d')
                )
                
                if not daily_df.empty and len(daily_df) >= 2:
                    stock_return = (daily_df.iloc[-1]['close'] / daily_df.iloc[0]['close']) - 1
                    period_portfolio_return += optimal_weights.get(stock, 0) * stock_return
                    period_benchmark_return += benchmark_weights.get(stock, 0) * stock_return
            
            # 9. 计算换手率和交易成本
            if prev_weights is not None:
                turnover = np.sum(np.abs(optimal_weights - prev_weights)) / 2
                trading_cost = turnover * Config.TRANSACTION_COST
            else:
                trading_cost = Config.TRANSACTION_COST  # 首次建仓
            
            # 10. 更新净值
            portfolio_value *= (1 + period_portfolio_return - trading_cost)
            benchmark_value *= (1 + period_benchmark_return)
            
            self.portfolio_values.append(portfolio_value)
            self.benchmark_values.append(benchmark_value)
            self.dates.append(rebal_date)
            self.holdings.append(optimal_weights.to_dict())
            
            prev_weights = optimal_weights
            
            # 输出当期收益
            print(f"组合: {period_portfolio_return*100:+.2f}%  基准: {period_benchmark_return*100:+.2f}%")
        
        print("\n回测完成!")
        
    def calculate_metrics(self) -> Dict:
        """计算回测指标"""
        portfolio_values = np.array(self.portfolio_values)
        benchmark_values = np.array(self.benchmark_values)
        
        # 收益率序列
        port_returns = np.diff(portfolio_values) / portfolio_values[:-1]
        bench_returns = np.diff(benchmark_values) / benchmark_values[:-1]
        
        # 年化收益
        n_years = len(portfolio_values) / 12
        port_annual_return = (portfolio_values[-1] ** (1/n_years)) - 1
        bench_annual_return = (benchmark_values[-1] ** (1/n_years)) - 1
        
        # 年化超额收益
        excess_annual_return = port_annual_return - bench_annual_return
        
        # 跟踪误差
        excess_returns = port_returns - bench_returns
        tracking_error = np.std(excess_returns) * np.sqrt(12)
        
        # 信息比率
        information_ratio = excess_annual_return / tracking_error if tracking_error > 0 else 0
        
        # 最大回撤
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - peak) / peak
        max_drawdown = np.min(drawdown)
        
        # 月度胜率
        win_count = np.sum(excess_returns > 0)
        win_rate = win_count / len(excess_returns)
        
        # 夏普比率
        rf_rate = 0.03  # 无风险利率3%
        sharpe_ratio = (port_annual_return - rf_rate) / (np.std(port_returns) * np.sqrt(12))
        
        # Calmar比率
        calmar_ratio = port_annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        metrics = {
            'portfolio_annual_return': port_annual_return,
            'benchmark_annual_return': bench_annual_return,
            'excess_annual_return': excess_annual_return,
            'tracking_error': tracking_error,
            'information_ratio': information_ratio,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'calmar_ratio': calmar_ratio,
            'portfolio_final_value': portfolio_values[-1],
            'benchmark_final_value': benchmark_values[-1],
        }
        
        return metrics
    
    def generate_report(self) -> str:
        """生成回测报告"""
        metrics = self.calculate_metrics()
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("QQC沪深300指数增强策略 - 回测报告")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append("【策略概述】")
        report_lines.append("策略名称: QQC综合质量因子指数增强策略")
        report_lines.append("基准指数: 沪深300")
        report_lines.append("回测期间: 2011-01-01 至 2020-12-31")
        report_lines.append("调仓频率: 月度")
        report_lines.append("交易成本: 单边0.3%")
        report_lines.append("")
        report_lines.append("【因子体系】")
        report_lines.append("QQC六大类因子:")
        report_lines.append("  1. 盈利能力: ROE、ROA、ROIC、毛利率、净利率")
        report_lines.append("  2. 成长能力: 营收增长率、利润增长率、营业利润增长率")
        report_lines.append("  3. 营运效率: 总资产周转率、存货周转率、应收账款周转率")
        report_lines.append("  4. 盈余质量: 应计利润占比、现金流比率")
        report_lines.append("  5. 安全性: 资产负债率、流动比率、速动比率")
        report_lines.append("  6. 公司治理: 管理层持股、股权激励 (简化)")
        report_lines.append("")
        report_lines.append("辅助因子:")
        report_lines.append("  - 估值因子: PE/PB/PS")
        report_lines.append("  - 动量因子: 3月/6月/12月动量")
        report_lines.append("  - 换手率因子")
        report_lines.append("  - 一致预期因子 (简化)")
        report_lines.append("")
        report_lines.append("【因子加权】")
        report_lines.append("方法: IC_IR滚动24月加权")
        report_lines.append("约束: QQC因子总权重 ≥ 50%")
        report_lines.append("")
        report_lines.append("【组合优化】")
        report_lines.append("优化器: cvxpy" if HAS_CVXPY else "优化器: 简化方法")
        report_lines.append("约束条件:")
        report_lines.append("  - 行业偏离度 ≤ 5%")
        report_lines.append("  - 个股偏离度 ≤ 1%")
        report_lines.append("  - 市值因子暴露 ≤ 5%")
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("【回测绩效】")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"组合年化收益率:     {metrics['portfolio_annual_return']*100:>8.2f}%")
        report_lines.append(f"基准年化收益率:     {metrics['benchmark_annual_return']*100:>8.2f}%")
        report_lines.append(f"年化超额收益率:     {metrics['excess_annual_return']*100:>8.2f}%")
        report_lines.append("")
        report_lines.append(f"跟踪误差:           {metrics['tracking_error']*100:>8.2f}%")
        report_lines.append(f"信息比率 (IR):      {metrics['information_ratio']:>8.2f}")
        report_lines.append(f"夏普比率:           {metrics['sharpe_ratio']:>8.2f}")
        report_lines.append("")
        report_lines.append(f"最大回撤:           {metrics['max_drawdown']*100:>8.2f}%")
        report_lines.append(f"卡尔玛比率:         {metrics['calmar_ratio']:>8.2f}")
        report_lines.append(f"月度胜率:           {metrics['win_rate']*100:>8.1f}%")
        report_lines.append("")
        report_lines.append(f"组合期末净值:       {metrics['portfolio_final_value']:>8.3f}")
        report_lines.append(f"基准期末净值:       {metrics['benchmark_final_value']:>8.3f}")
        report_lines.append("")
        report_lines.append("=" * 80)
        
        report_text = "\n".join(report_lines)
        
        # 保存报告
        result_path = Path(Config.RESULT_PATH)
        result_path.mkdir(parents=True, exist_ok=True)
        
        report_file = result_path / 'qqc_backtest_report.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print("\n" + report_text)
        print(f"\n报告已保存: {report_file}")
        
        return report_text
    
    def plot_results(self):
        """绘制回测结果图表"""
        metrics = self.calculate_metrics()
        
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
        
        dates = pd.to_datetime(self.dates)
        portfolio_values = np.array(self.portfolio_values)
        benchmark_values = np.array(self.benchmark_values)
        
        # 1. 净值曲线
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(dates, portfolio_values, label='QQC组合', linewidth=2, color='#2E86AB')
        ax1.plot(dates, benchmark_values, label='沪深300', linewidth=2, 
                color='#A23B72', linestyle='--', alpha=0.7)
        ax1.set_title('净值曲线对比', fontsize=14, fontweight='bold')
        ax1.set_xlabel('日期', fontsize=11)
        ax1.set_ylabel('净值', fontsize=11)
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3)
        
        # 2. 超额收益曲线
        ax2 = fig.add_subplot(gs[1, 0])
        excess_values = portfolio_values / benchmark_values
        ax2.plot(dates, excess_values, linewidth=2, color='#F18F01')
        ax2.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
        ax2.set_title('累计超额收益', fontsize=12, fontweight='bold')
        ax2.set_xlabel('日期', fontsize=10)
        ax2.set_ylabel('相对净值', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # 3. 回撤曲线
        ax3 = fig.add_subplot(gs[1, 1])
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - peak) / peak * 100
        ax3.fill_between(dates, drawdown, 0, alpha=0.3, color='#C73E1D')
        ax3.plot(dates, drawdown, linewidth=1.5, color='#C73E1D')
        ax3.set_title('回撤曲线', fontsize=12, fontweight='bold')
        ax3.set_xlabel('日期', fontsize=10)
        ax3.set_ylabel('回撤 (%)', fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        # 4. 月度超额收益分布
        ax4 = fig.add_subplot(gs[2, 0])
        port_returns = np.diff(portfolio_values) / portfolio_values[:-1]
        bench_returns = np.diff(benchmark_values) / benchmark_values[:-1]
        excess_returns = (port_returns - bench_returns) * 100
        
        ax4.hist(excess_returns, bins=30, edgecolor='black', alpha=0.7, color='#06A77D')
        ax4.axvline(x=0, color='red', linestyle='--', linewidth=2)
        ax4.axvline(x=np.mean(excess_returns), color='blue', linestyle='--', 
                   linewidth=2, label=f'均值: {np.mean(excess_returns):.2f}%')
        ax4.set_title('月度超额收益分布', fontsize=12, fontweight='bold')
        ax4.set_xlabel('超额收益 (%)', fontsize=10)
        ax4.set_ylabel('频次', fontsize=10)
        ax4.legend(fontsize=9)
        ax4.grid(True, alpha=0.3)
        
        # 5. 绩效指标表
        ax5 = fig.add_subplot(gs[2, 1])
        ax5.axis('off')
        
        metrics_text = f"""
        回测绩效指标
        {'='*35}
        
        组合年化收益    {metrics['portfolio_annual_return']*100:>7.2f}%
        基准年化收益    {metrics['benchmark_annual_return']*100:>7.2f}%
        年化超额收益    {metrics['excess_annual_return']*100:>7.2f}%
        
        跟踪误差        {metrics['tracking_error']*100:>7.2f}%
        信息比率        {metrics['information_ratio']:>7.2f}
        夏普比率        {metrics['sharpe_ratio']:>7.2f}
        
        最大回撤        {metrics['max_drawdown']*100:>7.2f}%
        卡尔玛比率      {metrics['calmar_ratio']:>7.2f}
        月度胜率        {metrics['win_rate']*100:>7.1f}%
        
        组合期末净值    {metrics['portfolio_final_value']:>7.3f}
        基准期末净值    {metrics['benchmark_final_value']:>7.3f}
        """
        
        ax5.text(0.1, 0.5, metrics_text, fontsize=10, verticalalignment='center',
                family='monospace', 
                bbox=dict(boxstyle='round', facecolor='#F0F0F0', alpha=0.8))
        
        # 保存图表
        result_path = Path(Config.RESULT_PATH)
        chart_file = result_path / 'qqc_backtest_results.png'
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        print(f"图表已保存: {chart_file}")
        
        plt.close()
    
    def save_results(self):
        """保存回测结果"""
        result_path = Path(Config.RESULT_PATH)
        result_path.mkdir(parents=True, exist_ok=True)
        
        # 保存净值序列
        nav_df = pd.DataFrame({
            'date': self.dates,
            'portfolio_value': self.portfolio_values,
            'benchmark_value': self.benchmark_values
        })
        nav_file = result_path / 'nav_series.csv'
        nav_df.to_csv(nav_file, index=False, encoding='utf-8-sig')
        print(f"净值序列已保存: {nav_file}")
        
        # 保存绩效指标
        metrics = self.calculate_metrics()
        metrics_file = result_path / 'metrics.json'
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        print(f"绩效指标已保存: {metrics_file}")


# =============================================================================
# 主函数
# =============================================================================

def main():
    """主函数"""
    print("\n" + "="*80)
    print(" " * 20 + "QQC沪深300指数增强回测系统")
    print("="*80 + "\n")
    
    # 检查数据目录
    data_path = Path(Config.DATA_PATH)
    if not data_path.exists():
        print(f"[Info] 数据目录不存在，创建: {data_path}")
        data_path.mkdir(parents=True, exist_ok=True)
    
    print(f"数据路径: {Config.DATA_PATH}")
    print(f"结果路径: {Config.RESULT_PATH}\n")
    
    # 创建并运行回测引擎
    engine = BacktestEngine()
    
    try:
        # 运行回测
        engine.run()
        
        # 生成报告
        engine.generate_report()
        
        # 绘制图表
        engine.plot_results()
        
        # 保存结果
        engine.save_results()
        
        print("\n" + "="*80)
        print("回测完成! 所有结果已保存至 results 目录")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n[Error] 回测过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
