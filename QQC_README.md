# QQC沪深300指数增强回测系统

## 简介

基于中金公司QQC（Quantitative Quality Control）综合质量因子的沪深300指数增强策略回测系统。

## 文件说明

- **qqc_backtest_cursor.py**: 主回测脚本，包含完整的回测框架
- **run_backtest.py**: 执行脚本，用于运行回测流程
- **QQC_README.md**: 使用说明文档

## 功能特点

### 1. 数据获取
- **优先使用akshare**获取实时A股数据
- **备选本地数据**读取（支持多个数据路径）
- 自动缓存机制，避免重复下载

### 2. QQC六大类因子

#### 盈利能力 (25%)
- CFOA: 经营现金流资产比
- ROE: 净资产收益率
- ROIC: 投资资本回报率

#### 成长能力 (25%)
- OP_SD: 营业利润稳健加速度
- NP_Acc: 净利润加速度
- OP_Q_YOY: 营业利润单季度同比
- NP_Q_YOY: 净利润单季度同比
- QPT: 业绩趋势因子

#### 营运效率 (15%)
- ATD: 总资产周转率变动
- OCFA: 产能利用率提升

#### 盈余质量 (15%)
- APR: 应计利润占比

#### 安全性 (10%)
- CCR: 现金流动负债比率

#### 公司治理 (10%)
- FLOAT_RATIO: 流通股比例
- MGMT_PAY: 管理层薪酬
- MGMT_HOLD: 管理层持股
- PENALTY: 处罚记录
- EQUITY_INCENTIVE: 股权激励

### 3. 辅助因子

- BP_LR: 账面市值比
- DP: 股息率
- EEP: 盈利收益率
- Momentum_24M: 24月动量
- VA_FC_1M: 1月换手率
- EEChange_3M: 3月盈利预期变化

### 4. 组合优化

- **IC_IR滚动24月加权**（QQC因子权重≥50%）
- **约束条件**：
  - 行业偏离 ≤ 5%
  - 个股偏离 ≤ 1%
  - 市值暴露 ≤ 5%
- **优化方法**：
  - 优先使用cvxpy进行凸优化
  - 提供简化优化方法作为降级方案

### 5. 回测框架

- 时间范围: 2011-2020
- 调仓频率: 月度
- 交易成本: 单边0.3%
- 基准: 沪深300指数（市值加权）

### 6. 绩效评估

输出指标：
- 年化收益率
- 年化超额收益
- 跟踪误差
- 信息比率
- 最大回撤
- 月度胜率
- 净值曲线图表

## 安装依赖

### 必需依赖

```bash
pip install numpy pandas matplotlib
```

### 可选依赖

```bash
# akshare - 用于下载实时数据
pip install akshare

# cvxpy - 用于组合优化
pip install cvxpy

# 或一次性安装所有依赖
pip install numpy pandas matplotlib akshare cvxpy
```

## 使用方法

### 方法1: 使用run_backtest.py（推荐）

```bash
# 基本用法（使用本地数据）
python run_backtest.py

# 下载最新数据后运行
python run_backtest.py --download

# 指定数据和结果路径
python run_backtest.py --data-path ./data --results-path ./results

# 查看帮助
python run_backtest.py --help
```

### 方法2: 直接运行主脚本

```bash
python qqc_backtest_cursor.py
```

## 数据要求

### 数据目录结构

```
data/
├── hs300_constituents.csv    # 沪深300成分股列表
├── index_000300.csv           # 沪深300指数数据
├── stock_000001.csv           # 个股日线数据
├── stock_000002.csv
└── ...
```

### 数据来源

1. **优先使用akshare**（推荐）
   - 自动下载最新数据
   - 支持全市场股票
   - 需要安装: `pip install akshare`

2. **本地数据**（备选）
   - 将数据文件放在 `./data` 或 `E:\openclaw\data` 目录
   - CSV格式，包含日期、开盘、收盘、最高、最低、成交量等字段

### 默认数据路径

脚本会按顺序查找以下路径：
1. `./data`
2. `E:\openclaw\data`
3. `./qqc_backtest/E:\openclaw\data`

## 输出结果

### 结果目录结构

```
results/
├── nav_curve.csv              # 净值曲线数据
├── performance_metrics.json   # 绩效指标
├── backtest_results.png       # 可视化图表
└── backtest_report.md         # Markdown报告
```

### 绩效指标示例

```json
{
  "annual_return": 0.12,
  "benchmark_annual_return": 0.10,
  "annual_excess_return": 0.02,
  "tracking_error": 0.05,
  "information_ratio": 0.40,
  "max_drawdown": -0.15,
  "monthly_win_rate": 0.65,
  "total_return": 1.45,
  "benchmark_total_return": 1.20
}
```

## 配置参数

可在 `qqc_backtest_cursor.py` 中修改 `Config` 类的参数：

```python
class Config:
    # 回测时间范围
    START_DATE = "20110101"
    END_DATE = "20201231"
    
    # 调仓频率 (M=月度, Q=季度)
    REBALANCE_FREQ = "M"
    
    # 交易成本 (单边0.3%)
    TRANSACTION_COST = 0.003
    
    # QQC因子权重
    DIMENSION_WEIGHTS = {
        'Profitability': 0.25,
        'Growth': 0.25,
        'Operation': 0.15,
        'Accrual': 0.15,
        'Safety': 0.10,
        'Governance': 0.10
    }
    
    # 组合约束
    MAX_STOCK_DEVIATION = 0.01     # 个股偏离≤1%
    MAX_INDUSTRY_DEVIATION = 0.05  # 行业偏离≤5%
    MAX_SIZE_EXPOSURE = 0.05       # 市值暴露≤5%
```

## 注意事项

1. **数据不足处理**：当财务数据不足时，会使用现有股票做演示
2. **公司治理因子**：由于数据获取困难，采用简化处理（中性值）
3. **财务数据更新**：财务数据按季度更新，月度调仓时沿用上一季度数据
4. **基准构建**：使用市值加权构建沪深300基准
5. **优化降级**：当cvxpy不可用时，自动使用简化优化方法

## 性能优化建议

1. **使用缓存**：首次运行会下载并缓存数据，后续运行速度更快
2. **减少股票数量**：可在代码中调整 `sample_stocks` 数量进行快速测试
3. **并行计算**：可使用多进程加速因子计算（需修改代码）

## 故障排除

### 问题1: akshare下载失败

**解决方案**：
- 检查网络连接
- 使用本地数据作为备选
- 或使用其他数据源

### 问题2: cvxpy优化失败

**解决方案**：
- 系统会自动降级到简化优化方法
- 或安装cvxpy: `pip install cvxpy`

### 问题3: 内存不足

**解决方案**：
- 减少回测时间范围
- 减少股票池大小
- 增加系统内存

## 扩展开发

### 添加新因子

1. 在 `FactorCalculator` 类中添加计算方法
2. 在 `Config.FACTOR_WEIGHTS` 中配置权重
3. 在 `calculate_all_factors` 中调用

### 修改优化方法

1. 修改 `PortfolioOptimizer` 类
2. 自定义目标函数和约束条件

### 自定义回测逻辑

1. 继承 `BacktestEngine` 类
2. 重写 `run` 方法

## 参考文献

- 中金公司: QQC综合质量因子研究报告
- Fama-French: Quality Minus Junk (QMJ) Factor
- 沪深300指数编制方案

## 许可证

MIT License

## 作者

Cursor AI Agent

## 更新日志

- 2026-03-16: v1.0 初始版本发布
  - 完整的QQC因子体系
  - 支持akshare和本地数据
  - cvxpy组合优化
  - 完整的回测框架

## 联系方式

如有问题或建议，请提交Issue。
