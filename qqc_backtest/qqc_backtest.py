"""
中金公司QQC综合质量因子指数增强回测脚本
============================================
基于中金公司QQC综合质量因子研究报告实现

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
import akshare as ak
import cvxpy as cp
from scipy import optimize
import matplotlib.pyplot as plt
from dataclasses import dataclass
import json

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 数据存储路径
DATA_PATH = r"E:\openclaw\data"
os.makedirs(DATA_PATH, exist_ok=True)

warnings.filterwarnings('ignore')


# =============================================================================
# 数据获取模块
# =============================================================================

class DataFetcher:
    """数据获取类 - 使用akshare获取A股数据"""
    
    def __init__(self, data_path: str = DATA_PATH):
        self.data_path = data_path
        self.cache = {}
        
    def _cache_path(self, name: str) -> str:
        """生成缓存文件路径"""
        return os.path.join(self.data_path, f"{name}.csv")
    
    def _load_cache(self, name: str) -> Optional[pd.DataFrame]:
        """从缓存加载数据"""
        path = self._cache_path(name)
        if os.path.exists(path):
            print(f"[Data] 从缓存加载: {name}")
            return pd.read_csv(path, parse_dates=['date'] if 'date' in pd.read_csv(path, nrows=0).columns else [])
        return None
    
    def _save_cache(self, name: str, df: pd.DataFrame):
        """保存数据到缓存"""
        path = self._cache_path(name)
        df.to_csv(path, index=False)
        print(f"[Data] 保存到缓存: {name}")
    
    def get_hs300_constituents(self, date: str) -> List[str]:
        """获取沪深300成分股"""
        cache_key = f"hs300_constituents_{date[:7]}"
        
        try:
            # 获取沪深300成分股
            df = ak.index_stock_cons_weight_csindex(symbol="000300")
            if df is not None and len(df) > 0:
                stocks = df['成分券代码'].tolist() if '成分券代码' in df.columns else df['code'].tolist()
                return [s.zfill(6) for s in stocks]
        except Exception as e:
            print(f"[Warning] 获取沪深300成分股失败: {e}")
        
        # 备用：使用固定列表
        return self._get_default_hs300()
    
    def _get_default_hs300(self) -> List[str]:
        """默认沪深300成分股列表（简化版）"""
        default_stocks = [
            '000001', '000002', '000063', '000100', '000333', '000338', '000568', '000651',
            '000725', '000768', '000858', '000895', '002001', '002007', '002024', '002027',
            '002142', '002230', '002236', '002271', '002304', '002352', '002415', '002460',
            '002475', '002594', '002714', '002812', '300003', '300014', '300015', '300033',
            '300059', '300122', '300124', '300142', '300274', '300408', '300413', '300433',
            '300498', '300750', '600000', '600009', '600016', '600028', '600030', '600031',
            '600036', '600048', '600050', '600104', '600196', '600276', '600309', '600332',
            '600340', '600346', '600406', '600436', '600438', '600519', '600585', '600588',
            '600690', '600703', '600745', '600809', '600837', '600887', '600893', '600900',
            '601012', '601066', '601088', '601100', '601138', '601166', '601186', '601211',
            '601288', '601318', '601319', '601328', '601336', '601398', '601601', '601628',
            '601633', '601668', '601688', '601766', '601788', '601857', '601888', '601899',
            '601901', '601933', '601988', '601989', '603288', '603501', '603659', '603799',
            '603986', '603993'
        ]
        return default_stocks
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取A股股票列表"""
        cache = self._load_cache("stock_list")
        if cache is not None:
            return cache
        
        try:
            df = ak.stock_info_a_code_name()
            self._save_cache("stock_list", df)
            return df
        except Exception as e:
            print(f"[Error] 获取股票列表失败: {e}")
            return pd.DataFrame(columns=['code', 'name'])
    
    def get_daily_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取个股日线数据"""
        cache_name = f"daily_{stock_code}_{start_date}_{end_date}"
        cache = self._load_cache(cache_name)
        if cache is not None:
            return cache
        
        try:
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                    start_date=start_date, end_date=end_date, adjust="qfq")
            if df is not None and len(df) > 0:
                df['date'] = pd.to_datetime(df['日期'])
                df['code'] = stock_code
                df = df.rename(columns={
                    '开盘': 'open', '收盘': 'close', '最高': 'high', 
                    '最低': 'low', '成交量': 'volume', '成交额': 'amount'
                })
                self._save_cache(cache_name, df)
                return df
        except Exception as e:
            print(f"[Warning] 获取{stock_code}日线数据失败: {e}")
        
        return pd.DataFrame()
    
    def get_financial_data(self, stock_code: str) -> pd.DataFrame:
        """获取财务数据"""
        cache_name = f"financial_{stock_code}"
        cache = self._load_cache(cache_name)
        if cache is not None:
            return cache
        
        try:
            df = ak.stock_financial_analysis_indicator(symbol=stock_code)
            if df is not None and len(df) > 0:
                df['code'] = stock_code
                self._save_cache(cache_name, df)
                return df
        except Exception as e:
            print(f"[Warning] 获取{stock_code}财务数据失败: {e}")
        
        return pd.DataFrame()
    
    def get_balance_sheet(self, stock_code: str) -> pd.DataFrame:
        """获取资产负债表"""
        cache_name = f"balance_{stock_code}"
        cache = self._load_cache(cache_name)
        if cache is not None:
            return cache
        
        try:
            df = ak.stock_balance_sheet_by_report_em(symbol=stock_code)
            if df is not None and len(df) > 0:
                df['code'] = stock_code
                self._save_cache(cache_name, df)
                return df
        except Exception as e:
            print(f"[Warning] 获取{stock_code}资产负债表失败: {e}")
        
        return pd.DataFrame()
    
    def get_income_statement(self, stock_code: str) -> pd.DataFrame:
        """获取利润表"""
        cache_name = f"income_{stock_code}"
        cache = self._load_cache(cache_name)
        if cache is not None:
            return cache
        
        try:
            df = ak.stock_profit_sheet_by_report_em(symbol=stock_code)
            if df is not None and len(df) > 0:
                df['code'] = stock_code
                self._save_cache(cache_name, df)
                return df
        except Exception as e:
            print(f"[Warning] 获取{stock_code}利润表失败: {e}")
        
        return pd.DataFrame()
    
    def get_cash_flow(self, stock_code: str) -> pd.DataFrame:
        """获取现金流量表"""
        cache_name = f"cashflow_{stock_code}"
        cache = self._load_cache(cache_name)
        if cache is not None:
            return cache
        
        try:
            df = ak.stock_cash_flow_sheet_by_report_em(symbol=stock_code)
            if df is not None and len(df) > 0:
                df['code'] = stock_code
                self._save_cache(cache_name, df)
                return df
        except Exception as e:
            print(f"[Warning] 获取{stock_code}现金流量表失败: {e}")
        
        return pd.DataFrame()
    
    def get_index_data(self, index_code: str = "000300", start_date: str = "20110101", 
                       end_date: str = "20201231") -> pd.DataFrame:
        """获取指数数据"""
        cache_name = f"index_{index_code}_{start_date}_{end_date}"
        cache = self._load_cache(cache_name)
        if cache is not None:
            return cache
        
        try:
            df = ak.index_zh_a_hist(symbol=index_code, period="daily", 
                                    start_date=start_date, end_date=end_date)
            if df is not None and len(df) > 0:
                df['date'] = pd.to_datetime(df['日期'])
                df = df.rename(columns={
                    '开盘': 'open', '收盘': 'close', '最高': 'high', 
                    '最低': 'low', '成交量': 'volume', '成交额': 'amount'
                })
                self._save_cache(cache_name, df)
                return df
        except Exception as e:
            print(f"[Error] 获取指数{index_code}数据失败: {e}")
        
        return pd.DataFrame()


# =============================================================================
# 因子计算模块
# =============================================================================

class FactorCalculator:
    """因子计算类 - 计算QQC六大维度因子"""
    
    def __init__(self, data_fetcher: DataFetcher):
        self.fetcher = data_fetcher
        
    def calculate_all_factors(self, stock_code: str, date: str) -> Dict[str, float]:
        """计算所有因子"""
        factors = {}
        
        # 获取数据
        fin_df = self.fetcher.get_financial_data(stock_code)
        balance_df = self.fetcher.get_balance_sheet(stock_code)
        income_df = self.fetcher.get_income_statement(stock_code)
        cash_df = self.fetcher.get_cash_flow(stock_code)
        
        if len(fin_df) == 0:
            return factors
        
        # 1. 盈利能力因子
        factors.update(self._calc_profitability(fin_df, balance_df, income_df))
        
        # 2. 成长能力因子
        factors.update(self._calc_growth(fin_df, income_df))
        
        # 3. 营运效率因子
        factors.update(self._calc_operation(fin_df, balance_df, income_df))
        
        # 4. 盈余质量因子
        factors.update(self._calc_accrual(balance_df, income_df, cash_df))
        
        # 5. 安全性因子
        factors.update(self._calc_safety(balance_df, cash_df))
        
        # 6. 公司治理因子（简化处理）
        factors.update(self._calc_governance(stock_code))
        
        return factors
    
    def _calc_profitability(self, fin_df: pd.DataFrame, balance_df: pd.DataFrame, 
                            income_df: pd.DataFrame) -> Dict[str, float]:
        """计算盈利能力因子"""
        factors = {}
        
        try:
            # CFOA = 经营现金流 / 总资产
            if len(fin_df) > 0:
                factors['CFOA'] = fin_df['每股经营现金流量'].iloc[0] / fin_df['每股净资产'].iloc[0] \
                                  if '每股经营现金流量' in fin_df.columns and '每股净资产' in fin_df.columns else 0
            
            # ROE = 净利润 / 净资产
            if '净资产收益率' in fin_df.columns:
                factors['ROE'] = fin_df['净资产收益率'].iloc[0] / 100
            elif len(income_df) > 0 and len(balance_df) > 0:
                net_profit = income_df.get('净利润', pd.Series([0])).iloc[0]
                equity = balance_df.get('所有者权益合计', pd.Series([1])).iloc[0]
                factors['ROE'] = net_profit / equity if equity != 0 else 0
            
            # ROIC = 净利润 / 投入资本
            if len(income_df) > 0 and len(balance_df) > 0:
                net_profit = income_df.get('净利润', pd.Series([0])).iloc[0]
                total_assets = balance_df.get('资产总计', pd.Series([0])).iloc[0]
                current_liab = balance_df.get('流动负债合计', pd.Series([0])).iloc[0]
                invested_capital = total_assets - current_liab
                factors['ROIC'] = net_profit / invested_capital if invested_capital != 0 else 0
                
        except Exception as e:
            print(f"[Warning] 盈利能力因子计算失败: {e}")
            factors = {'CFOA': 0, 'ROE': 0, 'ROIC': 0}
        
        return factors
    
    def _calc_growth(self, fin_df: pd.DataFrame, income_df: pd.DataFrame) -> Dict[str, float]:
        """计算成长能力因子"""
        factors = {}
        
        try:
            # OP_SD: 营业利润稳健加速度
            if len(income_df) >= 3:
                op = income_df.get('营业利润', pd.Series([0]*len(income_df)))
                if len(op) >= 3:
                    op_growth = op.pct_change().dropna()
                    if len(op_growth) >= 2:
                        factors['OP_SD'] = op_growth.iloc[0] - op_growth.iloc[1]
                    else:
                        factors['OP_SD'] = 0
                else:
                    factors['OP_SD'] = 0
            else:
                factors['OP_SD'] = 0
            
            # NP_Acc: 净利润加速度
            if len(income_df) >= 3:
                np_series = income_df.get('净利润', pd.Series([0]*len(income_df)))
                if len(np_series) >= 3:
                    np_growth = np_series.pct_change().dropna()
                    if len(np_growth) >= 2:
                        factors['NP_Acc'] = np_growth.iloc[0] - np_growth.iloc[1]
                    else:
                        factors['NP_Acc'] = 0
                else:
                    factors['NP_Acc'] = 0
            else:
                factors['NP_Acc'] = 0
            
            # OP_Q_YOY: 营业利润单季度同比
            if '营业利润同比增长率' in fin_df.columns:
                factors['OP_Q_YOY'] = fin_df['营业利润同比增长率'].iloc[0] / 100
            else:
                factors['OP_Q_YOY'] = 0
            
            # NP_Q_YOY: 净利润单季度同比
            if '净利润同比增长率' in fin_df.columns:
                factors['NP_Q_YOY'] = fin_df['净利润同比增长率'].iloc[0] / 100
            else:
                factors['NP_Q_YOY'] = 0
            
            # QPT: 业绩趋势因子
            if len(income_df) >= 4:
                np_series = income_df.get('净利润', pd.Series([0]*len(income_df)))
                if len(np_series) >= 4:
                    np_growth = np_series.pct_change().dropna()
                    factors['QPT'] = np_growth.mean() if len(np_growth) > 0 else 0
                else:
                    factors['QPT'] = 0
            else:
                factors['QPT'] = 0
                
        except Exception as e:
            print(f"[Warning] 成长能力因子计算失败: {e}")
            factors = {'OP_SD': 0, 'NP_Acc': 0, 'OP_Q_YOY': 0, 'NP_Q_YOY': 0, 'QPT': 0}
        
        return factors
    
    def _calc_operation(self, fin_df: pd.DataFrame, balance_df: pd.DataFrame, 
                        income_df: pd.DataFrame) -> Dict[str, float]:
        """计算营运效率因子"""
        factors = {}
        
        try:
            # ATD: 总资产周转率变动
            if len(balance_df) >= 2 and len(income_df) >= 2:
                revenue = income_df.get('营业收入', pd.Series([0]*len(income_df)))
                total_assets = balance_df.get('资产总计', pd.Series([1]*len(balance_df)))
                
                at_current = revenue.iloc[0] / total_assets.iloc[0] if total_assets.iloc[0] != 0 else 0
                at_prev = revenue.iloc[1] / total_assets.iloc[1] if total_assets.iloc[1] != 0 else 0
                factors['ATD'] = at_current - at_prev
            else:
                factors['ATD'] = 0
            
            # OCFA: 产能利用率提升
            if len(balance_df) >= 2 and len(income_df) >= 2:
                revenue = income_df.get('营业收入', pd.Series([0]*len(income_df)))
                fixed_assets = balance_df.get('固定资产', pd.Series([1]*len(balance_df)))
                
                fa_current = revenue.iloc[0] / fixed_assets.iloc[0] if fixed_assets.iloc[0] != 0 else 0
                fa_prev = revenue.iloc[1] / fixed_assets.iloc[1] if fixed_assets.iloc[1] != 0 else 0
                factors['OCFA'] = fa_current - fa_prev
            else:
                factors['OCFA'] = 0
                
        except Exception as e:
            print(f"[Warning] 营运效率因子计算失败: {e}")
            factors = {'ATD': 0, 'OCFA': 0}
        
        return factors
    
    def _calc_accrual(self, balance_df: pd.DataFrame, income_df: pd.DataFrame, 
                      cash_df: pd.DataFrame) -> Dict[str, float]:
        """计算盈余质量因子"""
        factors = {}
        
        try:
            # APR: 应计利润占比 = 应计利润 / 营业利润
            if len(income_df) > 0 and len(cash_df) > 0:
                net_profit = income_df.get('净利润', pd.Series([0])).iloc[0]
                op_cash_flow = cash_df.get('经营活动产生的现金流量净额', pd.Series([0])).iloc[0]
                operating_profit = income_df.get('营业利润', pd.Series([1])).iloc[0]
                
                accrual = net_profit - op_cash_flow
                factors['APR'] = accrual / operating_profit if operating_profit != 0 else 0
            else:
                factors['APR'] = 0
                
        except Exception as e:
            print(f"[Warning] 盈余质量因子计算失败: {e}")
            factors = {'APR': 0}
        
        return factors
    
    def _calc_safety(self, balance_df: pd.DataFrame, cash_df: pd.DataFrame) -> Dict[str, float]:
        """计算安全性因子"""
        factors = {}
        
        try:
            # CCR: 现金流动负债比率 = 经营净现金流 / 流动负债
            if len(cash_df) > 0 and len(balance_df) > 0:
                op_cash_flow = cash_df.get('经营活动产生的现金流量净额', pd.Series([0])).iloc[0]
                current_liab = balance_df.get('流动负债合计', pd.Series([1])).iloc[0]
                factors['CCR'] = op_cash_flow / current_liab if current_liab != 0 else 0
            else:
                factors['CCR'] = 0
                
        except Exception as e:
            print(f"[Warning] 安全性因子计算失败: {e}")
            factors = {'CCR': 0}
        
        return factors
    
    def _calc_governance(self, stock_code: str) -> Dict[str, float]:
        """计算公司治理因子（简化版）"""
        factors = {}
        
        # 由于治理数据较难获取，使用默认值或简化计算
        factors['FLOAT_RATIO'] = 0.5
        factors['MGMT_PAY'] = 0
        factors['MGMT_HOLD'] = 0
        factors['PENALTY'] = 0
        factors['EQUITY_INCENTIVE'] = 0
        
        return factors
    
    def calc_valuation_factors(self, stock_code: str, date: str) -> Dict[str, float]:
        """计算估值因子"""
        factors = {}
        
        try:
            daily_df = self.fetcher.get_daily_data(stock_code, date, date)
            fin_df = self.fetcher.get_financial_data(stock_code)
            
            if len(daily_df) == 0 or len(fin_df) == 0:
                return {'BP_LR': 0, 'DP': 0, 'EEP': 0}
            
            price = daily_df['close'].iloc[0]
            
            # BP_LR: 账面市值比
            if '每股净资产' in fin_df.columns:
                bvps = fin_df['每股净资产'].iloc[0]
                factors['BP_LR'] = bvps / price if price != 0 else 0
            else:
                factors['BP_LR'] = 0
            
            # DP: 股息率
            if '每股股息' in fin_df.columns:
                dps = fin_df['每股股息'].iloc[0]
                factors['DP'] = dps / price if price != 0 else 0
            else:
                factors['DP'] = 0
            
            # EEP: 盈利收益率
            if '每股收益' in fin_df.columns:
                eps = fin_df['每股收益'].iloc[0]
                factors['EEP'] = eps / price if price != 0 else 0
            else:
                factors['EEP'] = 0
                
        except Exception as e:
            print(f"[Warning] 估值因子计算失败: {e}")
            factors = {'BP_LR': 0, 'DP': 0, 'EEP': 0}
        
        return factors
    
    def calc_momentum_factor(self, stock_code: str, date: str) -> Dict[str, float]:
        """计算动量因子"""
        factors = {}
        
        try:
            end_date = datetime.strptime(date, '%Y%m%d')
            start_date = end_date - timedelta(days=730)
            
            df = self.fetcher.get_daily_data(
                stock_code, 
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )
            
            if len(df) > 60:
                returns = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
                factors['Momentum_24M'] = returns
            else:
                factors['Momentum_24M'] = 0
                
        except Exception as e:
            print(f"[Warning] 动量因子计算失败: {e}")
            factors = {'Momentum_24M': 0}
        
        return factors
    
    def calc_turnover_factor(self, stock_code: str, date: str) -> Dict[str, float]:
        """计算换手率因子"""
        factors = {}
        
        try:
            end_date = datetime.strptime(date, '%Y%m%d')
            start_date = end_date - timedelta(days=30)
            
            df = self.fetcher.get_daily_data(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )
            
            if len(df) > 0:
                avg_turnover = df['volume'].mean()
                factors['VA_FC_1M'] = -avg_turnover
            else:
                factors['VA_FC_1M'] = 0
                
        except Exception as e:
            print(f"[Warning] 换手率因子计算失败: {e}")
            factors = {'VA_FC_1M': 0}
        
        return factors
    
    def calc_consensus_factor(self, stock_code: str, date: str) -> Dict[str, float]:
        """计算一致预期因子"""
        factors = {}
        factors['EEChange_3M'] = 0
        return factors


# =============================================================================
# QQC综合质量因子构建
# =============================================================================

class QQCFactorBuilder:
    """QQC综合质量因子构建类"""
    
    def __init__(self, factor_calculator: FactorCalculator):
        self.calc = factor_calculator
        
        self.dimension_weights = {
            'Profitability': 0.25,
            'Growth': 0.25,
            'Operation': 0.15,
            'Accrual': 0.15,
            'Safety': 0.10,
            'Governance': 0.10
        }
        
        self.factor_weights = {
            'Profitability': {'CFOA': 0.33, 'ROE': 0.34, 'ROIC': 0.33},
            'Growth': {'OP_SD': 0.20, 'NP_Acc': 0.20, 'OP_Q_YOY': 0.20, 
                      'NP_Q_YOY': 0.20, 'QPT': 0.20},
            'Operation': {'ATD': 0.50, 'OCFA': 0.50},
            'Accrual': {'APR': 1.0},
            'Safety': {'CCR': 1.0},
            'Governance': {'FLOAT_RATIO': 0.30, 'MGMT_PAY': 0.15, 
                          'MGMT_HOLD': 0.25, 'PENALTY': 0.15, 'EQUITY_INCENTIVE': 0.15}
        }
    
    def build_qqc_factor(self, stock_code: str, date: str) -> float:
        """构建QQC综合质量因子"""
        factors = self.calc.calculate_all_factors(stock_code, date)
        
        if len(factors) == 0:
            return 0
        
        qqc_score = 0
        
        for dimension, dim_weight in self.dimension_weights.items():
            dim_score = 0
            dim_factors = self.factor_weights.get(dimension, {})
            
            for factor_name, factor_weight in dim_factors.items():
                factor_value = factors.get(factor_name, 0)
                if np.isnan(factor_value) or np.isinf(factor_value):
                    factor_value = 0
                dim_score += factor_value * factor_weight
            
            qqc_score += dim_score * dim_weight
        
        return qqc_score
    
    def build_all_factors(self, stock_code: str, date: str) -> Dict[str, float]:
        """构建所有因子"""
        all_factors = {}
        
        all_factors['QQC'] = self.build_qqc_factor(stock_code, date)
        all_factors.update(self.calc.calc_valuation_factors(stock_code, date))
        all_factors.update(self.calc.calc_momentum_factor(stock_code, date))
        all_factors.update(self.calc.calc_turnover_factor(stock_code, date))
        all_factors.update(self.calc.calc_consensus_factor(stock_code, date))
        
        return all_factors


# =============================================================================
# 组合优化模块
# =============================================================================

class PortfolioOptimizer:
    """组合优化类"""
    
    def __init__(self, risk_aversion: float = 1.0):
        self.risk_aversion = risk_aversion
        
    def optimize(self, 
                 expected_returns: np.ndarray,
                 cov_matrix: np.ndarray,
                 benchmark_weights: np.ndarray,
                 factor_scores: np.ndarray,
                 max_deviation: float = 0.01,
                 long_only: bool = True) -> np.ndarray:
        """组合优化求解"""
        n_assets = len(expected_returns)
        
        w = cp.Variable(n_assets)
        
        portfolio_return = expected_returns @ w
        portfolio_risk = cp.quad_form(w, cov_matrix)
        
        objective = cp.Maximize(portfolio_return - self.risk_aversion * portfolio_risk)
        
        constraints = [
            cp.sum(w) == 1,
        ]
        
        deviation = w - benchmark_weights
        constraints.append(cp.abs(deviation) <= max_deviation)
        
        if long_only:
            constraints.append(w >= 0)
        
        problem = cp.Problem(objective, constraints)
        
        try:
            problem.solve(solver=cp.ECOS)
            
            if problem.status == 'optimal':
                return w.value
            else:
                print(f"[Warning] 优化问题未收敛: {problem.status}")
                return benchmark_weights
        except Exception as e:
            print(f"[Error] 优化求解失败: {e}")
            return benchmark_weights


# =============================================================================
# 回测引擎
# =============================================================================

class BacktestEngine:
    """回测引擎类"""
    
    def __init__(self, 
                 start_date: str = "20110101",
                 end_date: str = "20201231",
                 rebalance_freq: str = "M",
                 transaction_cost: float = 0.003):
        
        self.start_date = start_date
        self.end_date = end_date
        self.rebalance_freq = rebalance_freq
        self.transaction_cost = transaction_cost
        
        self.fetcher = DataFetcher()
        self.calc = FactorCalculator(self.fetcher)
        self.builder = QQCFactorBuilder(self.calc)
        self.optimizer = PortfolioOptimizer()
        
        self.results = {}
        
    def generate_rebalance_dates(self) -> List[str]:
        """生成调仓日期"""
        dates = pd.date_range(start=self.start_date, end=self.end_date, freq=self.rebalance_freq)
        return [d.strftime('%Y%m%d') for d in dates]
    
    def run_backtest(self) -> Dict:
        """运行回测"""
        print("="*60)
        print("QQC综合质量因子指数增强回测")
        print("="*60)
        
        # 获取调仓日期
        rebalance_dates = self.generate_rebalance_dates()
        print(f"调仓日期数量: {len(rebalance_dates)}")
        
        # 获取指数数据
        index_df = self.fetcher.get_index_data("000300", self.start_date, self.end_date)
        if len(index_df) == 0:
            print("[Error] 无法获取指数数据")
            return {}
        
        # 初始化
        portfolio_values = []
        benchmark_values = []
        dates = []
        
        current_weights = None
        
        for i, date in enumerate(rebalance_dates):
            print(f"\n[{i+1}/{len(rebalance_dates)}] 调仓日期: {date}")
            
            # 获取沪深300成分股
            constituents = self.fetcher.get_hs300_constituents(date)
            print(f"  成分股数量: {len(constituents)}")
            
            if len(constituents) == 0:
                continue
            
            # 计算因子（简化：使用前10只股票演示）
            sample_stocks = constituents[:10]
            factor_scores = []
            
            for stock in sample_stocks:
                try:
                    factors = self.builder.build_all_factors(stock, date)
                    factor_scores.append(factors.get('QQC', 0))
                except Exception as e:
                    factor_scores.append(0)
            
            factor_scores = np.array(factor_scores)
            
            # 等权基准权重
            n_assets = len(sample_stocks)
            benchmark_weights = np.ones(n_assets) / n_assets
            
            # 简化：使用因子得分作为预期收益
            expected_returns = factor_scores
            
            # 简化协方差矩阵（单位矩阵）
            cov_matrix = np.eye(n_assets) * 0.01
            
            # 组合优化
            if i == 0 or current_weights is None:
                optimal_weights = benchmark_weights
            else:
                optimal_weights = self.optimizer.optimize(
                    expected_returns,
                    cov_matrix,
                    benchmark_weights,
                    factor_scores,
                    max_deviation=0.01
                )
            
            current_weights = optimal_weights
            
            # 记录组合权重
            print(f"  最优权重: {optimal_weights[:3]}...")
        
        # 获取指数收益
        index_df['returns'] = index_df['close'].pct_change()
        index_df['cumulative'] = (1 + index_df['returns'].fillna(0)).cumprod()
        
        # 模拟组合收益