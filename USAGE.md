# 使用指南 · skill-futures-cta-alpha

从期货数据算出 **date×品种×因子** 的结构化因子面板，喂给 factor-evaluate / ic-analysis /
backtest。本文覆盖安装、两条数据路径、管线命令、输入面板格式、常见场景、结果解读、实测可用信号。

---

## 目录
1. [安装](#1-安装)
2. [它做什么 / 不做什么](#2-它做什么--不做什么)
3. [两条数据路径](#3-两条数据路径)
4. [管线四步](#4-管线四步)
5. [输入面板格式](#5-输入面板格式)
6. [常见场景](#6-常见场景)
7. [实测可用信号（重要）](#7-实测可用信号重要)
8. [下游对接](#8-下游对接)

---

## 1. 安装
```bash
pip install pandas numpy pyarrow requests
```
`compute_factors` / `validate_factors` / `build_continuous` / `ic_check` 纯 pandas，可离线跑；
只有 `fetch_futures_panel` 依赖 Pandadata（`skill-pandadata-api`）。

## 2. 它做什么 / 不做什么
- **做**：把期货行情/持仓/期限/库存数据 → 22 个 CTA 因子的结构化面板（原始因子值）。
- **不做**：不生成研判报告（交 `futures-deepview-analyst`）、不写策略/择时（交 `ssquant-*`）、
  不做投资建议。方向标签是规则化先验，需 IC 实测。

## 3. 两条数据路径

| 路径 | 覆盖因子 | 依赖 |
|---|---|---|
| **A. Pandadata**（`fetch_futures_panel.py`） | 全 22 因子（含库存/持仓/carry/基差） | `skill-pandadata-api` + 账号 |
| **B. 自备面板**（跳过 fetch，直接喂 `compute_factors`） | 你面板里有的列对应的因子 | 无——任何行情源都行 |

> 价格类（动量/波动/反转）+ carry 只要日线/单合约即可，**不必 Pandadata**（实测就是用新浪主连+单
> 合约跑通的）。库存/持仓类需 Pandadata。缺某列 → 只跳该因子，不报错。

## 4. 管线四步
```bash
# (可选) 1) 主力换月拼接成后复权连续合约 + 展期收益
python scripts/build_continuous.py --contracts contracts.csv --out cont.csv

# 2) 取因子输入面板：路径A(Pandadata) 或 路径B(自备 panel.csv)
python scripts/fetch_futures_panel.py --varieties RB M CU --start 20220101 --end 20241231 --out panel.parquet

# 3) 算因子面板（纯 pandas，核心）
python scripts/compute_factors.py --panel panel.csv --out factors.csv

# 4) 校验后交下游
python scripts/validate_factors.py factors.csv

# (可选) 因子 IC 自检（完整归因交 skill-ic-analysis）
python scripts/ic_check.py --factors factors.csv --panel panel.csv --horizons 5 10 20
```

## 5. 输入面板格式
`compute_factors` 吃一张长表（一行 = 一个 date×品种），列：
- **必需**：`date`(YYYYMMDD)、`variety`、`close`
- **可选**（有则多算对应因子）：`high, low, volume, oi`（动量/突破/OI）；`pn, pf, Dn, Df`（carry/期限）；
  `basis`（基差）；`inventory, warehouse_receipt, spot_profit`（库存/现货）；`broker_net, ls_ratio,
  virtual_ratio`（持仓）；`roll_return`（来自 build_continuous，算展期因子）；`p1,p2,p3`（曲率）
- 字段→接口映射见 [references/data-map.md](references/data-map.md)。

## 6. 常见场景

**A. 只算价格类因子（最简，任意日线源）**
```bash
# panel.csv 至少含 date,variety,close[,high,low,oi] —— 用你的行情源导出
python scripts/compute_factors.py --panel panel.csv --out factors.csv
python scripts/validate_factors.py factors.csv
```

**B. 全 22 因子（Pandadata）**
```bash
python scripts/fetch_futures_panel.py --varieties RB M CU I J --start 20220101 --end 20241231 --out panel.parquet
python scripts/compute_factors.py --panel panel.parquet --out factors.parquet
```

**C. 验证某因子有没有预测力**
```bash
python scripts/ic_check.py --factors factors.csv --panel panel.csv --horizons 20
# 看 mean_ic / t / agree（实测方向是否符合先验）
```

## 7. 实测可用信号（重要）

方向已经真实数据校准（2018–2026, 30 品种，详见 [references/l3-evidence-ic.md](references/l3-evidence-ic.md)）——
**用 `direction` / 组合信号前必看**，因为**全球先验在中国大面积失效**：

| 因子 | 实测 | 可交易性(周调净 Sharpe) |
|---|---|---|
| `ts_slope`（contango） | ❗先验反：中国 contango 跑赢 | **+0.59 ⭐最佳**（回撤 −14%） |
| `tsmom_63`（3月动量） | ❗强反转（反向用） | +0.46 |
| `carry_ann` | ❗与全球相反（backwardation 跑输） | 同 ts_slope 反向 |
| `lowvol` | ⚠️ t_iid=5.7 但订正后不显著 | **≈0**（IC 本就不显著，且价差太小） |
| `tsmom_252_21`（12-1） | ✅ 弱正 | 净负 |

**两条铁律**：
1. **中国商品可交易 alpha = 反转 + carry-反转（做多 contango）**，别做经典趋势跟踪/做多 backwardation。
2. **IC 显著 ≠ 能赚钱**——`lowvol` IC 全库最强却净 Sharpe≈0。方向靠 `ic_check`，能否交易靠组合回测扣成本。

> 库存/持仓类需 Pandadata，**尚未实测**；carry 为新浪单合约 proxy，待 Pandadata 精确复核。

## 8. 下游对接
输出因子面板（`date,variety,factor_name,value`）直接喂：
- `skill-ic-analysis` —— 完整因子 IC/分层归因
- `skill-factor-evaluate` / `skill-factor-optimize` —— 因子评估/参数优化（已兼容期货因子）
- `skill-backtest` 或自建期货回测 —— 组合回测

要研判报告 → `futures-deepview-analyst`；要策略/执行 → `ssquant-ai-trader`。

---
> 本工具输出仅供量化研究参考，因子方向假设需实测验证，不构成任何投资建议。
