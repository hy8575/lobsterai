# QQC回测系统 - 快速开始指南

## 🚀 一分钟快速开始

### 第一步：安装依赖

```bash
pip install numpy pandas matplotlib cvxpy
```

### 第二步：运行回测

```bash
python run_backtest.py
```

就这么简单！

## 📊 查看结果

回测完成后，查看 `results/` 目录：

```
results/
├── qqc_backtest_report.txt      # 文本报告
├── qqc_backtest_results.png     # 可视化图表
├── nav_series.csv                # 净值数据
└── metrics.json                  # 绩效指标
```

### 核心绩效指标

基于模拟数据的示例结果：

- ✅ **年化超额收益**: 19.14%
- ✅ **信息比率**: 5.98
- ✅ **月度胜率**: 88.2%
- ✅ **夏普比率**: 10.38

## 📁 使用真实数据

### 准备数据文件

创建 `data/` 目录，放入以下CSV文件：

```
data/
├── hs300_components.csv          # 沪深300成分股
├── daily_600000.csv              # 个股日线数据
├── daily_600016.csv
├── ...
├── financial_600000.csv          # 财务数据
├── financial_600016.csv
├── ...
└── index_000300.csv              # 指数数据
```

### CSV文件格式示例

**hs300_components.csv**
```csv
code
600000
600016
600019
...
```

**daily_600000.csv**
```csv
date,code,open,high,low,close,volume,amount
2011-01-04,600000,15.20,15.50,15.10,15.40,10000000,154000000
...
```

**financial_600000.csv**
```csv
report_date,code,roe,roa,roic,gross_margin,net_margin,...
2011-03-31,600000,0.15,0.08,0.12,0.35,0.25,...
...
```

## ⚙️ 自定义配置

编辑 `qqc_backtest_cursor.py` 中的 `Config` 类：

```python
class Config:
    START_DATE = '2011-01-01'  # 回测起始日期
    END_DATE = '2020-12-31'    # 回测结束日期
    TRANSACTION_COST = 0.003   # 单边交易成本 0.3%
    QQC_MIN_WEIGHT = 0.50      # QQC因子最低权重 50%
```

## 🔍 理解策略

### QQC六大类因子

1. **盈利能力** - ROE、ROA、ROIC、毛利率、净利率
2. **成长能力** - 营收增长、利润增长、营业利润增长
3. **营运效率** - 资产周转率、存货周转率、应收账款周转率
4. **盈余质量** - 应计利润占比、现金流比率
5. **安全性** - 资产负债率、流动比率、速动比率
6. **公司治理** - 管理层持股、股权激励

### 策略逻辑

```
每月调仓:
  1. 计算所有股票的QQC因子和辅助因子
  2. 基于IC_IR计算因子权重（QQC因子权重≥50%）
  3. 计算每只股票的综合得分
  4. 组合优化（行业偏离≤5%、个股偏离≤1%、市值暴露≤5%）
  5. 执行调仓，扣除交易成本
```

## 💡 常见问题

**Q: 没有真实数据怎么办？**
A: 系统会自动生成模拟数据，可以先体验策略逻辑。

**Q: 回测运行多久？**
A: 通常1-2分钟（取决于股票数量和回测周期）。

**Q: 如何提升性能？**
A: 安装cvxpy可以使用更高效的优化器。

**Q: 结果图表在哪里？**
A: `results/qqc_backtest_results.png`

## 📚 更多文档

详细文档请查看：
- `QQC_README.md` - 完整使用说明
- `qqc_backtest_cursor.py` - 代码注释

## 🆘 需要帮助？

如遇问题，请检查：
1. Python版本 >= 3.8
2. 依赖包是否正确安装
3. 数据文件格式是否正确

---

**祝回测顺利！** 🎉
