# Output Schema — 因子面板

输出为 `factors/*.parquet`（或 `.csv`），**长表**，一行 = 一个 date×variety×factor 的因子值。
对齐股票因子库格式，供 `factor-evaluate` / `ic-analysis` / `backtest` 直接消费。

## 字段

| 列 | 类型 | 说明 |
|---|---|---|
| `date` | string(YYYYMMDD) | 交易日；因子仅用 ≤date 数据（防泄漏） |
| `variety` | string | 品种代码（如 `RB` 螺纹、`M` 豆粕、`CU` 铜） |
| `factor_name` | string | 因子代号，见 `factor-catalog.md` / 下方枚举 |
| `value` | float | 因子原始值（未截尾、未标准化；下游按需处理） |

## factor_name 枚举（22）

```
tsmom_252 tsmom_252_21 tsmom_63 breakout_55 ema_xover_20_100
xsmom_252_21 xsmom_63
carry_ann roll_return_63 basis_mom_20 vol_scaled_carry
ts_slope ts_curvature
oi_price_confirm_20 broker_net_chg_5 ls_ratio_z virtual_ratio_chg
inventory_mom_20 receipt_mom_20 spot_profit_z
lowvol st_reversal_5
```

## 约定

- **原始值**：本库不做截面 winsorize/zscore（`ls_ratio_z`/`spot_profit_z` 的 z 是**时序** 60 日
  标准化，属因子定义本身，非截面处理）。截面标准化由下游 `factor-evaluate` 负责。
- **缺因子**：输入面板缺某列 → 该列依赖的因子整体不出现（不是全 nan 行），运行日志登记。
- **方向假设**：每个因子的预期 IC 符号见 `factor-catalog.md`，是**先验**，以 `ic-analysis` 实测为准。

## 校验契约（validate_factors.py）

1. 必填列非空：`date, variety, factor_name, value`
2. 无 `inf/-inf`
3. `(date,variety,factor_name)` 无重复
4. `factor_name` 属已知枚举
5. `date` 为 8 位 `YYYYMMDD`
6. 单因子在 date×variety 网格上缺失率 ≤ 98%（否则视为空因子）
7. 单因子非零方差（拦截常量列）
