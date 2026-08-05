# Data Map — Pandadata 期货接口路由

因子输入面板的字段 → Pandadata 方法映射。所有调用经 `skill-pandadata-api`
确认签名/字段/单位/日期格式，不臆造参数。日期 `YYYYMMDD`，品种/合约带交易所后缀。

## 面板列 → 接口

| 面板列 | 用途因子族 | Pandadata 方法 | 备注 |
|---|---|---|---|
| `close, open, high, low, volume, oi` | A/B/E/G | `get_future_daily` | 主力/指定合约日线；`oi`=持仓量 |
| 主力合约映射 | 连续合约 | `get_future_dominant` | 换月依据（成交/持仓最大合约） |
| 合约元信息（到期日等） | C/D | `get_future_detail` | `Dn/Df` 到期天数来源 |
| `pn, pf, Dn, Df`（近/次月价与到期） | C/D | `get_future_term_structure` | 期限结构；carry/slope 直接用 |
| `basis`（基差） | C | `get_future_basis` | `basis=(现货−近月)/现货` |
| `inventory`（库存） | F | `get_future_inventory` | 交易所/社会库存 |
| `warehouse_receipt`（仓单） | F | `get_future_warehouse_receipt` | 注册仓单量 |
| `spot_profit`（现货/加工利润） | F | `get_future_spot_profit` | 盘面/现货利润 |
| `broker_net`（席位净多） | E | `get_broker_netmarg` / `get_broker_netmarg_change` | 前 N 席位净持仓（受披露规则限制） |
| `net_cap_change`（净资金变化） | E | `get_future_netcap_change` | |
| `ls_ratio`（多空比） | E | `get_future_ls_ratio` | 散户情绪 |
| `virtual_ratio`（虚实盘比） | E | `get_future_virtual_ratio` | 交割博弈 |

## 采集约定

- **先冒烟后批量**：每个方法先单品种单日 `head()/shape` 验证字段与空值原因，再扩区间/品种池。
- **同日对齐**：跨模块因子（如 carry × 库存）必须对齐同一 `trade_date`，不得拼接不同日期。
- **缺列降级**：某数据源缺失时，仅跳过依赖该列的因子（`compute_factors.py` 按列存在性条件计算），
  不整体报错；缺哪些因子在运行日志与 `factors` 元数据里登记。
- **披露限制**：席位持仓仅前若干名，解读"主力"时须注明覆盖度限制（沿用 deepview 的 caveat）。

## 与 deepview-analyst 的调用差异

同样调 `get_future_basis`/`get_future_term_structure` 等，但本库是**全品种、长区间、批量拉取
构面板**（为算时序因子），deepview 是**单品种、单日/短窗、快照式**（为写研判）。用途不同，不判重。
