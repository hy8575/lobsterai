# Auto Factor Pipeline Skill

自动监控研报目录，使用 Cursor Cloud Agent 提取/审核因子，
生成计算脚本并执行完整回测流程。

## 触发方式

1. **定时任务**: 每 10 分钟扫描 /data/quant/研报 目录
2. **手动**: `python3 /data/quant/scripts/auto_factor_pipeline.py --pdf <path>`

## 流程

`
PDF → 推送GitHub → Cursor Agent提取 → Cursor Agent审核(循环)
    → 验证 → 生成计算脚本 → 因子计算 → 回测 → 报告
`

## 环境变量

- CURSOR_API_KEY: Cursor Cloud API Key
- GITHUB_TOKEN: GitHub PAT
- GITHUB_REPO: 仓库名 (默认 hy8575/lobsterai)

## 升级条件

- 审核超过 5 轮仍未通过 → 生成 ESCALATION.txt
- 因子计算失败 → 生成 ESCALATION.txt
- 回测失败 → 生成 ESCALATION.txt

所有中间产物保存在 /data/quant/_manifests/research_run_<run_id>/