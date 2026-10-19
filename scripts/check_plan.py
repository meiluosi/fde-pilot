"""试点方案完整性检查：只查结构与事前登记规则，不验证指标是否合理、数据是否存在。"""
import argparse
import json
import re
import sys
from pathlib import Path

SECTIONS = [
    ('范围', '试点范围'), ('来源', '来源与交接'), ('假设', '假设'), ('指标', '指标字典'),
    ('对照', '对照与归因'), ('样本', '样本与参与者'), ('护栏', '护栏与停止条件'), ('节奏', '检查节奏'),
    ('判据', '成败判据'), ('数据', '数据与授权'), ('责任', '责任与配合'), ('变更', '变更记录'),
]
LAYERS = ('技术', '使用', '业务', '护栏')
DESIGNS = ('同期对照', '配对前后', '前后对比', '无对照')
METRIC_COLS = ['ID', '层', '定义', '分子/分母', '单位', '基线', '目标', '采集', '责任']
SELECTION_RISK = ('自愿', '自选', '志愿', '主动报名')


def split_sections(text):
    secs, cur = {}, None
    for line in text.splitlines():
        m = re.match(r'^##\s+(.*)', line)
        if m:
            cur = m.group(1).strip()
            secs[cur] = []
        elif cur is not None:
            secs[cur].append(line)
    return secs


def unfilled(s):
    s = s.strip().lstrip('-* ').strip()
    if s == '待填':
        return True
    m = re.match(r'^[^：:]*[：:]\s*(.*)$', s)
    return bool(m) and m.group(1).strip() in ('', '待填')


def filled(lines):
    return [l.strip() for l in lines
            if l.strip() and not l.strip().startswith(('>', '<!--', '|')) and not unfilled(l)]


def value_of(lines, key):
    for line in lines:
        m = re.match(r'^\s*[-*]\s*' + key + r'[^：:]*[：:]\s*(.*)$', line)
        if m:
            return m.group(1).strip()
    return None


def missing(v):
    return v in (None, '', '待填')


def find_section(secs, key):
    head = next((h for h in secs if key in h), None)
    return secs[head] if head is not None else None


def parse_metrics(text):
    """返回 (metrics, problems)。metrics: {M1: {'层': .., '基线': ..}}"""
    secs = split_sections(text)
    lines = find_section(secs, '指标') or []
    rows = [[c.strip() for c in l.strip().strip('|').split('|')] for l in lines if l.strip().startswith('|')]
    metrics, problems = {}, []
    if not rows:
        return metrics, problems
    header = rows[0]
    idx = {}
    for col in METRIC_COLS:
        pos = next((i for i, h in enumerate(header) if col in h), None)
        if pos is None:
            problems.append('指标字典缺少列：' + col)
        idx[col] = pos
    for r in rows[1:]:
        if not r or not re.fullmatch(r'M\d+', r[0]):
            continue
        rec = {}
        for col, pos in idx.items():
            v = r[pos] if pos is not None and pos < len(r) else ''
            rec[col] = '' if v in ('', '待填') else v
        for col in METRIC_COLS:
            if idx[col] is not None and not rec[col]:
                problems.append('%s 的“%s”未填写' % (r[0], col))
        metrics[r[0]] = rec
    return metrics, problems


def parse_stops(text):
    stops, bad = {}, []
    lines = find_section(split_sections(text), '护栏') or []
    for line in lines:
        m = re.match(r'^\s*[-*]\s*(S\d+)[：:]\s*(.*)$', line)
        if not m:
            continue
        v = m.group(2).strip()
        if v in ('', '待填'):
            continue
        parts = [p.strip() for p in re.split(r'[｜|]', v)]
        if len(parts) >= 3 and all(parts[:3]):
            stops[m.group(1)] = parts[:3]
        else:
            bad.append(m.group(1))
    return stops, bad


def check(text):
    errors, warnings = [], []
    secs = split_sections(text)
    found = {}
    for key, label in SECTIONS:
        sec = find_section(secs, key)
        if sec is None:
            errors.append('缺少章节：' + label)
            continue
        found[key] = sec
        if key != '指标' and not filled(sec):
            errors.append('未填写：' + label)

    def need(key, field, label=None, level=errors):
        if key in found and missing(value_of(found[key], field)):
            level.append('未填写：%s' % (label or field))

    need('范围', '起止')
    need('范围', '期中检查')
    need('来源', '承接的 Demo 复盘')
    need('来源', '已获授权与对接人', level=warnings)
    need('样本', '参与者选择方式')
    need('样本', '学习期')
    need('样本', '最小有效窗口与样本')
    need('对照', '归因限制')
    need('数据', '数据用途约定', level=warnings)

    if '假设' in found and not re.search(r'^\s*[-*]\s*H\d+[：:]\s*(?!待填)\S', '\n'.join(found['假设']), re.M):
        errors.append('至少需要一条假设（H1：…）')

    if '样本' in found:
        sel = value_of(found['样本'], '参与者选择方式') or ''
        for neg in ('非自愿', '不是自愿', '非自选', '不靠自愿'):  # 否定写法不算风险
            sel = sel.replace(neg, '')
        if any(w in sel for w in SELECTION_RISK):
            warnings.append('参与者为自愿/自选：存在选择偏差，报告时须分别报告并写明代表性限制')

    if '对照' in found:
        design = value_of(found['对照'], '对照设计') or ''
        if missing(design) or not design.startswith(DESIGNS):
            errors.append('对照设计须以此开头：' + ' / '.join(DESIGNS))
        elif design.startswith(('无对照', '前后对比')):
            warnings.append('无对照/前后对比：业务效果最高只能判“部分”，报告须写无对照仅相关')

    metrics, problems = parse_metrics(text)
    errors.extend(problems)
    if '指标' in found:
        if len(metrics) < 3:
            errors.append('指标字典至少需要 3 项（现有 %d）' % len(metrics))
        for mid, rec in metrics.items():
            if rec['层'] and rec['层'] not in LAYERS:
                errors.append('%s 的层须为：%s' % (mid, ' / '.join(LAYERS)))
            if '待测' in rec['基线']:
                warnings.append('%s 基线为待测：须在检查节奏中安排基线测量，且在启动前完成' % mid)
        layers = {r['层'] for r in metrics.values()}
        for need_layer in ('使用', '业务', '护栏'):
            if need_layer not in layers:
                errors.append('指标字典缺少“%s”层指标' % need_layer)

    stops, bad = parse_stops(text)
    if '护栏' in found:
        if not stops:
            errors.append('至少需要一条格式正确的停止条件（S1：条件｜动作｜责任岗位）')
        for b in bad:
            errors.append('%s 格式应为“条件｜动作｜责任岗位”' % b)

    if '判据' in found:
        for kind in ('成功判据', '失败判据', '延长判据'):
            v = value_of(found['判据'], kind)
            if missing(v):
                errors.append('未填写：' + kind)
                continue
            ids = re.findall(r'M\d+', v)
            if not ids and kind != '延长判据':  # 延长判据针对样本与窗口，不必引用指标
                errors.append('%s 未引用指标 ID' % kind)
            for i in ids:
                if i not in metrics:
                    errors.append('%s 引用了方案中不存在的指标 %s' % (kind, i))
        succ = re.findall(r'M\d+', value_of(found['判据'], '成功判据') or '')
        if succ and metrics and not any(metrics.get(i, {}).get('层') == '业务' for i in succ):
            errors.append('成功判据须包含业务层指标')
    return errors, warnings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan', type=Path)
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    try:
        text = a.plan.read_text(encoding='utf-8')
    except OSError as e:
        p.error(str(e))
    errors, warnings = check(text)
    if a.json:
        print(json.dumps({'errors': errors, 'warnings': warnings, 'ok': not errors}, ensure_ascii=False, indent=2))
    else:
        for e in errors:
            print('错误：' + e)
        for w in warnings:
            print('警告：' + w)
        print('通过结构检查（不代表方案合理）' if not errors else '未通过：%d 个错误' % len(errors))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
