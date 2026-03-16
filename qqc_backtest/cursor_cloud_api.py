#!/usr/bin/env python3
"""
Cursor Cloud API 调用脚本
使用Cursor Cloud Agents API生成QQC回测脚本
"""

import requests
import base64
import json
import time
import os

# 配置
CURSOR_API_KEY = "crsr_12005277b6adafaea78a77e5fbae1c0221d1fe11b5f0fea429a3487da29b4338"
GITHUB_REPO = "https://github.com/ou_0517d70816281d68ada6056720964f2f/qqc-backtest-repo"
BASE_URL = "https://api.cursor.com"

# Basic Auth编码 (API_KEY:)
auth_string = base64.b64encode(f"{CURSOR_API_KEY}:".encode()).decode()
headers = {
    "Authorization": f"Basic {auth_string}",
    "Content-Type": "application/json"
}

# 提示词
prompt_text = """在本仓库中：
1) 阅读并分析《量化多因子系列（1）：QQC综合质量因子与指数增强应用》研报的核心逻辑（QQC六大类因子、沪深300增强、因子权重与约束）。
2) 生成完整的 Python 回测脚本，要求：
   - 使用 akshare 获取 A 股真实行情与基本面数据
   - 实现 QQC 相关因子计算（盈利能力、成长能力、营运效率、盈余质量、安全性、公司治理）
   - 沪深300成分股内选股
   - 滚动IC_IR加权
   - 行业/市值/个股权重约束（行业偏离≤5%，个股偏离≤1%）
   - 月度调仓，单边费率 0.3%
   - 输出净值与绩效指标（年化收益、超额收益、跟踪误差、信息比、最大回撤、月度胜率）
   - 脚本需可直接运行，数据源仅用 akshare
   - 数据存储到 E:\\openclaw\\data\\ 目录

请生成完整、可直接运行的Python脚本。"""

# 创建Agent任务
def create_agent():
    url = f"{BASE_URL}/v0/agents"
    
    payload = {
        "prompt": {
            "text": prompt_text
        },
        "model": "claude-4.5-sonnet-thinking",
        "source": {
            "repository": GITHUB_REPO,
            "ref": "main"
        },
        "target": {
            "autoCreatePr": True,
            "branchName": f"cursor/qqc-backtest-{time.strftime('%Y%m%d')}"
        }
    }
    
    print("="*60)
    print("创建Cursor Cloud Agent任务")
    print("="*60)
    print(f"API URL: {url}")
    print(f"Repository: {GITHUB_REPO}")
    print("-"*60)
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            return result.get('id')
        else:
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"请求失败: {e}")
        return None

# 轮询Agent状态
def poll_agent(agent_id, max_retries=60, interval=10):
    url = f"{BASE_URL}/v0/agents/{agent_id}"
    
    print(f"\n轮询Agent状态: {agent_id}")
    print("="*60)
    
    for i in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('status')
                
                print(f"[{i+1}/{max_retries}] Status: {status}")
                
                if status == "FINISHED":
                    print("\n✓ Agent任务完成!")
                    print(f"结果: {json.dumps(result, indent=2)}")
                    return result
                elif status in ["FAILED", "ERROR"]:
                    print(f"\n✗ Agent任务失败!")
                    print(f"错误: {result}")
                    return None
            else:
                print(f"[{i+1}/{max_retries}] Error: {response.status_code}")
                
        except Exception as e:
            print(f"[{i+1}/{max_retries}] 请求异常: {e}")
        
        time.sleep(interval)
    
    print("\n轮询超时!")
    return None

# 主函数
def main():
    # 创建Agent
    agent_id = create_agent()
    
    if not agent_id:
        print("\n创建Agent失败!")
        return
    
    print(f"\nAgent ID: {agent_id}")
    
    # 轮询等待完成
    result = poll_agent(agent_id)
    
    if result:
        print("\n" + "="*60)
        print("任务完成! 请检查GitHub仓库的PR/分支获取生成的脚本")
        print("="*60)
        
        # 保存结果
        result_path = "/home/node/.openclaw/workspace/qqc_backtest/cursor_agent_result.json"
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"结果已保存: {result_path}")
    else:
        print("\n任务失败或超时")

if __name__ == "__main__":
    main()
