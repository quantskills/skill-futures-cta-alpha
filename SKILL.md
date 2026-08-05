---
name: futures-cta-alpha
description: >-
  Commodity-futures CTA factor library — computes a structured date×variety factor
  panel (time-series & cross-sectional momentum, carry/roll, term structure,
  positioning/COT, inventory, volatility). Use when the user asks for 商品期货因子、
  CTA 信号、动量/carry/期限结构/库存/持仓因子, a factor panel for futures backtesting,
  or futures factor IC. Fills the ecosystem gap of ZERO futures factor libraries
  (vs 10 for equities). Emits factor values for the factor toolchain
  (factor-evaluate / ic-analysis / backtest), NOT human-readable reports.
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-futures-cta-alpha
  repository_url: https://github.com/quantskills/skill-futures-cta-alpha
  project_type: skill
  collection: futures-cta-alpha
  creator: 13817660341-coder
  creator_url: https://github.com/13817660341-coder
  maintainer: 13817660341-coder
  maintainer_url: https://github.com/13817660341-coder
quantSkills:
  project_type: skill
  category: factor-library
  tags:
    - futures
    - commodity
    - cta
    - factor-library
    - momentum
    - carry
    - term-structure
    - pandadata
  platforms:
    - claude-code
    - codex
    - hermes
    - openclaw
    - cursor
  status: stable
  # Pandadata is required only by fetch_futures_panel.py. compute_factors /
  # validate_factors / ic_check / build_continuous are pure pandas — feed your
  # own daily panel and the price + carry factors run with no Pandadata at all.
  requires:
    - skill-pandadata-api
  validation_level: runnable
  maintainer_type: community
  summary_zh: >-
    商品期货 CTA 因子库：计算 date×品种×因子 的结构化因子面板（时序/截面动量、carry/展期、
    期限结构、持仓、库存、波动率），对接 factor-evaluate / ic-analysis / backtest 工具链，
    填补生态"股票 10 因子、期货 0 因子"的空白。方向经真实 IC 校准：中国商品是反转市，
    carry 与全球相反，且 IC 显著 ≠ 可交易。
  summary_en: >-
    Commodity-futures CTA factor library producing a structured factor panel
    (momentum, carry, term structure, positioning, inventory, volatility) for the
    factor toolchain — filling the ecosystem's zero-futures-factor gap. Directions
    are calibrated on real IC: China commodities are a reversal market, carry is
    inverted vs global, and significant IC does not imply tradeability.
---

# Futures CTA Alpha

商品期货因子库，对标股票侧 `skill-factor-alpha191-alpha101`。输入 Pandadata 期货数据，
输出 **date×品种×因子 的结构化因子面板**，供 `factor-evaluate` / `ic-analysis` / `backtest`
等工具链直接消费。填补生态最大结构性空白：**股票侧 10 个因子库，期货侧 0 个**。

> 定位边界：本库**只计算因子值**，**不生成研判报告、不做投资建议、不写策略代码**。

## 已验证信号（2018–2026 真实 IC，详见 references/l3-evidence-ic.md）

价格类因子方向经真实数据 IC 校准——**中国商品是反转市，全球动量先验大面积失效**：

**IC 显著性**（横截面预测力）：

> ⚠️ **t 列为 t_iid（未订正）**。T+20 的相邻日度 IC 共享 19/20 收益窗口，旧的
> `t = IR×√N` 公式高估约 3–4.5 倍。`ic_check.py` 已改用 Newey-West(lag=h−1)，
> 但下表尚未在原始面板上重算。订正后 **`lowvol` / `breakout_55` / `st_reversal_5` /
> `tsmom_252_21` 不再显著**，仅反转类站得住——详见 `references/l3-evidence-ic.md` 文首订正说明。

| 因子 | IC@T+20 | t_iid ⚠️ | 实测方向 |
|---|---|---|---|
| **lowvol** | +3.8% | +5.7 | ⚠️ 订正后不显著 |
| ts_slope (contango) | +4.1% | +5.1 | ❗ 先验反（中国 contango 跑赢） |
| carry_ann | −4.1% | −5.1 | ❗ 先验反（与全球相反） |
| tsmom_252_21 (12-1) | +2.1% | +3.1 | ✅ 长动量弱正 |
| **tsmom_63 / ema_xover / breakout** | −7% / −5.5% / −2.4% | −11 / −9 / −4 | ❗ 强反转（先验反） |

**可交易性**（周调组合、扣 4bp 净 Sharpe）——⚠️ **IC 显著 ≠ 能赚钱**：

| 因子 | 净 Sharpe | |
|---|---|---|
| **ts_slope**(carry 反) | **+0.59** | ⭐最佳，回撤 −14% |
| **tsmom_63**(反转) | +0.46 | 稳 |
| lowvol | −0.02 | IC 最强却**净 Sharpe≈0**（价差太小） |
| tsmom_252_21 | −0.25 | 净负 |
| **组合**（去冗余+实测符号） | **0.58** | 年化 +9%，回撤 −25% |

> 一句话：**中国商品可交易 alpha = 反转 + carry-反转（做多 contango），全球的"动量 + 做多
> backwardation"在中国全反。组合 Sharpe ~0.58（周调净值）。** 库存/持仓类需 Pandadata **待测**。

---

## 与 skill-futures-deepview-analyst 的分工（重要 · registry 判重关键）

二者用**相同数据源**（basis / 期限结构 / 持仓 / 库存），但**产物与下游完全正交**：

| | futures-deepview-analyst | 本库（futures-cta-alpha） |
|---|---|---|
| 角色 | 分析师**看盘写报告**（analyst） | 因子研究员**算因子面板**（factor library） |
| 产物 | 人读中文研判报告（MD/HTML） | `date×variety×factor` 结构化面板（parquet/csv） |
| 数据用法 | 单品种/单日快照的**定性研判** | 全品种时序面板的**定量因子** |
| 下游 | 给人看 / 交 `ssquant` 写策略 | 交 `factor-evaluate`/`ic-analysis`/`backtest` |

**硬性边界（写死在实现里）：**
1. **不生成研判报告**——那是 deepview 的活；本库只产因子面板 + 因子字典。
2. **输出对齐股票因子库格式**（`date, variety, factor_name, value`）。
3. 数据虽同走 `pandadata-api` 期货接口，但用途是**全品种批量时序因子计算**，非单品种快照。
4. 用户若要研判/策略 → **反向 handoff 给 `futures-deepview-analyst` / `ssquant-*`**。

> 类比：deepview ↔ `a-share-stock-dossier`（个股报告）；本库 ↔ `factor-alpha191-alpha101`（因子库）。
> 同数据、不同产物，是生态既有的健康分层关系。

---

## 核心工作流

1. **确定品种池与区间**：默认活跃主力品种全集，日频，指定 `start/end`。
2. **构建连续合约**：`build_continuous.py` 按成交/持仓换月，产出后复权连续价 + 展期日志。
   方法与坑见 `references/continuous-contract.md`。
3. **拉取因子输入面板**：`fetch_futures_panel.py` 走 `pandadata-api` 期货接口，汇集
   日线 OHLC/OI、期限结构、基差、库存/仓单、持仓/多空比、现货利润为一张 tidy 面板。
   接口路由见 `references/data-map.md`。
4. **计算因子**：`compute_factors.py` 纯 pandas 在面板上算因子（见 `references/factor-catalog.md`），
   **仅用 ≤t 数据防泄漏**，输出原始因子值（不做择时、不做标准化）。
5. **校验**：`validate_factors.py` 查泄漏（因子不得含未来）、覆盖率、nan 率、常量列、极端值。
6. **落盘**：`factors/YYYYMMDD.parquet`，schema `date, variety, factor_name, value`。

---

## 因子概览

7 个因子族、约 22 个因子（完整计算式/接口/方向假设见 `references/factor-catalog.md`）：

- **A 时序动量**（★★★ CTA 基石）：`tsmom_252/252_21/63`、`breakout_55`、`ema_xover_20_100`
- **B 截面动量**（★★）：`xsmom_252_21`、`xsmom_63`
- **C Carry/展期**（★★★ 商品最稳健）：`carry_ann`、`roll_return_63`、`basis_mom_20`、`vol_scaled_carry`
- **D 期限结构**（★★）：`ts_slope`、`ts_curvature`
- **E 持仓/情绪**（★ 方向需实测）：`oi_price_confirm_20`、`broker_net_chg_5`、`ls_ratio_z`、`virtual_ratio_chg`
- **F 库存/仓单/现货**（★★）：`inventory_mom_20`、`receipt_mom_20`、`spot_profit_z`
- **G 波动率/反转**（★★）：`lowvol`、`st_reversal_5`

---

## 质量标准

- **防未来函数**：因子在 `t` 日只用 `≤t` 数据；`validate_factors.py` 强制校验。
- **展期正确性**：连续合约换月不得引入跳空虚假收益；`roll_return` 与展期日志可对账。
- **方向假设即先验**：catalog 的 `IC±` 是先验，**必须过 `ic-analysis` 实测**才写入结论；
  参考本仓 `disclosure` 类经验——经验直觉常被数据推翻（如"易主=利好"）。
- **可复现**：相同品种池+区间+数据快照，因子面板一致。
- **不做投资建议**：只产因子值，报告/策略/择时交下游。

---

## 免责声明

> 本因子库仅供量化研究参考，因子方向假设需实测验证，不构成任何投资建议。
