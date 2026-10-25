# 2026-10-23 近邻理论与期刊定位核对

本文件仅负责文献及主张定位；不宣称新实验已经完成。依据本轮完整审稿意见中与理论、应用任务及期刊匹配有关的条目，以及当前正文第 1–3 节。使用 agent-reach 网页/Exa 路由、literature-review；技术判断仅依据原始论文、作者机构全文及官方产品文档。检索日期：2026-10-23。

## 调研结论

- **认证、局部完整性、unknown 并非本文独立理论创新。** Razniewski 与 Nutt 明确区分局部表完整性和查询完整性，并研究从前者推导后者；本文应把自己的覆盖元数据放进这一已知框架。全文核对到 §3.3、§5.2、§7，而非仅看摘要。[PVLDB 原文](https://www.vldb.org/pvldb/vol4/p749-razniewski.pdf)
- **确定性必须随输出语义定义。** Libkin 说明，简单地对可能世界的答案取元组交集不能普遍代表完整的确定知识。本文应声明 yes/no、first 原子和完整报告是不同类型输出，不能把某些肯定元组已知等同于整个报告完整。[IJCAI 原文](https://www.ijcai.org/Proceedings/15/Papers/609.pdf)
- **产品文档支持历史复核场景，不能替代价值效果实验。** Grafana 允许按时间、标签和状态检查历史转换与触发值，即使静默或 mute timing 生效仍显示状态事件；它没有给出本文查询的使用频率、精确位级数值的必要性或人员效率证据。[Grafana 官方文档](https://grafana.com/docs/grafana/latest/alerting/monitor-status/view-alert-state-history/)
- **实际约束应以服务要求及实测成本组织。** Prometheus 官方描述完整压缩、按时间/大小保留、远程读写以及开放块/WAL成本；这支持研究完整性与保留期之间的选择，不能支持“真实系统只允许几十 KiB”的主张。[Prometheus 官方存储文档](https://prometheus.io/docs/prometheus/latest/storage/)
- **ESWA 的应用系统路径成立，但不能靠改名承担创新。** 作者指南当前范围包括智能系统的设计、开发、测试、实施及管理，也重视实际指导意义；范围匹配不等于结果足以录用。[ESWA 官方作者指南](https://www.sciencedirect.com/journal/expert-systems-with-applications/publish/guide-for-authors)

## 供正文使用的英文段落

以下为可直接整合的提议文本。先保留方法层面的措辞；新增实验的结果必须在实际运行后填入，不能先写出胜负。

### 理论定位段（约 110 词）

Reliable answers from incomplete history have an established theoretical basis. Local completeness statements can entail the completeness of a query, and concrete retained facts can support additional inferences [@razniewski2011completeness]. Certainty also depends on the semantics assigned to both stored information and query outputs [@libkin2015certain]. We use these ideas to specify the monitoring service; certification and abstention are not new principles. Our empirical question is which representation meets a declared historical review task after its metadata, numerical payload and expiration policy are charged to the same budget. The contribution must therefore be established by the resulting service–cost boundaries, including comparisons with complete compression and summaries that retain their own completeness semantics.

### 应用任务段（约 120 词）

We operationalize historical review as two executable tasks. Trigger reconstruction returns whether a specified channel crossed its recorded rule within an interval and, when established, its first recorded high-score atom. Report reconstruction returns the requested high-score records together with an explicit statement of which portions are complete or unavailable. These tasks are consistent with monitoring interfaces that expose state changes and evaluated values, including history retained while notifications are muted [@grafana2026statehistory]. Exact numerical recovery is one declared audit service, not a universal operator requirement. A secondary service permits specified time and value tolerances. The evaluation measures reconstruction relative to the original logged output; it does not measure fault resolution, analyst time, safety, or causal root attribution.

### 本文增量定位（结果形成后，须按实测改写）

The study develops an executable selection protocol for monitoring-history services. It asks first whether complete reversible history satisfies the required horizon and access cost. Where it does not, it compares the answers retained by coverage-aware summaries, support maps and numerical filling under common online arrivals and byte accounting. The relevant increment is the measured boundary between a complete service, a narrower service and unavailable evidence. In particular, the experiments test whether charging completeness metadata and using residual capacity changes the apparent ordering of summaries, and whether choices made from past prefixes preserve the requested future service. These are empirical questions within a known completeness framework, not claims of a new database certainty theory.

本段是研究问题及可评估增量，不是已证实的结果。若过去选择的政策不能稳定保持未来服务，应报告失败及原因；不可用上述文字暗示成功。

## 对当前定义与解码器的具体约束

以下是本文方法设计的推论，不是引用论文直接给出的监控算法。

1. 令 retained state 的语义为所有与其记录、边界、角色、计数及完整性标记相容的原始历史集合。只有这些历史对**所请求的完整类型输出**给出同一结果，才认证该完整输出。known-positive 是独立的确定信息，应参与 first 判断，而不必重复属于另一个 coverage 容器。
2. first 的可认证条件是：返回已知正点中最早的点，并能排除查询中所有严格更早的位置。不要不必要地要求其自身再进入负覆盖范围。查询 {1,2,3} 中已知 1、2 为负，保留正点 3，即可认证 first=3。
3. 给 summary 完整的角色语义：完整处理的 bucket/channel 上 first-high 与 last-high 可排除其前后相应范围；只保留数值原子而忘记角色会人为削弱摘要。
4. 没有某个 channel 的摘要行，不能自动代表该 channel 没有 high。完整接纳桶的元数据必须确定频道全集和空组语义，或显式保存空组，并把成本计入。
5. `min/max` 必须声明是高分集合内的 score 极值还是所有观测值的极值。两者服务不同。定量 score 的取值、序列位置和记录载荷不可混用。
6. 部分 high 明细可作为已知记录返回，但必须独立标注 `report_complete=false`。一个正见证能认证“存在”，并不认证“这是全部”。
7. 全部返回 unknown 是声称 soundness 的空洞方法。应在小域穷举相容历史，对每个表示状态和查询同时核对 false certification 与 avoidable refusal。统计上不能把大量相同状态的重复查询当作新增独立应用样本。
8. 容差服务仍须有明确输出及误差界。比如返回 earliest-time 范围和 score 区间，并检查所有相容历史都落在容差内；不能把选择的一个近似点误当保证。

## 近邻理论的查核记录

| 来源与获取范围 | 已核实的具体关系 | 不应据此声称 |
|---|---|---|
| Razniewski, S., Nutt, W. (2011). *Completeness of Queries over Incomplete Databases*. PVLDB 4(11), 749–760. [全文](https://www.vldb.org/pvldb/vol4/p749-razniewski.pdf), [出版元数据/DOI](https://dl.acm.org/doi/10.14778/3402707.3402715). 阅读 §3.3、§5.2、§7 与结论。 | 一般完整性推断已有理论；完整性断言的根据必须可信。本文 metadata 是执行收集规程留下的证明前提。 | 不能把本文字节预算、在线压缩或实测监控结果归给该文；也不能说该文只讨论“全库完整”。 |
| Libkin, L. (2015). *How to Define Certain Answers*. IJCAI 2015, 4282–4288. [全文](https://www.ijcai.org/Proceedings/15/Papers/609.pdf), [官方条目](https://www.ijcai.org/Abstract/15/609). 阅读 §1、§5–7。 | 应说明输出对象的语义，并区分确定的部分信息和完整答案。 | 不应把我们的简单 interval 判定写成其一般理论的证明，也不应断言“所有 certain answers 都只是交集”。 |

书目注意：PVLDB DOI 已与出版索引交叉核对。IJCAI 官方 PDF 与条目均未列 DOI；ACM 的归档索引 URL 含 `10.5555/2832747.2832854`，本次新增 bib 使用官方 URL，**不把归档索引号当作已由官方给出的 DOI**。页码由 PDF 4282–4288 核实。

## ESWA 近年相关文献：有用但不强行扩展为直接竞争者

选择逻辑：保留与监控决策、解释性证据及实际资源评价相邻的论文。没有发现并全文核实到与本稿完整问题完全同构的近期 ESWA 论文；这不是“此前不存在”的证据。压缩和不完整查询的最接近工作来自数据库领域，应当正面引用，不能为凑目标刊引用而替换为无关检测器。

| 来源/已获取范围 | 可用于正文的关系及限制 |
|---|---|
| Strem et al. (2025), *APT: Alarm Prediction Transformer*, ESWA 261, 125521; DOI [10.1016/j.eswa.2024.125521](https://doi.org/10.1016/j.eswa.2024.125521). [DFKI 作者机构全文](https://www.dfki.de/fileadmin/user_upload/import/16205_1-s2.0-S0957417424023881-main.pdf), §3、§4.1、§4.4、§5。 | 结合事件与信号预测未来告警，在两个真实焚烧厂及一个模拟流程数据上评价。可说明监控系统论文需要清晰任务和应用验证。它评价前瞻预测，本稿评价已产生输出的历史重建；不是本稿归档算法基线。其人类/安全动机不能转借为本稿已测到的效益。原 bib 已有，不重复加入。 |
| Mejri et al. (2024), *Unsupervised anomaly detection in time-series: An extensive evaluation and analysis of state-of-the-art methods*, ESWA 256, 124922; DOI [10.1016/j.eswa.2024.124922](https://doi.org/10.1016/j.eswa.2024.124922). [作者上传的出版全文](https://arxiv.org/pdf/2212.03637v3.pdf), §4 与 §5.3–5.6。 | 评价不仅包含常规检测指标，也包含模型大小、稳定性及异常类型。可支持“应用适用条件与成本应被检验”的评价取向；它没有证明本稿特定存储限制或查询价值。原 bib 已有。 |
| Young et al. (2022), *Parameterisation of domain knowledge for rapid and iterative prototyping of knowledge-based systems*, ESWA 208, 118169; DOI [10.1016/j.eswa.2022.118169](https://doi.org/10.1016/j.eswa.2022.118169). [作者机构条目](https://strathprints.strath.ac.uk/81726/), [出版页](https://www.sciencedirect.com/science/article/pii/S0957417422013380)。本次取得出版摘要/机构摘要和全文链接元数据，**未成功取得正文**。 | 使用 rise/fall/fluctuate/stable 形式化知识并用于 Tennessee Eastman 模拟流程。可用于有限的一句背景对比：可解释诊断知识与可重建历史记录是不同任务。不能依据摘要推断其数据保留结构、运行成本或证明其不能支持某种查询。非必要引用，新增 bib 供选择。 |
| Park & Shim (2026), *A plug-in module for detecting and explaining anomalies in inter-variable dependencies in multivariate time series*, ESWA 316, 131906; DOI [10.1016/j.eswa.2026.131906](https://doi.org/10.1016/j.eswa.2026.131906). [作者机构元数据/摘要](https://pure.seoultech.ac.kr/en/publications/a-plug-in-module-for-detecting-and-explaining-anomalies-in-inter-/)。**仅摘要已核实**。 | 解释的是依赖结构偏移，且在 SWaT/WADI 检测评价；本文不能把保留 score 原子称为同等诊断解释。原 bib 已有；无需为增加目标刊引用强行加入。 |

APT issue year 2025，但 DOI 和 online date 属 2024；Mejri 的 issue year 2024，arXiv 初版 2022、v3 为 2024。引用应按出版版本，不能误称为 2022 出版的 ESWA 文。

## 官方功能证据与应用主张边界

| 官方页面（2026-10-23 核对） | 支持 | 不支持 |
|---|---|---|
| [Grafana alert state history](https://grafana.com/docs/grafana/latest/alerting/monitor-status/view-alert-state-history/) | 查看时间/标签/状态转换、对应表达式值；被静默时仍有状态历史；可对后端历史查询。 | 本稿使用的任一 query 分布、阈值精确数值具有普遍必要性、first 记录改善人工判断。 |
| [Prometheus storage](https://prometheus.io/docs/prometheus/latest/storage/) | 高效完整压缩、本地和远程存储、按时间和大小保留；大小限制与缓冲/WAL、压实临时空间应区分。 | 全进程内存硬上限、真实部署仅有 64/256 KiB、本文原型等同生产 TSDB。 |
| [ESWA author guide](https://www.sciencedirect.com/journal/expert-systems-with-applications/publish/guide-for-authors) | 应用智能系统设计/测试/管理与实际指导的文章路径；原创贡献仍需说明。 | 精确录用概率；仅提供大量软件检查即达到发表标准。 |

获取限制：ScienceDirect 直接浏览部分页返回 403；Exa 取得官方作者指南正文；Jina 请求作者指南附近页面返回混入脚本的无效内容，未据其作结论。上述两篇理论论文、APT、Mejri 均通过 PDF 正文阅读；Young 和 Park 明确保留为摘要层证据。未使用社交媒体或登录后内容。

## 给主代理的整合建议

1. 主文新增一个紧凑的 completeness/certain-answer 段，不需要把数据库理论改写成冗长新定理。方法中直接定义相容历史、输出服务和保证边界。
2. 用覆盖语义强摘要、剩余预算填充、统一在线过期和 past-only 选择的实测结果承接增量。只有实验真实改变选择或明确服务边界，才可写“practical guidance”。
3. 可保留已有 detector/evaluation 引用，但相关工作重心移到完整性、查询与压缩。APT、Mejri 是应用/评价邻居，不是压缩竞争者。
4. 不建议新增没有直接使用价值的目标刊引用。两篇理论文为核心新增；Young 为可选背景。

## 来源列表

- [Completeness of Queries over Incomplete Databases — PVLDB full text](https://www.vldb.org/pvldb/vol4/p749-razniewski.pdf)
- [PVLDB publisher metadata](https://dl.acm.org/doi/10.14778/3402707.3402715)
- [How to Define Certain Answers — IJCAI full text](https://www.ijcai.org/Proceedings/15/Papers/609.pdf)
- [IJCAI official abstract and page reference](https://www.ijcai.org/Abstract/15/609)
- [APT — DFKI full text](https://www.dfki.de/fileadmin/user_upload/import/16205_1-s2.0-S0957417424023881-main.pdf)
- [Mejri et al. — published full text, author deposit](https://arxiv.org/pdf/2212.03637v3.pdf)
- [Young et al. — author institution](https://strathprints.strath.ac.uk/81726/)
- [Park and Shim — author institution](https://pure.seoultech.ac.kr/en/publications/a-plug-in-module-for-detecting-and-explaining-anomalies-in-inter-/)
- [Grafana alert state history](https://grafana.com/docs/grafana/latest/alerting/monitor-status/view-alert-state-history/)
- [Prometheus storage](https://prometheus.io/docs/prometheus/latest/storage/)
- [ESWA author guide and current scope](https://www.sciencedirect.com/journal/expert-systems-with-applications/publish/guide-for-authors)

Agent Reach v1.5.0 已检查为当前最新。没有安装或更新任何插件。
