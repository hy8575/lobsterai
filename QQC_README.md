# QQC沪深300指数增强回测系统

## 简介

本项目实现了基于中金公司QQC（综合质量因子）的沪深300指数增强策略回测系统。

## 功能特性

### 因子体系

**QQC六大类因子：**
1. **盈利能力**：ROE、ROA、ROIC、毛利率、净利率
2. **成长能力**：营收增长率、利润增长率、营业利润增长率
3. **营运效率**：总资产周转率、存货周转率、应收账款周转率
4. **盈余质量**：应计利润占比、现金流比率
5. **安全性**：资产负债率、流动比率、速动比率
6. **公司治理**：管理层持股、股权激励

**辅助因子：**
- 估值因子（PE/PB/PS）
- 动量因子（3M/6M/12M）
- 换手率因子
- 一致预期因子

### 策略特点

- **IC_IR滚动24月加权**：动态调整因子权重
- **QQC因子权重≥50%**：确保质量因子主导
- **严格约束条件**：
  - 行业偏离度 ≤ 5%
  - 个股偏离度 ≤ 1%
  - 市值因子暴露 ≤ 5%
- **组合优化**：使用cvxpy进行二次规划优化

### 回测设置

- 回测期间：2011-01-01 至 2020-12-31
- 调仓频率：月度
- 交易成本：单边 0.3%
- 基准指数：沪深300（市值加权）

## 安装依赖

### 必需依赖

```bash
pip install numpy pandas matplotlib
```

### 可选依赖

```bash
pip install cvxpy  # 用于高级组合优化
```

> 注：如果不安装cvxpy，系统会自动使用简化优化方法。

## 使用方法

### 方法1：使用运行脚本（推荐）

```bash
python run_backtest.py
```

运行脚本会自动：
- 检查依赖包
- 检测数据目录
- 执行回测
- 生成报告和图表
- 显示结果

### 方法2：直接运行主脚本

```bash
python qqc_backtest_cursor.py
```

## 数据准备

### 数据路径

脚本会按以下优先级查找数据目录：
1. `./data` （当前目录下的data文件夹）
2. `E:\openclaw\data` （Windows绝对路径）

### 数据文件格式

如果有真实数据，请准备以下CSV文件放入 `data/` 目录：

1. **沪深300成分股**：`hs300_components.csv`
   - 字段：code（股票代码）

2. **个股日线数据**：`daily_{股票代码}.csv`
   - 字段：date, code, open, high, low, close, volume, amount

3. **财务数据**：`financial_{股票代码}.csv`
   - 字段：report_date, code, roe, roa, roic, gross_margin, net_margin, 
           revenue_growth, profit_growth, operating_profit_growth,
           asset_turnover, inventory_turnover, receivable_turnover,
           accrual_ratio, cash_flow_ratio, debt_ratio, current_ratio,
           quick_ratio, pe, pb, ps, total_market_cap

4. **指数数据**：`index_000300.csv`
   - 字段：date, close, volume

### 模拟数据模式

如果数据目录为空或不存在，系统会自动生成模拟数据运行回测演示。

## 输出结果

回测完成后，结果保存在 `results/` 目录：

1. **qqc_backtest_report.txt** - 文本格式回测报告
2. **qqc_backtest_results.png** - 可视化图表
   - 净值曲线对比
   - 累计超额收益
   - 回撤曲线
   - 月度超额收益分布
   - 绩效指标表
3. **nav_series.csv** - 净值时间序列
4. **metrics.json** - 绩效指标（JSON格式）

## 回测绩效示例

基于模拟数据的回测结果：

| 指标 | 数值 |
|------|------|
| 组合年化收益率 | 35.91% |
| 基准年化收益率 | 16.78% |
| 年化超额收益率 | 19.14% |
| 跟踪误差 | 3.20% |
| 信息比率 (IR) | 5.98 |
| 夏普比率 | 10.38 |
| 月度胜率 | 88.2% |

> 注：实际绩效取决于真实市场数据。

## 自定义配置

可以在 `qqc_backtest_cursor.py` 的 `Config` 类中修改配置：

```python
class Config:
    # 数据路径
    DATA_PATH = './data'
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
```

## 项目结构

```
.
├── qqc_backtest_cursor.py  # 主回测脚本
├── run_backtest.py          # 运行脚本
├── QQC_README.md           # 本文档
├── data/                    # 数据目录（需手动创建或自动生成）
└── results/                 # 结果目录（自动创建）
    ├── qqc_backtest_report.txt
    ├── qqc_backtest_results.png
    ├── nav_series.csv
    └── metrics.json
```

## 技术说明

### 因子计算

- 财务数据按季度更新，月度沿用最新一期数据
- 因子值进行标准化处理（Z-score）
- 缺失值使用0填充

### IC/IR计算

- IC（信息系数）：因子值与未来收益率的Spearman秩相关系数
- IR（信息比率）：IC均值 / IC标准差
- 滚动窗口：24个月

### 因子加权

- 基于IC_IR加权，IR越高权重越大
- 约束QQC六大类因子总权重 ≥ 50%
- 剩余权重分配给辅助因子

### 组合优化

优先使用cvxpy求解器，包含以下约束：
- 权重和为1，非负约束
- 个股权重相对基准偏离≤1%
- 行业权重相对基准偏离≤5%
- 市值因子暴露≤5%

若cvxpy不可用，降级到简化方法：
- 基于综合得分排序
- 选择前50%股票等权重配置

### 回测流程

1. 每月月初调仓
2. 计算所有因子值
3. 更新IC/IR历史
4. 计算因子权重
5. 计算综合得分
6. 组合优化
7. 计算持仓期收益
8. 扣除交易成本

## 依赖版本

- Python >= 3.8
- numpy >= 1.20.0
- pandas >= 1.3.0
- matplotlib >= 3.3.0
- cvxpy >= 1.1.0 (可选)

## 注意事项

1. **数据质量**：回测结果高度依赖输入数据质量
2. **交易成本**：实际交易成本可能高于回测假设
3. **市场冲击**：大规模资金可能产生市场冲击成本
4. **幸存者偏差**：确保数据包含退市股票
5. **未来函数**：确保因子计算不使用未来信息

## 常见问题

**Q: 为什么回测结果这么好？**
A: 当前使用的是模拟数据。真实数据的回测结果会更加现实。

**Q: cvxpy安装失败怎么办？**
A: 可以不安装cvxpy，系统会自动使用简化优化方法。

**Q: 如何使用真实数据？**
A: 按照"数据文件格式"章节准备CSV文件，放入 `data/` 目录即可。

**Q: 可以修改回测周期吗？**
A: 可以在 `Config` 类中修改 `START_DATE` 和 `END_DATE`。

**Q: 支持其他指数吗？**
A: 可以修改数据加载模块，替换成分股列表和基准指数数据。

## 许可证

本项目仅供学习和研究使用。

## 作者

OpenClaw

## 更新日志

### v1.0.0 (2026-03-16)
- 初始版本发布
- 实现QQC六大类因子
- 实现IC_IR滚动加权
- 实现cvxpy组合优化
- 完整回测报告和可视化
