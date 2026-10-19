"""两组或配对数据的效应与 bootstrap 区间（中位数）。

只描述抽样不确定性。不处理混杂、选择偏差和聚类（同一人的多件案件不独立）；
聚类数据请先按人汇总再输入。不验证数据真实性。
"""
import argparse
import json
import random
import statistics
import sys


def parse_nums(s):
    out = [float(x) for x in s.replace('，', ',').split(',') if x.strip()]
    if not out:
        raise ValueError('数据为空')
    return out


def bootstrap(control, treatment, paired=False, reps=5000, seed=0, conf=0.95):
    rng = random.Random(seed)
    if paired:
        if len(control) != len(treatment):
            raise ValueError('配对数据长度须相同')
        d = [t - c for c, t in zip(control, treatment)]
        stat = [statistics.median([rng.choice(d) for _ in d]) for _ in range(reps)]
        point = statistics.median(d)
    else:
        stat = []
        for _ in range(reps):
            sc = [rng.choice(control) for _ in control]
            st = [rng.choice(treatment) for _ in treatment]
            stat.append(statistics.median(st) - statistics.median(sc))
        point = statistics.median(treatment) - statistics.median(control)
    stat.sort()
    lo = stat[int((1 - conf) / 2 * reps)]
    hi = stat[min(reps - 1, int((1 + conf) / 2 * reps))]
    return point, lo, hi


def summarize(control, treatment, paired=False, reps=5000, seed=0, conf=0.95):
    point, lo, hi = bootstrap(control, treatment, paired, reps, seed, conf)
    mc, mt = statistics.median(control), statistics.median(treatment)
    out = {
        'n_control': len(control), 'n_treatment': len(treatment), 'paired': paired,
        'median_control': mc, 'median_treatment': mt,
        'mean_control': statistics.mean(control), 'mean_treatment': statistics.mean(treatment),
        'effect_median_treatment_minus_control': point,
        'bootstrap_interval': [lo, hi], 'confidence': conf, 'reps': reps, 'seed': seed,
        'interval_excludes_zero': lo > 0 or hi < 0,
        'notes': ['效应 = 试点组 − 对照组；负值表示试点组更小（如耗时更短）',
                  '只反映抽样不确定性；不处理混杂、选择偏差、聚类',
                  '不验证数据真实性与口径一致'],
    }
    if mc:
        out['relative_effect_vs_control_median'] = point / mc
    if min(len(control), len(treatment)) < 20:
        out['notes'].append('任一组 n<20：小样本，区间可能不稳，只说明机制')
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--control', required=True, help='对照组数据，逗号分隔')
    p.add_argument('--treatment', required=True, help='试点组数据，逗号分隔')
    p.add_argument('--paired', action='store_true', help='按位置配对（长度须相同）')
    p.add_argument('--reps', type=int, default=5000)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--conf', type=float, default=0.95)
    a = p.parse_args()
    try:
        out = summarize(parse_nums(a.control), parse_nums(a.treatment), a.paired, a.reps, a.seed, a.conf)
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == '__main__':
    main()
