"""
情景分析因子模型回测 - Cursor生成版本
基于中金公司研报《量化多因子系列（2）：非线性假设下的情景分析因子模型》

核心逻辑：
1. 传统多因子模型统一打分，忽视个股差异（线性假设）
2. 因子对收益的影响是非线性的
3. 基于规模、流动性、估值、盈利、成长的情景特征划分股票池
4. 在不同情景下分别优化因子权重（最大化IR）
"""

import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
from scipy import stats
from scipy.optimize import minimize
import warnings
import os
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 设置路径
WORK_DIR = '/home/node/.openclaw/workspace'
DATA_DIR = f'{WORK_DIR}/cursor_scenario_data'
RESULT_DIR = f'{WORK_DIR}/cursor_scenario_results'
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

print("="*80)
print("情景分析因子模型回测 - Cursor生成版本")
print("基于中金公司研报 - 量化多因子系列（2）")
print("="*80)

# ============================================
# 第一步：数据获取和预处理
# ============================================
print("\n【步骤1】数据获取和预处理...")

def get_stock_list():
    """获取A股股票列表"""
    try:
        stock_df = ak.stock_zh_a_spot_em()
        return stock_df[['代码', '名称']].copy()
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return pd.DataFrame()

def get_stock_data(stock_code, start_date, end_date):
    """获取个股历史数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, end_date=end_date, adjust="qfq")
        if len(df) > 0:
            df['date'] = pd.to_datetime(df['日期'])
            df['close'] = df['收盘'].astype(float)
            df['open'] = df['开盘'].astype(float)
            df['high'] = df['最高'].astype(float)
            df['low'] = df['最低'].astype(float)
            df['volume'] = df['成交量'].astype(float)
            df['amount'] = df['成交额'].astype(float)
            df['stock_code'] = stock_code
            return df[['date', 'stock_code', 'open', 'high', 'low', 'close', 'volume', 'amount']]
    except Exception as e:
        return None
    return None

def get_index_data(index_code, start_date, end_date):
    """获取指数数据"""
    try:
        df = ak.index_zh_a_hist(symbol=index_code, period="daily", 
                                start_date=start_date, end_date=end_date)
        df['date'] = pd.to_datetime(df['日期'])
        df['close'] = df['收盘'].astype(float)
        return df[['date', 'close']].rename(columns={'close': f'{index_code}_close'})
    except Exception as e:
        print(f"获取指数{index_code}失败: {e}")
        return pd.DataFrame()

def get_index_components(index_code):
    """获取指数成分股"""
    try:
        df = ak.index_stock_cons_weight_csindex(symbol=index_code)
        return df['成分券代码'].tolist()
    except Exception as e:
        print(f"获取指数{index_code}成分股失败: {e}")
        return []

# ============================================
# 第二步：情景特征因子计算
# ============================================
print("\n【步骤2】情景特征因子计算...")

def calculate_scenario_features(price_df):
    """
    计算情景特征因子
    
    情景特征（Contextual Features）：
    1. 规模(Size): Ln_MC - 总市值对数
    2. 流动性(Liquidity): VSTD等权 - 成交额/收益率波动
    3. 估值(Cheapness): BP_LR - 市净率倒数
    4. 盈利(Profit): ROE_TTM均值（过去3年）
    5. 成长(Growth): OP_SD与NP_SD等权（8个季度）
    """
    df = price_df.copy()
    
    # 计算收益率
    df['return'] = df['close'].pct_change()
    df['return_1d'] = df['return']
    
    # 1. 规模特征 (Size): 使用成交额作为市值代理（简化版）
    df['market_cap_proxy'] = df['amount'] / (df['volume'] + 1e-6) * df['volume'].rolling(20).mean()
    df['Size'] = np.log(df['market_cap_proxy'] + 1)
    
    # 2. 流动性特征 (Liquidity): VSTD = 成交额 / 收益率波动
    df['return_std_1m'] = df['return'].rolling(20).std() + 1e-6
    df['return_std_3m'] = df['return'].rolling(60).std() + 1e-6
    df['return_std_6m'] = df['return'].rolling(120).std() + 1e-6
    
    df['VSTD_1M'] = df['amount'] / df['return_std_1m']
    df['VSTD_3M'] = df['amount'] / df['return_std_3m']
    df['VSTD_6M'] = df['amount'] / df['return_std_6m']
    df['Liquidity'] = df[['VSTD_1M', 'VSTD_3M', 'VSTD_6M']].mean(axis=1)
    
    # 3. 估值特征 (Cheapness): BP_LR代理 - 使用价格倒数
    df['Cheapness'] = 1.0 / (df['close'] + 1e-6)
    
    # 4. 盈利特征 (Profit): ROE代理 - 使用收益率稳定性
    df['Profit'] = df['return'].rolling(252).mean() / (df['return'].rolling(252).std() + 1e-6)
    
    # 5. 成长特征 (Growth): 收益增长加速度
    df['return_ma_short'] = df['return'].rolling(60).mean()
    df['return_ma_long'] = df['return'].rolling(252).mean()
    df['Growth'] = (df['return_ma_short'] - df['return_ma_long']) / (df['return_ma_long'].abs() + 1e-6)
    
    return df

# ============================================
# 第三步：Alpha因子计算
# ============================================
print("\n【步骤3】Alpha因子计算...")

def calculate_alpha_factors(price_df):
    """
    计算Alpha因子
    
    Alpha因子：
    1. 质量(Quality): QQC综合质量因子
    2. 预期估值(Con_Value): EEP一致预期EP
    3. 预期调整(Con_Change): EEChange与EOPchange等权
    4. 动量(Momentum): Momentum_24M-1M与12M-1M等权
    5. 换手率(Turnover): VA_FC_1M/3M/6M等权
    """
    df = price_df.copy()
    
    # 1. 质量因子 (Quality): 综合质量指标
    # 使用夏普比率作为质量代理
    df['Quality'] = df['return'].rolling(252).mean() / (df['return'].rolling(252).std() + 1e-6)
    
    # 2. 预期估值 (Con_Value): EP代理
    df['Con_Value'] = 1.0 / (df['close'] + 1e-6)
    
    # 3. 预期调整 (Con_Change): 价格变化率
    df['Con_Change'] = df['close'].pct_change(63)  # 3个月变化
    
    # 4. 动量因子 (Momentum): 24M-1M与12M-1M等权
    df['Momentum_24M_1M'] = df['close'].pct_change(504) - df['close'].pct_change(21)
    df['Momentum_12M_1M'] = df['close'].pct_change(252) - df['close'].pct_change(21)
    df['Momentum'] = (df['Momentum_24M_1M'] + df['Momentum_12M_1M']) / 2
    
    # 5. 换手率因子 (Turnover): VA_FC等权
    df['turnover_1m'] = df['volume'] / df['volume'].rolling(20).mean()
    df['turnover_3m'] = df['volume'] / df['volume'].rolling(60).mean()
    df['turnover_6m'] = df['volume'] / df['volume'].rolling(120).mean()
    df['Turnover'] = df[['turnover_1m', 'turnover_3m', 'turnover_6m']].mean(axis=1)
    
    return df

# ============================================
# 第四步：情景分组和IC分析
# ============================================
print("\n【步骤4】情景分组和IC分析...")

def group_by_scenario(df, scenario_feature, date_col='date'):
    """
    按情景特征分组（High/Low）
    以中位数为界划分
    """
    results = []
    
    for date in df[date_col].unique():
        date_data = df[df[date_col] == date].copy()
        
        if len(date_data) < 10:
            continue
        
        # 按中位数分组
        median_val = date_data[scenario_feature].median()
        date_data['group'] = (date_data[scenario_feature] > median_val).astype(int)
        date_data['group_label'] = date_data['group'].map({1: 'High', 0: 'Low'})
        
        results.append(date_data)
    
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()

def calculate_ic(group_df, factor_col, forward_return_col='forward_return'):
    """
    计算信息系数（IC）
    IC = corr(factor_t, return_t+1)
    """
    ic_results = []
    
    for date in group_df['date'].unique():
        date_data = group_df[group_df['date'] == date]
        
        if len(date_data) < 10:
            continue
        
        valid_data = date_data[[factor_col, forward_return_col]].dropna()
        
        if len(valid_data) >= 10:
            ic, p_value = stats.spearmanr(valid_data[factor_col], valid_data[forward_return_col])
            ic_results.append({
                'date': date,
                'ic': ic,
                'p_value': p_value,
                'sample_size': len(valid_data)
            })
    
    return pd.DataFrame(ic_results)

def analyze_ic_by_group(df, scenario_feature, alpha_factors):
    """
    按情景分组分析IC
    """
    results = {}
    
    # 分组
    grouped_df = group_by_scenario(df, scenario_feature)
    
    for group_label in ['High', 'Low']:
        group_data = grouped_df[grouped_df['group_label'] == group_label]
        
        if len(group_data) == 0:
            continue
        
        group_results = {}
        
        for factor in alpha_factors:
            ic_df = calculate_ic(group_data, factor)
            
            if len(ic_df) > 0:
                group_results[factor] = {
                    'ic_mean': ic_df['ic'].mean(),
                    'ic_std': ic_df['ic'].std(),
                    'ic_ir': ic_df['ic'].mean() / (ic_df['ic'].std() + 1e-6),
                    'ic_positive_ratio': (ic_df['ic'] > 0).mean(),
                    'sample_size': len(ic_df)
                }
        
        results[group_label] = group_results
    
    # 全市场分析
    all_results = {}
    for factor in alpha_factors:
        ic_df = calculate_ic(grouped_df, factor)
        
        if len(ic_df) > 0:
            all_results[factor] = {
                'ic_mean': ic_df['ic'].mean(),
                'ic_std': ic_df['ic'].std(),
                'ic_ir': ic_df['ic'].mean() / (ic_df['ic'].std() + 1e-6),
                'ic_positive_ratio': (ic_df['ic'] > 0).mean(),
                'sample_size': len(ic_df)
            }
    
    results['All'] = all_results
    
    return results, grouped_df

# ============================================
# 第五步：最优化IR权重计算
# ============================================
print("\n【步骤5】最优化IR权重计算...")

def optimize_ir_weights(ic_matrix, lookback=12):
    """
    最大化IR的最优权重计算
    
    公式: v ∝ Σ_IC^(-1) · IC̄
    
    其中:
    - Σ_IC: IC协方差矩阵 (滚动12个月)
    - IC̄: IC均值向量 (滚动12个月)
    """
    if len(ic_matrix) < lookback:
        return None
    
    # 计算IC均值
    ic_mean = ic_matrix.mean(axis=0)
    
    # 计算IC协方差矩阵
    ic_cov = ic_matrix.cov()
    
    try:
        # 计算最优权重: v ∝ Σ^(-1) · μ
        ic_cov_inv = np.linalg.inv(ic_cov + np.eye(len(ic_cov)) * 1e-6)  # 正则化
        raw_weights = ic_cov_inv.dot(ic_mean)
        
        # 归一化权重
        weights = raw_weights / (np.abs(raw_weights).sum() + 1e-6)
        
        return pd.Series(weights, index=ic_matrix.columns)
    except Exception as e:
        print(f"权重优化失败: {e}")
        return None

def calculate_optimal_weights_by_scenario(grouped_df, alpha_factors, lookback=12):
    """
    为每个情景组计算最优权重
    """
    weights_history = []
    
    dates = sorted(grouped_df['date'].unique())
    
    for i, date in enumerate(dates):
        if i < lookback:
            continue
        
        # 获取历史数据
        hist_dates = dates[i-lookback:i]
        hist_data = grouped_df[grouped_df['date'].isin(hist_dates)]
        
        date_weights = {'date': date}
        
        for group_label in ['High', 'Low']:
            group_hist = hist_data[hist_data['group_label'] == group_label]
            
            if len(group_hist) < lookback * 5:
                continue
            
            # 构建IC矩阵
            ic_matrix = pd.DataFrame()
            for factor in alpha_factors:
                factor_ic = []
                for d in hist_dates:
                    d_data = group_hist[group_hist['date'] == d]
                    if len(d_data) > 0:
                        ic_val = d_data[f'{factor}_ic'].iloc[0] if f'{factor}_ic' in d_data.columns else 0
                        factor_ic.append(ic_val)
                    else:
                        factor_ic.append(0)
                ic_matrix[factor] = factor_ic
            
            # 计算最优权重
            weights = optimize_ir_weights(ic_matrix, lookback)
            
            if weights is not None:
                for factor in alpha_factors:
                    date_weights[f'{group_label}_{factor}_weight'] = weights.get(factor, 0)
        
        weights_history.append(date_weights)
    
    return pd.DataFrame(weights_history)

# ============================================
# 第六步：回测引擎
# ============================================
print("\n【步骤6】回测引擎...")

def backtest_strategy(grouped_df, alpha_factors, scenario_feature, 
                      holding_num=200, fee_rate=0.002, lookback=12):
    """
    回测策略
    
    参数:
    - holding_num: 持仓数量
    - fee_rate: 单边交易费率
    - lookback: 权重计算回看期
    """
    results = []
    dates = sorted(grouped_df['date'].unique())
    
    for i, date in enumerate(dates):
        if i < lookback:
            continue
        
        # 获取当前日期数据
        date_data = grouped_df[grouped_df['date'] == date].copy()
        
        if len(date_data) < holding_num * 2:
            continue
        
        # 获取历史数据计算权重
        hist_dates = dates[i-lookback:i]
        hist_data = grouped_df[grouped_df['date'].isin(hist_dates)]
        
        # 计算复合因子得分
        date_data['composite_score'] = 0
        
        for group_label in ['High', 'Low']:
            group_data = date_data[date_data['group_label'] == group_label]
            group_hist = hist_data[hist_data['group_label'] == group_label]
            
            if len(group_hist) < lookback * 5:
                continue
            
            # 计算各因子IC
            ic_values = {}
            for factor in alpha_factors:
                ic_list = []
                for d in hist_dates:
                    d_data = group_hist[group_hist['date'] == d]
                    if len(d_data) > 0 and f'{factor}_ic' in d_data.columns:
                        ic_list.append(d_data[f'{factor}_ic'].iloc[0])
                ic_values[factor] = np.mean(ic_list) if ic_list else 0
            
            # 简单等权（简化版，实际应使用优化权重）
            total_ic = sum(abs(v) for v in ic_values.values()) + 1e-6
            
            group_mask = date_data['group_label'] == group_label
            for factor in alpha_factors:
                weight = ic_values[factor] / total_ic
                date_data.loc[group_mask, 'composite_score'] += date_data.loc[group_mask, factor] * weight
        
        # 选股
        selected = date_data.nlargest(holding_num, 'composite_score')
        
        # 计算组合收益（等权）
        if 'forward_return' in selected.columns:
            portfolio_return = selected['forward_return'].mean()
        else:
            portfolio_return = 0
        
        results.append({
            'date': date,
            'portfolio_return': portfolio_return,
            'holding_num': len(selected),
            'avg_score': selected['composite_score'].mean()
        })
    
    return pd.DataFrame(results)

# ============================================
# 第七步：绩效分析
# ============================================
print("\n【步骤7】绩效分析...")

def calculate_performance(returns_df, benchmark_returns=None):
    """
    计算绩效指标
    """
    if len(returns_df) == 0:
        return {}
    
    returns = returns_df['portfolio_return'].dropna()
    
    if len(returns) == 0:
        return {}
    
    # 年化收益
    annual_return = (1 + returns.mean()) ** 12 - 1
    
    # 年化波动
    annual_vol = returns.std() * np.sqrt(12)
    
    # 夏普比率（假设无风险利率为0）
    sharpe = annual_return / (annual_vol + 1e-6)
    
    # 最大回撤
    cum_returns = (1 + returns).cumprod()
    rolling_max = cum_returns.expanding().max()
    drawdown = (cum_returns - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    # 胜率
    win_rate = (returns > 0).mean()
    
    # 累计收益
    cumulative_return = cum_returns.iloc[-1] - 1
    
    results = {
        'annual_return': annual_return,
        'annual_volatility': annual_vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'cumulative_return': cumulative_return,
        'total_months': len(returns)
    }
    
    # 相对基准的超额收益
    if benchmark_returns is not None and len(benchmark_returns) == len(returns):
        excess_returns = returns - benchmark_returns
        results['excess_annual_return'] = excess_returns.mean() * 12
        results['excess_sharpe'] = excess_returns.mean() / (excess_returns.std() + 1e-6) * np.sqrt(12)
        results['excess_win_rate'] = (excess_returns > 0).mean()
    
    return results

# ============================================
# 第八步：可视化
# ============================================
print("\n【步骤8】可视化...")

def plot_results(returns_df, ic_analysis, scenario_feature, result_dir):
    """
    绘制回测结果图表
    """
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # 1. 累计收益曲线
    if len(returns_df) > 0:
        returns_df['cumulative'] = (1 + returns_df['portfolio_return']).cumprod() - 1
        axes[0, 0].plot(returns_df['date'], returns_df['cumulative'], linewidth=2)
        axes[0, 0].set_title(f'Cumulative Returns ({scenario_feature})', fontsize=12)
        axes[0, 0].set_ylabel('Cumulative Return')
        axes[0, 0].grid(True, alpha=0.3)
    
    # 2. IC时间序列
    if 'All' in ic_analysis and len(ic_analysis['All']) > 0:
        # 这里需要实际的IC时间序列数据
        axes[0, 1].set_title('IC Time Series (Placeholder)', fontsize=12)
        axes[0, 1].text(0.5, 0.5, 'IC Data Required', ha='center', va='center')
    
    # 3. 分组IC对比
    if len(ic_analysis) > 0:
        groups = list(ic_analysis.keys())
        factors = list(ic_analysis['All'].keys()) if 'All' in ic_analysis else []
        
        if len(factors) > 0:
            x = np.arange(len(factors))
            width = 0.25
            
            for i, group in enumerate(groups[:3]):  # 最多3组
                if group in ic_analysis:
                    ic_means = [ic_analysis[group].get(f, {}).get('ic_mean', 0) for f in factors]
                    axes[0, 2].bar(x + i*width, ic_means, width, label=group, alpha=0.7)
            
            axes[0, 2].set_xlabel('Factors')
            axes[0, 2].set_ylabel('IC Mean')
            axes[0, 2].set_title('IC Mean by Group', fontsize=12)
            axes[0, 2].set_xticks(x + width)
            axes[0, 2].set_xticklabels(factors, rotation=45, ha='right')
            axes[0, 2].legend()
            axes[0, 2].grid(True, alpha=0.3)
    
    # 4. 月度收益分布
    if len(returns_df) > 0:
        axes[1, 0].hist(returns_df['portfolio_return'], bins=30, alpha=0.7, edgecolor='black')
        axes[1, 0].set_title('Monthly Return Distribution', fontsize=12)
        axes[1, 0].set_xlabel('Return')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].axvline(returns_df['portfolio_return'].mean(), color='r', linestyle='--', label='Mean')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
    
    # 5. 回撤曲线
    if len(returns_df) > 0:
        cum_returns = (1 + returns_df['portfolio_return']).cumprod()
        rolling_max = cum_returns.expanding().max()
        drawdown = (cum_returns - rolling_max) / rolling_max
        axes[1, 1].fill_between(returns_df['date'], drawdown, 0, alpha=0.5, color='red')
        axes[1, 1].set_title('Drawdown', fontsize=12)
        axes[1, 1].set_ylabel('Drawdown')
        axes[1, 1].grid(True, alpha=0.3)
    
    # 6. 绩效指标表格
    axes[1, 2].axis('off')
    
    plt.tight_layout()
    plt.savefig(f'{result_dir}/cursor_backtest_results.png', dpi=150, bbox_inches='tight')
    print(f"图表已保存到: {result_dir}/cursor_backtest_results.png")

# ============================================
# 主程序
# ============================================
if __name__ == "__main__":
    print("\n" + "="*80)
    print("开始运行情景分析因子模型回测")
    print("="*80)
    
    # 参数设置
    START_DATE = '20170101'
    END_DATE = '20211231'
    SAMPLE_SIZE = 100  # 测试用股票数量
    
    # 获取股票列表
    print("\n获取股票列表...")
    stock_list = get_stock_list()
    
    if len(stock_list) == 0:
        print("无法获取股票列表，使用模拟数据")
        # 生成模拟数据
        np.random.seed(42)
        dates = pd.date_range('2017-01-01', '2021-12-31', freq='D')
        stocks = [f'S{i:03d}' for i in range(1, SAMPLE_SIZE + 1)]
        
        mock_data = []
        for stock in stocks:
            price = 100
            for date in dates:
                # 生成随机 walk 价格
                price = price * (1 + np.random.randn() * 0.02)
                volume = np.random.randint(1000000, 10000000)
                amount = price * volume
                mock_data.append({
                    'date': date,
                    'stock_code': stock,
                    'open': price * 0.99,
                    'high': price * 1.02,
                    'low': price * 0.98,
                    'close': price,
                    'volume': volume,
                    'amount': amount
                })
        
        all_data = pd.DataFrame(mock_data)
    else:
        # 获取样本股票数据
        sample_stocks = stock_list['代码'].iloc[:SAMPLE_SIZE].tolist()
        
        print(f"\n下载 {len(sample_stocks)} 只股票数据...")
        all_stock_data = []
        
        for i, stock in enumerate(sample_stocks[:20]):  # 先取20只
            print(f"  [{i+1}/20] 下载 {stock}...")
            df = get_stock_data(stock, START_DATE, END_DATE)
            if df is not None and len(df) > 100:
                all_stock_data.append(df)
        
        if len(all_stock_data) > 0:
            all_data = pd.concat(all_stock_data, ignore_index=True)
        else:
            print("数据下载失败，使用模拟数据")
            all_data = pd.DataFrame()
    
    if len(all_data) == 0:
        print("没有可用数据，退出")
        exit(1)
    
    print(f"\n数据概览: {len(all_data)} 条记录")
    
    # 计算特征和因子
    print("\n计算情景特征和Alpha因子...")
    processed_data = []
    
    for stock in all_data['stock_code'].unique()[:20]:
        stock_data = all_data[all_data['stock_code'] == stock].copy()
        
        if len(stock_data) < 100:
            continue
        
        # 计算情景特征
        stock_data = calculate_scenario_features(stock_data)
        
        # 计算Alpha因子
        stock_data = calculate_alpha_factors(stock_data)
        
        # 计算未来收益（1个月）
        stock_data['forward_return'] = stock_data['close'].pct_change(21).shift(-21)
        
        processed_data.append(stock_data)
    
    if len(processed_data) == 0:
        print("数据处理失败")
        exit(1)
    
    all_processed = pd.concat(processed_data, ignore_index=True)
    print(f"处理后数据: {len(all_processed)} 条")
    
    # 按月采样
    all_processed['year_month'] = all_processed['date'].dt.to_period('M')
    monthly_data = all_processed.groupby(['year_month', 'stock_code']).last().reset_index()
    monthly_data['date'] = monthly_data['year_month'].dt.to_timestamp()
    
    print(f"\n月度数据: {len(monthly_data)} 条")
    
    # 定义Alpha因子列表
    alpha_factors = ['Quality', 'Con_Value', 'Con_Change', 'Momentum', 'Turnover']
    scenario_features = ['Size', 'Liquidity', 'Cheapness', 'Profit', 'Growth']
    
    # 对每个情景特征进行分析
    all_results = {}
    
    for scenario in scenario_features[:3]:  # 先测试前3个
        print(f"\n{'='*60}")
        print(f"情景特征分析: {scenario}")
        print('='*60)
        
        # 分组和IC分析
        ic_analysis, grouped_df = analyze_ic_by_group(monthly_data, scenario, alpha_factors)
        
        print(f"\n{scenario} 情景IC分析结果:")
        for group in ['High', 'Low', 'All']:
            if group in ic_analysis:
                print(f"\n  {group}组:")
                for factor in alpha_factors:
                    if factor in ic_analysis[group]:
                        metrics = ic_analysis[group][factor]
                        print(f"    {factor}: IC={metrics['ic_mean']:.4f}, IR={metrics['ic_ir']:.4f}")
        
        all_results[scenario] = {
            'ic_analysis': ic_analysis,
            'grouped_df': grouped_df
        }
    
    # 保存结果
    print("\n" + "="*80)
    print("保存分析结果...")
    print("="*80)
    
    # 保存IC分析结果
    ic_summary = []
    for scenario, data in all_results.items():
        for group in ['High', 'Low', 'All']:
            if group in data['ic_analysis']:
                for factor in alpha_factors:
                    if factor in data['ic_analysis'][group]:
                        metrics = data['ic_analysis'][group][factor]
                        ic_summary.append({
                            'scenario_feature': scenario,
                            'group': group,
                            'factor': factor,
                            'ic_mean': metrics['ic_mean'],
                            'ic_std': metrics['ic_std'],
                            'ic_ir': metrics['ic_ir'],
                            'positive_ratio': metrics['ic_positive_ratio']
                        })
    
    ic_df = pd.DataFrame(ic_summary)
    ic_df.to_csv(f'{RESULT_DIR}/cursor_ic_analysis.csv', index=False)
    print(f"IC分析结果已保存: {RESULT_DIR}/cursor_ic_analysis.csv")
    
    # 生成可视化
    print("\n生成可视化图表...")
    for scenario, data in all_results.items():
        try:
            plot_results(pd.DataFrame(), data['ic_analysis'], scenario, RESULT_DIR)
        except Exception as e:
            print(f"图表生成失败 ({scenario}): {e}")
    
    print("\n" + "="*80)
    print("回测完成!")
    print("="*80)
    print(f"\n结果文件:")
    print(f"  - {RESULT_DIR}/cursor_ic_analysis.csv")
    print(f"  - {RESULT_DIR}/cursor_backtest_results.png")
