# fde-pilot · v0.1.0（草案）

FDE Skill 系列的第五个：把通过 Demo 的方案设计成可检验的试点，运行期做启动与期中检查，结束时按**事前登记**的指标判定成效。Demo（fde-demo）换信任和授权，试点换业务结果的证据。可独立运行，不需要安装系列中的其他 Skill，也不修改它们的仓库。系列约定见 [references/series.md](references/series.md)。

## 核心观点
- 指标、对照、判据在试点开始前登记，之后不得替换；事后新增的指标只算探索性发现。
- 使用量不等于价值，准确率提升不等于节时；复核与纠错时间计入业务指标，严重错误在护栏层单列。
- 无对照时只报告相关变化。三轴（使用与采用、业务效果、护栏与可持续）分别判定，再给 Proceed / Iterate / Pivot / Stop-Defer。
- Proceed 是进入正式交付或扩大范围的协商，不是上线授权。

## 安装与使用
将整个 `fde-pilot` 文件夹放入宿主的 skills 目录，保留目录名与 SKILL.md。Codex 常用 `${CODEX_HOME:-$HOME/.codex}/skills/`。已有同名目录时先检查，不覆盖：
```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R -n fde-pilot "${CODEX_HOME:-$HOME/.codex}/skills/"
python3 "${CODEX_HOME:-$HOME/.codex}/skills/fde-pilot/scripts/manifest.py" --check
```
最后一条核对子目录和文件是否齐全。宿主未发现技能时开启新会话。可直接说：
- “用 $fde-pilot 根据这份 Demo 复盘设计试点，先问最影响设计的问题。”
- “检查这份试点方案有没有事前登记完整，对照怎么设计。”
- “试点第 2 周了，做期中检查，看有没有触发停止条件。”
- “根据方案和日志做成效判定。”

## 工程内容
- SKILL.md：入口与四种模式路由。
- references/：设计要点、偏差与对策、运行期预警、三轴与结论规则、证据协议、模式动作、衔接、系列约定。
- templates/：试点方案、启动检查、试点日志、期中检查、成效报告。
- scripts/：`check_plan.py`（方案事前登记检查）、`check_readout.py`（报告是否越过证据阶梯、是否用了事后指标）、`calc_effect.py`（两组/配对效应与 bootstrap 区间）、`manifest.py`（安装完整性）。
- examples/claims-pilot/：承接车险材料核对 Demo 的虚构示例，结论为 Iterate。
- tests/：单元测试与行为用例、结果记录。

## 运行验证
Python 3.9+，仅用标准库。
```sh
python3 -I -m unittest discover -s tests -v
python3 scripts/check_plan.py examples/claims-pilot/plan.md
python3 scripts/check_readout.py examples/claims-pilot/readout.md --plan examples/claims-pilot/plan.md --log examples/claims-pilot/log.md
python3 scripts/calc_effect.py --control 17,18,16,19,17,18 --treatment 11,12,10,13,11,12
```
脚本只检查结构与规则、描述抽样不确定性，不能证明数据真实、样本有代表性或试点有效，也不能代替真人对照设计与现场采集。实际结果与限制见 [tests/RESULTS.md](tests/RESULTS.md)。

## 状态与来源
草案：尚未经任何真实试点检验，行为测试只做过一轮小规模模拟（见 RESULTS）。设计依据是 fde-problem-framing 的指标规范与证据协议、fde-demo 的交接字段，以及作者的 FDE 实践经验；详见 [DEVELOPMENT.md](DEVELOPMENT.md)，推进计划见 [ROADMAP.md](ROADMAP.md)。示例的数字、人物与阈值都是示意，不是客户事实。

## 参考与致谢

本系列各 Skill 在方法设计上不同程度参考了《FDE:AI落地实战指南》，以及作者本人的 FDE 实践经历。各 Skill 的流程、模板、规则与脚本是在此基础上改写和扩展的方法。示例中的人物、数字与场景均为虚构，不是客户事实。

## 许可
MIT，见 [LICENSE](LICENSE)。
