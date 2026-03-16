#!/usr/bin/env python3
"""
调用Cursor API使用opus4.6生成QQC回测脚本
"""

import requests
import json
import os

CURSOR_API_KEY = "crsr_12005277b6adafaea78a77e5fbae1c0221d1fe11b5f0fea429a3487da29b4338"

# Cursor API endpoint (可能需要根据实际情况调整)
# 尝试不同的可能端点
API_URLS = [
    "https://api.cursor.com/v1/chat/completions",
    "https://cursor.com/api/v1/chat/completions",
    "https://gateway.cursor.sh/v1/chat/completions",
]
API_URL = API_URLS[0]  # 使用第一个

headers = {
    "Authorization": f"Bearer {CURSOR_API_KEY}",
    "Content-Type": "application/json"
}

# QQC回测脚本生成Prompt
prompt = """你是一个专业的量化研究员，请根据中金公司QQC综合质量因子研究报告，生成一个完整的Python回测脚本。

## QQC综合质量因子六大维度：

1. **盈利能力**(Profitability): CFOA(经营现金流/总资产)、ROE(净利润/净资产)、ROIC(净利润/投入资本)
2. **成长能力**(Growth): OP_SD(营业利润稳健加速度)、NP_Acc(净利润加速度)、OP_Q_YOY(营业利润单季度同比)、QPT(业绩趋势因子)、NP_Q_YOY(净利润单季度同比)
3. **营运效率**(Operation): ATD(总资产周转率变动)、OCFA(产能利用率提升)
4. **盈余质量**(Accrual): APR(应计利润占比=应计利润/营业利润)
5. **安全性**(Safety): CCR(现金流动负债比率=经营净现金流/流动负债)
6. **公司治理**(Governance): 流通股占比、管理层薪酬、管理层持股数量、受处罚情况(负向)、是否实施股权激励

## 指数增强模型：
- 底层因子：QQC(核心，权重≥50%) + 估值因子(BP_LR、DP、EEP) + 动量因子(Momentum_24M) + 换手率因子(VA_FC_1M) + 一致预期因子(EEChange_3M)
- 权重分配：滚动24个月IC_IR加权，QQC强制≥50%
- 约束条件：行业偏离≤5%，个股偏离≤1%，市值暴露≤5%

## 回测参数：
- 时间范围：2011-01-01 至 2020-12-31 (样本内2011-2018，样本外2019-2020)
- 调仓频率：月度
- 交易成本：单边0.3%
- 选股范围：沪深300成分股

## 要求：
1. 使用akshare获取真实A股数据
2. 数据存储到 E:\\openclaw\\data\\ 目录
3. 完整的因子计算逻辑
4. 组合优化求解（使用cvxpy或scipy）
5. 输出回测结果：净值曲线、年化收益、年化超额、跟踪误差、信息比、最大回撤、月度胜率
6. 生成详细的回测报告

请生成完整的、可直接运行的Python脚本。由于代码可能较长，请分多次返回，每次返回一个完整的模块或函数，并告诉我是否还有后续代码。"""

data = {
    "model": "opus-4.6",
    "messages": [
        {"role": "system", "content": "You are a professional quantitative researcher specializing in factor investing and index enhancement strategies."},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.7,
    "max_tokens": 8000
}

for api_url in API_URLS:
    print(f"\n正在尝试API端点: {api_url}")
    print("-" * 60)
    
    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print("\n生成的代码:\n")
            print(content[:2000] + "..." if len(content) > 2000 else content)
            
            # 保存到文件
            output_path = "/home/node/.openclaw/workspace/qqc_backtest/qqc_cursor_opus_part1.py"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"\n代码已保存到: {output_path}")
            break
        else:
            print(f"Error: {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"请求失败: {e}")
        continue
else:
    print("\n所有API端点都失败了。Cursor API可能需要特定的访问方式。")
