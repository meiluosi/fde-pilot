# 系列约定

FDE Skill 系列各自独立运行，通过手动读取的产物衔接，不互相依赖安装。本文件约定编号、结论词和边界，各仓库对应的衔接文件保持一致。

## 系列地图

| Skill | 管什么 | 主要产出 | 结论词 |
|---|---|---|---|
| fde-ramp | 见客户前搭起行业基本盘，拿图去被一线改 | 链路图、活动表、行话表、corrections | 自检分数 |
| fde-problem-framing | 把需求变成有证据的业务问题，比较 AI 与非 AI | 定义卡、诊断底稿、验证计划 | Proceed / Investigate / Non-AI / Stop-Defer |
| fde-route-selection | 业务问题定义之后，先过滤合规与部署等硬约束，再选适配路线，最后用客户样本比选模型的质量、成本与延迟 | 见该仓库 | 见该仓库 |
| fde-knowledge-base | 路线含文档检索（RAG）时，判断知识够不够、怎么治、怎么评、质量卡在哪 | 知识库判断卡、摸底表、治理章程、评测集、诊断日志 | Proceed / Investigate / Pivot / Stop-Defer |
| fde-comms | 与人的关键沟通：访谈、向上汇报、坏消息 | 提纲、纪要、一页汇报稿 | 无（产出文稿） |
| fde-demo | 设计并复盘一次客户 Demo，换验证与信任 | 简报、记录表、复盘 | Proceed / Iterate / Pivot / Stop-Defer |
| fde-pilot | 把 Demo 通过的方案做成可检验的试点并判定成效 | 试点方案、日志、成效报告 | Proceed / Iterate / Pivot / Stop-Defer |

典型顺序：ramp → problem-framing → route-selection → knowledge-base（场景含文档检索时）→ demo → pilot；comms 贯穿各阶段。顺序不是强制，缺哪一环就在入口标“未提供”。knowledge-base 的摸底可早于 demo：Demo 用的是精选文档还是随机抽样的真实文档，须写明。

## 编号命名空间
跨 Skill 引用时加前缀，保留原编号，不覆盖：`ramp:S01`、`framing:V2`、`framing:C01`、`kb:Q01`、`demo:L3`、`pilot:M2`。knowledge-base 内部：摸底样本 `D#`、知识问题 `K#`、评测题 `Q#`、诊断记录 `F#`。本 Skill 内部：记录 `L#`，假设沿用上游 ID。试点内部：指标 `M#`、停止条件 `S#`、假设 `H#`、记录 `P#`。

## 结论词
词相同，含义随阶段不同，跨 Skill 引用时一律带前缀写 `demo:Proceed`。

| 结论 | framing | demo | pilot |
|---|---|---|---|
| Proceed | 所写范围的下一阶段（可去做 Demo/试点），不是上线 | 进入试点范围协商 | 进入正式交付或扩大范围的协商 |
| Investigate / Iterate | 证据不足，先做最小验证 | 某一轴证据不足，再演一轮 | 某一轴证据不足，延长或修正后再试 |
| Non-AI / Pivot | 改用非 AI 方案 | 主张被推翻，转向新发现 | 同左 |
| Stop-Defer | 暂停并写重开条件 | 同左 | 同左 |

knowledge-base 沿用四个词：`kb:Proceed` 是所写范围的原型或首批建设，不是上线；`kb:Investigate` 是权限、环境、治理或摸底证据不足；`kb:Pivot` 是该类问题改走数据查询、实时接口或源系统，或最简方案（现有搜索、目录加状态规则、规则定位加原文直出）已够，不借用 Non-AI；`kb:Stop-Defer` 同左。

## 边界
| 事项 | 归谁 | 另一方做什么 |
|---|---|---|
| 判断问题是否真实、该不该上 AI | framing | demo 只检验其中一条假设，不重新裁定 |
| 把行业图拿给一线改 | ramp 第 4 步 | demo 是它的高保真版本，使用 ramp 的 corrections 作为叙述基础 |
| 与客户访谈、预沟通、坏消息稿的措辞与策略 | comms | demo 定义对外纪要的内容边界（只含事实、确认事项、待确认事项），措辞与沟通策略可交给 comms |
| 对客户预期的管理话术（立项、Demo、上线等阶段） | comms（规划中） | demo 提供 Demo 阶段的事实：范围、已知失败、不做什么 |
| 向高管汇报 Demo 结果 | comms 上行 | demo 复盘提供三轴状态和证据，不替用户措辞 |
| 试点方案、指标与对照设计 | pilot | demo 的 Proceed 复盘提供范围建议与交接字段 |
| 路线含文档检索时：文档摸底、知识治理、评测集、检索与生成的分层诊断、原文兜底 | knowledge-base | framing 提供场景与错误代价；demo 写明所用文档是精选还是随机抽样；pilot 接用其评测集、指标与治理状态 |
| 模型比选、成本、部署与合规约束 | route-selection | knowledge-base 只反馈问题类型分布与环境约束，不选模型 |

## 回写规则
下游发现上游假设被推翻，或客户纠正了流程、术语，写成“回写建议”，由上游 Skill 的修订流程处理；不直接改上游原件。回写建议写明：对象产物、原内容、新证据（带前缀编号）、建议修订。

## 交接字段（demo → pilot）
Proceed 的复盘至少带出：已换到的授权与对接人；尚未拿到的授权；三轴仍未验证的假设；失败样例清单（转为试点护栏和停止条件）；共同作者清单与反向信号清单；现场提出的需求变更；原始基线与口径。
