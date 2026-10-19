"""成效报告规则检查：核对三轴状态是否越过证据阶梯、是否使用了事后指标。不验证日志本身是否真实。"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_plan import find_section, parse_metrics, parse_stops, split_sections, missing, value_of  # noqa: E402

LOG_TYPES = ('日志指标', '对照观测', '抽检复核', '访谈', '事件', '解读')
AXES = {
    '使用与采用': {'layers': ('使用',), 'types': ('日志指标', '对照观测')},
    '业务效果': {'layers': ('业务', '技术'), 'types': ('对照观测', '抽检复核', '日志指标')},
    '护栏与可持续': {'layers': ('护栏',), 'types': ('日志指标', '抽检复核', '事件')},
}
PARTIAL_TYPES = ('日志指标', '对照观测', '抽检复核', '事件', '访谈')
REFUTE_TYPES = ('日志指标', '对照观测', '抽检复核', '事件')
NEXT_KEYS = {'Proceed': ('扩大范围建议',), 'Iterate': ('补验证', '下次改什么'),
             'Pivot': ('转向',), 'Stop-Defer': ('重开条件',)}


def parse_log(text):
    log = {}
    for line in text.splitlines():
        if not line.strip().startswith('|'):
            continue
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) >= 6 and re.fullmatch(r'P\d+', c[0]):
            log[c[0]] = {'type': c[1], 'metric': c[2], 'window': c[3], 'n': c[4], 'value': c[5],
                         'note': c[7] if len(c) > 7 else ''}
    return log


def section_filled(text, keyword):
    cur, body = None, {}
    for line in text.splitlines():
        m = re.match(r'^##\s+(.*)', line)
        if m:
            cur = m.group(1).strip()
            body[cur] = []
        elif cur:
            s = line.strip()
            if s and not s.startswith('>') and s != '待填':
                body[cur].append(s)
    return any(keyword in h and body[h] for h in body)


def field(text, key):
    for line in text.splitlines():
        m = re.match(r'^\s*[-*]\s*' + key + r'[：:]\s*(.*)$', line)
        if m:
            v = m.group(1).strip()
            return None if v in ('', '待填') else v
    return None


def check(readout, plan, log):
    errors, warnings = [], []
    metrics, _ = parse_metrics(plan)
    stops, _ = parse_stops(plan)
    for i, r in log.items():
        if r['type'] not in LOG_TYPES:
            errors.append('记录 %s 的类型“%s”不在：%s' % (i, r['type'], ' / '.join(LOG_TYPES)))

    m = re.search(r'建议结论[：:]\s*(Proceed|Iterate|Pivot|Stop-Defer)\b', readout)
    verdict = m.group(1) if m else None
    if not verdict:
        errors.append('未找到有效的建议结论（Proceed / Iterate / Pivot / Stop-Defer）')

    attribution = field(readout, '因果归因')
    if attribution not in ('有对照', '无对照仅相关'):
        errors.append('因果归因须为：有对照 / 无对照仅相关')
    design = value_of(find_section(split_sections(plan), '对照') or [], '对照设计') or ''
    if attribution == '有对照' and design.startswith(('无对照', '前后对比')):
        errors.append('方案对照设计为“%s”，报告不能写“有对照”' % design.split('，')[0][:6])

    triggered = field(readout, '触发的停止条件')
    trig_ids = re.findall(r'S\d+', triggered or '')
    if triggered is None:
        errors.append('未写“触发的停止条件”（无，或 S1 等编号）')
    for s in trig_ids:
        if s not in stops:
            errors.append('触发的停止条件 %s 不在方案中' % s)
    no_trigger = triggered is not None and not trig_ids

    posthoc_used = set()
    status = {}
    for axis, rule in AXES.items():
        m = re.search(r'^\s*[-*]\s*' + axis + r'[：:]\s*(已验证|部分|未验证|被推翻)\s*[｜|]\s*证据[：:]\s*([^｜|\n]*)',
                      readout, re.M)
        if not m:
            errors.append('未找到“%s”的判定（格式：- 轴：状态｜证据：P1,P2｜范围：…）' % axis)
            continue
        st, ids = m.group(1), re.findall(r'P\d+', m.group(2))
        status[axis] = st
        unknown = [i for i in ids if i not in log]
        if unknown:
            errors.append('%s引用了日志中不存在的 ID：%s' % (axis, ', '.join(unknown)))
        recs = {i: log[i] for i in ids if i in log}
        inf = [i for i, r in recs.items() if r['type'] == '解读']
        if inf:
            errors.append('%s把解读当证据引用：%s' % (axis, ', '.join(inf)))
        for i, r in recs.items():
            if r['type'] in ('访谈', '事件', '解读'):
                continue
            if r['metric'] not in metrics:
                posthoc_used.add(i)
                errors.append('%s引用的 %s 使用了方案之外的指标“%s”，事后指标不能作证据' % (axis, i, r['metric']))

        def qualifies(r):
            if r['type'] not in rule['types']:
                return False
            if r['type'] == '事件':
                return True
            if metrics.get(r['metric'], {}).get('层') not in rule['layers']:
                return False
            return r['n'] not in ('', '-', '待填')

        if st == '已验证':
            good = [i for i, r in recs.items() if qualifies(r)]
            if len(set(good)) < 2:
                errors.append('%s判为已验证，但只有 %d 条可计入记录（需≥2，且指标层、类型、样本数合格）'
                              % (axis, len(set(good))))
            if axis == '业务效果':
                if not any(recs[i]['type'] in ('对照观测', '抽检复核') for i in good):
                    errors.append('业务效果判为已验证，需至少 1 条对照观测或抽检复核')
                if attribution != '有对照':
                    errors.append('业务效果判为已验证，但因果归因不是“有对照”')
            if axis == '护栏与可持续' and not no_trigger:
                errors.append('护栏与可持续判为已验证，但存在触发的停止条件或未填写')
        elif st == '部分':
            if not any(r['type'] in PARTIAL_TYPES for r in recs.values()):
                errors.append('%s判为部分，但没有日志指标/对照观测/抽检复核/事件/访谈类记录' % axis)
        elif st == '被推翻':
            if not any(r['type'] in REFUTE_TYPES for r in recs.values()):
                errors.append('%s判为被推翻，但没有日志指标/对照观测/抽检复核/事件类反证' % axis)

    if verdict == 'Proceed':
        if len(status) == 3 and any(v != '已验证' for v in status.values()):
            errors.append('Proceed 要求三轴均为已验证')
        if trig_ids:
            errors.append('存在触发的停止条件，不能 Proceed')
    if verdict == 'Iterate' and len(status) == 3 and all(v == '已验证' for v in status.values()) and no_trigger:
        warnings.append('三轴均已验证且无触发的停止条件，考虑是否应为 Proceed')
    if verdict:
        for key in NEXT_KEYS[verdict]:
            if field(readout, key) is None:
                errors.append('结论 %s 须填写“%s”' % (verdict, key))

    if not section_filled(readout, '对照事前登记'):
        errors.append('“对照事前登记”一节为空')
    outside = {i for i, r in log.items() if r['type'] in ('日志指标', '对照观测', '抽检复核')
               and r['metric'] not in metrics}
    if outside and not section_filled(readout, '探索性发现'):
        warnings.append('日志中有方案之外的指标记录（%s），请在“探索性发现”中单列' % ', '.join(sorted(outside)))
    open_events = [i for i, r in log.items() if r['type'] == '事件' and not re.search('已关闭|已处理', r['note'])]
    if open_events:
        warnings.append('存在未标注已关闭/已处理的事件：' + ', '.join(open_events))
    if not log:
        warnings.append('日志中没有解析出 P 编号记录；各轴最高只能判“部分”且须标仅用户转述')
    return errors, warnings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('readout', type=Path)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    try:
        readout = a.readout.read_text(encoding='utf-8')
        plan = a.plan.read_text(encoding='utf-8')
        log = parse_log(a.log.read_text(encoding='utf-8'))
    except OSError as e:
        p.error(str(e))
    errors, warnings = check(readout, plan, log)
    if a.json:
        print(json.dumps({'errors': errors, 'warnings': warnings, 'ok': not errors}, ensure_ascii=False, indent=2))
    else:
        for e in errors:
            print('错误：' + e)
        for w in warnings:
            print('警告：' + w)
        print('通过规则检查（不代表数据真实、不代表试点有效）' if not errors else '未通过：%d 个错误' % len(errors))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
