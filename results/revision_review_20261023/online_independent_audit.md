# 在线驱动独立审计：2026-10-23

范围：只读审查 `scripts/review_online_20261023.py`，未修改源文件或其他代理的工作。新构造及回执仅写入本目录 `online_independent_audit*`。判定针对冻结的闭块快照实验，不扩展为生产系统、每样本更新或开放块耐久性证明。

**判断：当前有效且不重叠的 chunk 输入下，未发现 past-only、过期数据救答、全局持久字节收费或 first/report 组合的阻断性错误。** 需要限定拒绝洞标签和查询年龄的含义；它们不影响认证正确性。

代码快照：

- online SHA256：`366c446dbc538818753049711526d7e1b1ee7ee3ebcf5adb286b7ef04314902e`
- core SHA256：`6ffa3462733abd162d9a6d612464ef5bec9ead680335b0f9d83330d36d44d637`
- 独立检查脚本：本目录 `online_independent_audit.py`
- 完整机器回执：本目录 `online_independent_audit.json`

## 实际执行与结果

独立构造使用2个随机流、2频道、8决策、300/500/1,000字节三档容量及四种在线方法。每两决策关闭一个块，按持久文件解码后直接枚举相容 support；oracle 不调用 core `_state` 或 `_compatible`。分数非单调且允许并列。查询覆盖每个 prefix 的全部子集，数值报告以源记录逐字节核对。

| 检查 | 实际数值 |
|---|---:|
| 快照条件 | 96 |
| 全子集查询 | 16,320 |
| 查询前将预载 source 置空 | 16,320 |
| 改写全部未来后缀、核对过去快照不变 | 24 |
| 淘汰块 | 30 |
| 拒绝块 | 10 |
| 部分覆盖查询 | 8,208 |
| 错误认证或可避免拒答 | 0 |

另独立扫描现有正式目录 `online_snapshots` 中232个已保存文件、22,330个目录项。检查所有文件的实际大小、header horizon、目录条目边界、payload 起止范围、无重叠、无未收费尾部字节。**字节或重叠违规为0，最大容量使用比为1.0。** 此结构扫描不代替每个真实数据 query 的语义审计；原正式驱动另执行其原始记录比较。

## 关键判断依据

**Past-only。** close(lo,hi) 仅选择 `[lo,hi)` 的原子，传入 high/usability 的 `[:hi]`；清理后的 header 用当前 `now=hi`。adaptive 在当时快照和当前关闭块的实际大小上作选择，不读取事件标签或未来 query。未来扰动检查核对相同 prefix 的二进制快照相同。冻结完整 source 预载于评价进程属于输入模拟，不能当作 archive-owned 内存；但 source 不能进入查询答案。

**无过期救答。** query 从当前文件重新读取 frame、header、目录及相交 payload，不从 self.chunks 的旧对象或 self.s 读取数值/支持。遗漏目录范围增加可能 high 数上界，保留正点可以回答 yes，但不能据此补出一个缺失前缀的 exact first。独立检查把 `ar.s=None` 后执行全部16,320个查询，仍正确；已淘汰数据没有用于救答。

**组合正确性。** 不重叠块的 min/max high count 可相加；缺失索引作为自由未知位置。全局 earliest possible 为各块及缺失位置候选的最小值，全局 latest forced first 为保证非空的块之最早强制界。只有二者一致且存在性已确定才认证 first。complete_report 要求 total lower=upper=保留数值数，因数值为已知正点且无重复，在当前模型内足以排除任何未返回 high。空查询可正确返回 no 与完整空报告；这不是物理正常性判断。

**收费。** FRAME、真实JSON、每个ENTRY和所有payload共计全局实际大小；header只收费一次。目录保留完整块的范围，缺口不被隐式解释成无high。当前有效 writer 每个闭块只追加一次，正式目录独立扫描未发现重复/重叠。`read_bytes` 只累加 payload，不含 header/目录读取；summary 的 `mean_payload_read` 命名准确，正文不能改称总I/O字节。

**闭块与资源。** 驱动只在 block closure 序列化并安排 query，close_p95 是关闭块及写快照耗时，不是每决策更新p95。peak_open是声明的原子和位图数量；tracked_transient是部分可见 payload/原子计数，未计全体 Python、zlib临时对象或查询的 horizon-sized 数组，不是总RAM峰值。当前正文若已写为下界及闭块实验，则无需改源。

## 必须保持的语义限定

1. **`rejected_hole` 是离线归因。** 它读取未计入持久文件的 self.rows 全历史拒绝记录。该字段不影响 support、first 或 report；但客户端仅凭当前收费归档无法区分某缺口此前被拒绝还是已过期。正文应称“offline rejected-range overlap”，不可把原因标签包装成持久服务保证。若未来必须从归档返回此原因，则需额外收费保存拒绝日志。
2. **`cross_boundary` 是部分覆盖。** 当前定义是一个 query 同时有 retained 和 missing 索引。跨两个已保留 chunk、且无缺口的 query 为 false。因此准确称谓是 partial coverage 或 crossing the retained/unavailable boundary，不能称所有跨chunk查询。
3. **`age` 是查询末端年龄。** 计算为 `now−1−query_end`，不是自首个 high 或原触发点经过的时长，也不是反馈延迟或人员反应时间。past_high workload 由截至当前已观察的 highs 选锚点；scheduled workload按既定位置构造。两者都不是观测到的用户请求频率。
4. 长度字段是请求长度，早期 prefix 会截短且不同请求可能得到相同索引集合。clamped age 也可能重复。它们可作软件压力查询，不能视为新增独立事件或精确经验用户分布。
5. writer 的应用前提是合法、不重叠的 lo/hi、有效频道以及诚实编码器；接口没有全面防御任意损坏文件、重复close或越界频道。实际 run_one 和已扫描文件满足前提，因此是非阻断性输入验证边界。

## 对稿件可使用的结论

> The closed-block adapter was independently checked on 96 finite snapshot conditions and 16,320 subset queries, including expiration, rejected blocks and partially covered scopes. Query answers were unchanged when access to the preloaded stream was removed. Future-suffix perturbations left past snapshot bytes unchanged. A separate structural scan found no capacity or overlapping-directory violation in 232 saved experiment snapshots. These checks concern the declared logged-record service, not open-block durability, total process memory or operational safety.

以上独立检查不证明 adaptive 更优，也不增加真实 incident 样本量。方法选择是否带来使用价值须由正式32条件和块宽敏感性中的服务、保留期及成本结果判断，包含失败。
