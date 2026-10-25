# 2026-10-23 独立只读审计

审查范围：`review_archive_core_20261023.py`、`review_experiments_20261023.py`。未修改代码、正文、既有结果或书目。在线驱动尚不在此次审查范围；不能由本报告推导其已通过因果到达、FIFO 或容量审计。

审查快照：

- core SHA256：`6ffa3462733abd162d9a6d612464ef5bec9ead680335b0f9d83330d36d44d637`
- experiments SHA256：`ae901929ca8496120901fe69f9ba6a13531e74ed95df4290a544113ee51c7758`

## 判断与优先修复

**当前结论：核心认证公式未发现阻断性错误；有限枚举与独立扩展检查在下述模型内通过。发表主张仍需限定其范围。** 代码实现的是声明的 eligible-high 记录服务，不是物理异常、安全或人员行为保证。

| 优先级 | 发现 | 最小修复及主张边界 |
|---|---|---|
| P1，复现入口 | experiments 第111行接收 `--fine` 和 `--online`，但 main 仅使用 `--pilot`。目前两参数会静默运行 coarse static。 | 由各独立驱动承担时删除或显式拒绝这两参数，并记录真实入口；不能据这些参数的执行日志声称已跑 fine/online。 |
| P1，审计与版本一致 | 读到的既有有限世界回执曾记录 core `fbb4d5c0...`，与本次 core 快照不同。 | 最终代码冻结后重跑其 selfcheck，确保回执、正式运行和交付代码 SHA 一致；本报告的独立检查只覆盖上列 SHA。 |
| P1，保证范围 | 64-world 代码枚举六决策的二元 support，不枚举全部 float32 score/value/version 世界。 | 写为有限 support-state 穷举，配合数值自由度的语义论证；不写为全数值状态穷举、任意在线系统证明或普遍安全证明。 |
| P2，容差解释 | `empirical_tolerance` 是已知原始 first 的离线匹配成功率：时间差≤1决策、score/value绝对差≤0.01、version相同。它不是所有相容历史上的容差证书。 | 保留 empirical/observed fidelity 标签，列清单位及数值尺度。跨 cadence 比较时，1 coarse 决策和1 fine 决策对应不同名义时长；统一时间容差，或明确为不同服务条件。 |
| P2，结果分母 | complete_report 包含空/负查询，这些报告可能是正确的空集合。脚本也独立输出 complete_positive。 | 主结果同时给正查询完整报告及负查询认证，不只给汇总 complete_report 比率。incident/channel/backbone 不能算独立 incident。 |
| P2，在线适用条件 | `_summary` 的 last/extrema 是关闭 bucket 的完整角色；`_changes` 用到关闭 parent/chunk 内的 last/extrema。`merge_archives` 假设 retained chunks 不重叠。 | 在线仅在 block 关闭后形成这些摘要，开放缓冲明确另计；在线驱动验证 chunk 非重叠、past-only 入选、过期范围未知。不要将 final-history 候选选择误称逐样本无缓冲算法。 |

## 表示语义和公平性

1. `_summary` 显式生成每个完整 bucket/channel 的组，包括 count=0 的空组。因此没有把“没有保留某 channel 行”免费解释成无 high。部分接纳只接收完整组，遗漏组保持未知；角色、计数及压缩后的组元数据均计入实际 payload。first、last、minimum、maximum 均是 **high 集合内 score** 的位置，不能称原始测量值的全时段极值。
2. `_state` 同时利用完整 support、保留正数值、首末外侧的负位置及组基数约束。它不会要求一个已有正见证再次属于另一个 coverage 容器才能认证 first。count 可能进一步强制剩余位置全部为 high 或 low。这比只有 witness 的弱摘要基线更完整。
3. usability 是单独收费、channel-shared 的 decision 位图。unusable 在声明服务里没有 eligible high，但不同于观测到的 below-threshold；query 同时返回两个计数。负回答只表示声明的 high 集合为空，不表示该区间物理正常。数据若要支持每频道不同的可用性，必须换 schema，不能直接套此 shared 位图。
4. encode 的输入是 frozen atoms/high/usability/header；事件和 dimension 标签只进入 queries/离线 truth，不传给编码器。uniform time-rank fill 不优先补救失败查询。静态 header 可以带已知全历史 provenance，因此它是 retrospective comparison；在线应调用清理后的 prefix header，不能把未来到达数组或最终 horizon 保存在在线入选状态。
5. 所有布局均收费实际 frame、JSON、usability、group/support/numeric/fill。method 在快照内使用固定32字符栏位，避免方法名称长度带来无关预算差。full 比较两个完整可逆编码并选实际较小者；adaptive 优先检查 full 是否已适用。full 本身不适用时返回收费的 refusal，未把超过预算候选作为可用答案。
6. `_changes` 当前按真实 parent/channel 分组，保持已有 first/last/min/max/change 的选择逻辑；不是任意 bucket 改名。bitmap 完整保存 support，numeric 可裁减，故不能把 binary support 和 numeric report 混为同一终点。
7. build_seconds 是 Python 实现的实际候选构造时间，包括为每方法计算 full 候选的开销。它不是数据库引擎吞吐比较。decode/merge 产生 horizon-sized 易失数组；其 RAM、缓存和在线 query 延迟必须另测，不能由持久字节上限推导总内存有界。

## 有限世界审计的最强可辩护范围

原 selfcheck 的全部64个 support 世界采用 n=6、单频道，七种 archive 配置，每一配置检查全部64个查询子集（不仅是连续区间）。它在给定已解码状态下独立筛出相容 support，然后核对 yes/no/unknown、first 位置以及 complete high-record report 是否一致，并检查可避免拒答。另有不可用输入、完整范围外正见证、分块合并和未来未覆盖位置的构造例。

这足以作为实现回归与小域模型检查；它不是所有流、所有预算和所有编码输入的数学证明。原有限测试的 score 随时间单调，无法单独充分测试 extrema 角色的实际选择，也不直接覆盖多个频道与部分组接纳。本次补充独立检查覆盖了这些情形，见下一节。

对任意已由本编码器生成、组区间互不重叠的有效状态，可以另给简洁的数值语义论证：相容 support 必须保留已知 first/last/min/max 正位置与完整组计数；其他未保留 high 的 score 可以赋为该组已保留 first 的 score，仍满足已有 extrema 值和角色，亦不会在既有 first 之前创造 high。即使 score 因极值相等而唯一，未保留的 window-last float32 在本服务中仍无外部函数约束。因此不能由 score 角色恢复整个原始16-byte atom。这个结论依赖 **未存数值没有额外可推导约束、原始日志而非模型可重新计算、组来自诚实编码器** 的声明；若额外保存了确定值函数或模型输入，则须重新分析。

允许的论文表述：

> We exhaustively checked the support semantics on a six-decision domain and tested additional multichannel, nonmonotone-score and partial-admission cases. The numeric-report criterion assumes that an unretained window-last value has no further retained determining constraint. These checks establish finite-domain implementation agreement with the declared service, rather than exhaustive verification of all numerical histories or a production-system safety guarantee.

`_compatible` 对 support 的枚举不读取 score extrema 的值域；它只要求极值位置为正。因此应将上段数值扩展论证写在方法/补充材料，不能把 oracle 本身说成已经枚举并校验所有 numeric role 约束。

## 独立扩展执行结果

本审查通过内联只读 Python（`-B`，未保存额外脚本或运行输出文件）另构造了8个随机 frozen-stream 案例，每例8决策、2频道。score 从4个值随机选择，包含非单调和并列值；window-last 独立随机。使用八类配置，含宽度2/3/8、无限候选、严格小预算、fill、bitmap、full/refusal。直接从解码 schema 枚举256种单频道 support，独立构造查询真值，没有调用 core `_state` 或 `_compatible`。

实际结果：

| 项目 | 数值 |
|---|---:|
| 原始随机案例 | 8 |
| 频道 | 2 |
| 每案例决策 | 8 |
| archive 条件 | 64 |
| 部分组接纳档案 | 11 |
| 完整拒绝档案 | 8 |
| 全部查询子集检查 | 32,768 |
| 错误认证/可避免拒答 | 0 |

同时核对 min/max high count、exact first、完整 numeric-report 判定、roundtrip numeric 字节以及有限预算不超限。此检查不是额外独立 incident，不增加应用样本量。没有审查 root 正在编写的在线驱动，也未重跑全部真实数据；正式性能和实际服务收益仍须以该轮结果为依据。

## 非阻断性稳健性说明

编码器已检查 atom 总数与 high 总数一致及每个 atom 都处于 high。若未来允许外部自带输入，可再显式检查输入 `(t,ch)` 唯一；当前 decoder 会拒绝保留的重复 numeric，但仅“总数相同且都落在 high”并不在逻辑上排除某 high 被遗漏而另一 high 重复。现有受控生成管线未发现该问题。本研究的证书前提应是有效、未损坏且由声明编码器产生的归档；当前不是防恶意损坏文件的通用验证器。

## 可复现补记

按主代理要求，已把原内联扩展检查保存为 `scripts/review_independent_semantics_20261023.py` 并重新执行。正式回执为本目录 `independent_semantics_audit.json`。保留同一 seed、八个随机案例、64个 archive 条件、11个部分接纳、8个拒绝以及32,768个查询检查，结果仍为零错误/可避免拒答；core SHA 与上列快照一致。初次“未保存脚本”的描述仅指初次运行，现已具有可执行复现入口与脚本 SHA。
