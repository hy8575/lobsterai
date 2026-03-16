"""
QQC回测数据下载脚本
使用akshare下载真实A股数据到本地
"""

import os
import sys
import time
import akshare as ak
import pandas as pd
from datetime import datetime

# 数据存储路径
DATA_PATH = r"E:\openclaw\data"
os.makedirs(DATA_PATH, exist_ok=True)

print("="*60)
print("QQC回测数据下载")
print("="*60)
print(f"数据存储路径: {DATA_PATH}")
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

# 1. 下载沪深300成分股
print("\n[1/5] 下载沪深300成分股...")
try:
    hs300 = ak.index_stock_cons_weight_csindex(symbol="000300")
    hs300.to_csv(os.path.join(DATA_PATH, "hs300_constituents.csv"), index=False)
    print(f"      成功: {len(hs300)} 只成分股")
    stock_list = hs300['成分券代码'].tolist() if '成分券代码' in hs300.columns else hs300['code'].tolist()
except Exception as e:
    print(f"      失败: {e}")
    stock_list = []

# 2. 下载沪深300指数数据
print("\n[2/5] 下载沪深300指数数据(2011-2020)...")
try:
    index_df = ak.index_zh_a_hist(symbol="000300", period="daily", 
                                   start_date="20110101", end_date="20201231")
    index_df.to_csv(os.path.join(DATA_PATH, "hs300_index.csv"), index=False)
    print(f"      成功: {len(index_df)} 个交易日")
except Exception as e:
    print(f"      失败: {e}")

# 3. 下载成分股日线数据（前50只）
print("\n[3/5] 下载成分股日线数据...")
sample_stocks = stock_list[:50] if len(stock_list) > 50 else stock_list
print(f"      将下载 {len(sample_stocks)} 只股票的数据")

success_count = 0
for i, stock in enumerate(sample_stocks):
    try:
        stock_code = str(stock).zfill(6)
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date="20110101", end_date="20201231",
                                adjust="qfq")
        if len(df) > 0:
            df.to_csv(os.path.join(DATA_PATH, f"stock_{stock_code}.csv"), index=False)
            success_count += 1
        if (i + 1) % 10 == 0:
            print(f"      进度: {i+1}/{len(sample_stocks)} 只")
        time.sleep(0.5)  # 避免请求过快
    except Exception as e:
        print(f"      {stock_code} 下载失败: {e}")

print(f"      完成: {success_count}/{len(sample_stocks)} 只成功")

# 4. 下载财务数据
print("\n[4/5] 下载财务数据...")
financial_count = 0
for i, stock in enumerate(sample_stocks[:20]):  # 前20只
    try:
        stock_code = str(stock).zfill(6)
        # 主要财务指标
        fin_df = ak.stock_financial_analysis_indicator(symbol=stock_code)
        if len(fin_df) > 0:
            fin_df.to_csv(os.path.join(DATA_PATH, f"financial_{stock_code}.csv"), index=False)
            financial_count += 1
        time.sleep(0.5)
    except:
        pass

print(f"      完成: {financial_count} 只股票的财务数据")

# 5. 生成数据清单
print("\n[5/5] 生成数据清单...")
data_summary = {
    '数据类型': ['沪深300成分股', '沪深300指数', '个股日线', '财务数据'],
    '数量': [len(stock_list), len(index_df) if 'index_df' in locals() else 0, 
             success_count, financial_count],
    '更新时间': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')] * 4
}
summary_df = pd.DataFrame(data_summary)
summary_df.to_csv(os.path.join(DATA_PATH, "data_summary.csv"), index=False)

print("\n" + "="*60)
print("数据下载完成!")
print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)
