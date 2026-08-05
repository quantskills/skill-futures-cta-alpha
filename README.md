# skill-futures-cta-alpha

**简体中文** | [English](README.en.md)

商品期货 CTA 因子库，对标股票侧 `skill-factor-alpha191-alpha101`。输入 Pandadata 期货数据，
输出 **date×品种×因子** 的结构化因子面板，供 `factor-evaluate` / `ic-analysis` / `backtest`
直接消费。

> 📖 **完整使用指南见 [USAGE.md](USAGE.md)** —— 安装、两条数据路径、管线四步、输入面板格式、
> 常见场景、实测可用信号（哪些因子真能交易）。

- **填生态最大空白**：股票侧 **10 个**因子库，期货侧 **0 个**。
- **与 `skill-futures-deepview-analyst` 互补**：deepview 用相同数据产**人读研判报告**；本库产
  **结构化因子面板**。同数据、不同产物、不同下游（详见 SKILL.md「与 deepview-analyst 的分工」）。
- **只算因子、不做研判/策略/择时**——报告交 deepview，策略交 ssquant。

## 结构

```
SKILL.md                       # 方向/定位 + 工作流 + 与 deepview 分工
references/
  factor-catalog.md            # 22 个因子：计算式 + 数据接口 + 方向假设 ⭐
  data-map.md                  # 面板列 → Pandadata 期货接口路由
  continuous-contract.md       # 连续合约 + 展期收益方法
  output-schema.md             # 因子面板字段 + 校验契约
scripts/
  fetch_futures_panel.py       # 从 Pandadata 汇集因子输入面板（依赖 pandadata-api）
  build_continuous.py          # 后复权连续合约 + roll_return（纯 pandas，可离线测）
  compute_factors.py           # 因子引擎（纯 pandas，可离线测）⭐
  validate_factors.py          # 因子面板校验器
  ic_check.py                  # 因子 IC 自检（L2→L3 证据；完整归因交 skill-ic-analysis）
references/l3-evidence-ic.md   # 真实 IC 检验结果：中国商品是反转市，先验被推翻 ⭐
```

## 因子族（22 因子，7 族）

| 族 | 因子 | 先验 |
|---|---|---|
| A 时序动量 | tsmom_252/252_21/63, breakout_55, ema_xover_20_100 | ★★★ |
| B 截面动量 | xsmom_252_21, xsmom_63 | ★★ |
| C Carry/展期 | carry_ann, roll_return_63, basis_mom_20, vol_scaled_carry | ★★★ |
| D 期限结构 | ts_slope, ts_curvature | ★★ |
| E 持仓/情绪 | oi_price_confirm_20, broker_net_chg_5, ls_ratio_z, virtual_ratio_chg | ★ |
| F 库存/仓单 | inventory_mom_20, receipt_mom_20, spot_profit_z | ★★ |
| G 波动/反转 | lowvol, st_reversal_5 | ★★ |

## 快速开始

```bash
pip install pandas numpy pyarrow

# 1) 构建连续合约（或直接用你的主力/连续价面板）
python scripts/build_continuous.py --contracts contracts.parquet --out cont.parquet

# 2) 汇集因子输入面板（需 pandadata-api；或自备 panel.parquet）
python scripts/fetch_futures_panel.py --varieties RB M CU --start 20220101 --end 20241231 --out panel.parquet

# 3) 计算因子面板
python scripts/compute_factors.py --panel panel.parquet --out factors/all.parquet

# 4) 校验后交下游
python scripts/validate_factors.py factors/all.parquet
# -> factor-evaluate / ic-analysis / backtest
```

## 免责

> 本因子库仅供量化研究参考，因子方向假设需实测验证，不构成任何投资建议。

## License

GPL-3.0-only

---

## 📜 License

Copyright (C) 2026 the QuantSkills contributors.

This program is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version. This program is
distributed WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See [LICENSE](LICENSE) for details.
