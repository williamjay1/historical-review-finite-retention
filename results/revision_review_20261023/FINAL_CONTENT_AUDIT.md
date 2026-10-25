# 终稿内容独立审读：2026-10-23

范围：只读审读合稿 `manuscript/ESWA_Manuscript.md`、`ESWA_Supplementary.md`，并对照本轮完整评估、已执行核心/在线独立检查和结果审计。未修改正文、补充材料或实现。以下定位采用便于 root 整合的 fragment 行号；主稿由这些 fragment 拼接，重新构建后主稿行号可能变化。

**阶段判断：内容修订 GO，存在两处可直接补齐的文字/复现精度问题；未发现要求新增数据、重训或改变主结果的阻断性科学错误。** 这是当前文章类型下的内容判断，不是保证 ESWA 录用。期刊适配路径为应用智能监控系统的历史复核、实现评价与条件化服务选择。

一句话贡献：在同一监控记录、真实字节和时间顺序下，实测完整压缩、完整语义摘要与有限保留分别能提供哪些 exact-first 和 complete-report 服务，并揭示静态优势何时被在线历史竞争反转。

## 优先补齐的两处

### 1. 恢复最小 score 生成规程，避免 frozen 成为方法黑箱

定位：`review_methods_20261023.md` 第7–11行；`review_supplement_20261023.md` 第5–11行。

当前两份稿件说明 frozen、配对、同参数和逐位一致，但删掉了旧版可供读者理解 q/τ 的实际规程：六特征、训练/校准拆分、PCA保留方差、ridge正则及四滞后、残差归一化与阈值校准、ESA粗决策时长。这不影响现有归档程序结果，但影响读者判断 high 记录稀疏性、相关性和成本来自哪条规则。标题中的“监控历史”不是任意未定义的分数日志。

最小修复：在S1补约150–200词已经执行且原版已准确记载的生成规则，正文3.1指向S1。可保持 detector 不是新贡献；无须追加 detector 比赛或新训练。须保留原来的数值准确性：六特征、PCA90%方差、ridge四个既有滞后及λ=10、校准Q0.95和Q0.995、SMD80/20训练/校准、ESA既有时间拆分与300/180 released-second窗口。实际参数以原配置/运行回执为准，不凭本报告产生新参数。

### 2. exact-first 公式明确排除空与负查询

定位：`review_methods_20261023.md` 第40行；`review_supplement_20261023.md` 第45行。

两处“earliest and latest compatible first positions coincide”须写为 **L>0 且 earliest/latest 相等**。源码已经要求 answer='yes'，因此只是让文字与实现严格一致。负/空查询没有 first，不能因两个空哨兵同为−1被理解为 first certificate。无需重跑实验。

## 建议性小修，不构成停止条件

1. `review_results_discussion_20261023.md` 第34行“Giving summaries their complete roles and counts materially changes the comparison”可以改成“With complete-group semantics, coverage summaries ...”。现表2比较了不同完整表示，不是单独去掉roles而固定全部payload的因果消融。存在性构造和强基线已经证明角色有用，但不应把整个数值差都归因于角色本身。无需为此新增消融，调整归因表述即可。
2. S5目前写了核心28,672及独立32,768检查，尚未简述已完成的在线独立16,320检查与预载源置空/未来扰动。可在S5追加短段并在S6加入两个独立审计入口。它们应放在验证部分，不回到摘要以检查次数代替贡献。
3. Supplement S2第47行的数值扩展论证可具体写“an admitted group's first score”，使其不会被误读为任意一个极值都能赋给更早未知位置而不改变并列极值角色。现有存在性表述并非实质错误，具体化能减少形式化争议。

## 对最新评估核心要求的闭环判断

| 原评估问题 | 当前证据及表述 | 判断 |
|---|---|---|
| 完整压缩很便宜，为什么要有损 | 表1公开57/60粗流与53/56细流在256 KiB完整可行；容量不是客户需求，ρ逐历史计量；三个服务区间由引言和讨论承接。 | 已实质修复。没有靠缩小容量或复制数据制造瓶颈。 |
| certainty/局部完整性不是新理论 | Related2.2与方法3.3直接引用两篇理论全文；下界明确为服务边界，codec/fallback不称创新。 | 已修复。中心增量是条件化实测，非改名。 |
| 摘要被削弱为孤立点 | 完整bucket/channel、空组、首末极值角色及count明确收费；解码利用负边界和基数约束。 | 已修复。强摘要主要结果在正文表2/3，而非隐藏在SI。 |
| 剩余容量未用 | 两种fill及full-if-fits进入116历史的统一静态比较，slack和unsaved同时披露；hard server收益有限也公开。 | 已修复，且改变了完整报告结果。 |
| 实际复核任务不闭合 | 两个明确输出：认证first+原atom、完整high报告。真实异常三记录案例展示first成功而report失败。 | 已修复为可执行任务；没有推成真实人类收益。 |
| bit-exact不是普遍需求 | 主服务明确为replay audit；次级经验容差与不保证discarded value清楚区分。 | 合理边界。容差不增加新atom匹配的负结果也公开。 |
| 粗cadence上游机会不足 | 全56配对fine流纳入，保留327/322/2254等各层分母，细粒度仍缺106/98 annotated-high incidents。 | 已修复；未把归档率当检测率。 |
| 离线与在线脱节 | 同一框架比较四种表示，纳入真实困难粗/细server，32条件5280查询；adaptive失利及Mission1反例都在正文。 | 已修复；并未把静态full-if-fits代入在线结论。 |
| 查询未触及过期历史 | 末端年龄、长度、部分覆盖和拒绝洞分层；scope因block宽变化而不同已明说。 | 已修复，不是伪称真实用户延迟。 |
| 只报0错误而不查过度拒答 | 有限support oracle同时检查soundness和avoidable refusal；独立扩展及在线构造亦通过。 | 已修复，范围未夸大为所有float32世界。 |
| usability语义混淆 | 每格式单独收费shared usability；真实grid无不可用输入明确披露。 | 已修复，未借合成验证声称真实缺失泛化。 |
| 旧反馈/通知研究分散主线 | 新SI围绕S1–S6，旧通知等价/及时丢失/未来retention失败仅作为关联限制保留。 | 叙事已集中，关键负结果未隐藏。 |

## 主要主张、分母及边界

已读 `RESULT_CLAIM_AUDIT.md` 的独立逐项重算，未重复该代理已完成的全量数值工作。其主表、图分母及正文数值均匹配输出；本次另直接抽看了 tolerance_summary.csv 和 fine_task_case.json，二者与第4.3节一致。

- coarse的57/60与fine的53/56是不同设计集合，正文和表1明确区分。116 histories是相关的device/model与mission/model组合，没有被说成116独立部署。
- 2329 positive / 4508全部 annotated scopes分开，negative及unknown不混用分母；Table2 complete-positive与joint-first不是边际计数的暗示交集。
- complete-only静态all-or-refuse是明确参照，不冒充最佳在线完整保留。讨论同时解释了闭块完整存储可以保住近期任务。
- hard server的first与report、byte/slack/unsaved不混为单一“证据保留”；3条记录例子有真实异常source坐标及原atom支持。
- age是query末端年龄，cross-boundary是部分覆盖，rejected洞为未收费实验日志的离线归因；正文已按在线审计修正。
- open/transient成本是部分下界，p95仅闭块/query，未称per-decision延迟或总RAM峰值。
- 过去字节外推仍有false feasible和false infeasible；固定margin来自同规则扩展，未改成赢家挑选或未来保证。
- repeated channels/backbones/queries没有生成显著性。SMD annotated dimensions、ESA affected channels没有被当作物理根因；released time不是deadline。
- 16B不包含低分、完整窗口或waveform；旧36B的特征检查没有借来扩展新预算保证。未存predictor对象和ESA数值重拟合的限制仍在。
- perfect-oracle feedback为模拟，AI实际参与范围如实披露，没有虚构调查、工时、安全或人员错误数据。

## 残余发表风险与合理停止点

当前中心比旧版清楚：结果不再只是“丢了就拒答”，而是完整压缩经常最便宜、强语义和fill改变静态服务、在线年龄竞争又反转静态优势，以及过去尺寸不能保证未来。这些差异由共同实际记录和任务输出检验，而非只靠命名。

剩余风险仍是应用需求没有实测：精确重放与小容量是明确服务条件，而非被证明普遍重要的行业需求。这会影响编辑对应用广度和重要性的判断；正文已据此限制结论。没有依据再要求强行问卷、湿实验、更多seed或无关新数据，也不能保证具体期刊录用。此处合理停止在：补齐最小方法规程、对齐first条件、完成引用/图表及交付一致性，而非继续堆计算掩盖未观测的人类收益。

本报告不审 Word/PDF 版式或图片视觉质量；该部分由专门图表/渲染核验承担。
