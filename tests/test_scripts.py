import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'scripts'))

import calc_effect  # noqa: E402
import check_plan  # noqa: E402
import check_readout  # noqa: E402
import manifest  # noqa: E402

EX = R / 'examples' / 'claims-pilot'
PLAN = (EX / 'plan.md').read_text(encoding='utf-8')
READOUT = (EX / 'readout.md').read_text(encoding='utf-8')
LOG = check_readout.parse_log((EX / 'log.md').read_text(encoding='utf-8'))


class PlanTests(unittest.TestCase):
    def test_example_passes(self):
        errors, _ = check_plan.check(PLAN)
        self.assertEqual(errors, [])

    def test_template_fails(self):
        errors, _ = check_plan.check((R / 'templates' / 'pilot-plan.md').read_text(encoding='utf-8'))
        self.assertGreater(len(errors), 10)

    def test_metrics_parsed(self):
        metrics, problems = check_plan.parse_metrics(PLAN)
        self.assertEqual(sorted(metrics), ['M1', 'M2', 'M3', 'M4'])
        self.assertEqual(problems, [])
        self.assertEqual(metrics['M4']['层'], '护栏')

    def test_missing_guardrail_layer(self):
        errors, _ = check_plan.check(PLAN.replace('| M4 | 护栏 |', '| M4 | 技术 |'))
        self.assertTrue(any('护栏' in e and '层' in e for e in errors))

    def test_unknown_metric_in_criteria(self):
        errors, _ = check_plan.check(PLAN.replace('M4 > 0', 'M7 > 0'))
        self.assertTrue(any('M7' in e for e in errors))

    def test_success_criteria_must_include_business_metric(self):
        text = PLAN.replace('- 成功判据：第 2–4 周 M2 试点组中位数比对照组低 25% 以上，且 M3', '- 成功判据：M3')
        text = text.replace('且 M1 每周', '且 M1 每周')
        errors, _ = check_plan.check(text)
        self.assertTrue(any('业务层' in e for e in errors))

    def test_stop_condition_format(self):
        errors, _ = check_plan.check(PLAN.replace('- S3：系统不可用累计超过 8 小时｜回退人工并记录事件｜IT 数据岗', '- S3：只有条件'))
        self.assertTrue(any('S3' in e for e in errors))

    def test_no_control_and_selection_warnings(self):
        text = PLAN.replace('- 对照设计：同期对照。', '- 对照设计：无对照。')
        text = text.replace('非自愿报名', '自愿报名')
        errors, warnings = check_plan.check(text)
        self.assertEqual(errors, [])
        self.assertTrue(any('无对照' in w for w in warnings))
        self.assertTrue(any('选择偏差' in w for w in warnings))

    def test_negated_volunteer_wording_is_not_flagged(self):
        _, warnings = check_plan.check(PLAN)
        self.assertFalse(any('选择偏差' in w for w in warnings))

    def test_baseline_pending_warns(self):
        text = PLAN.replace('试验前两周基线 17 分钟（日志；示例）', '待测')
        errors, warnings = check_plan.check(text)
        self.assertTrue(any('M2' in w and '待测' in w for w in warnings))

    def test_requires_learning_period_and_demo_source(self):
        errors, _ = check_plan.check(PLAN.replace('- 学习期（不计入判定）：第 1 周；学习期数据保留并单列', '- 学习期（不计入判定）：待填'))
        self.assertTrue(any('学习期' in e for e in errors))
        errors, _ = check_plan.check(PLAN.replace('- 承接的 Demo 复盘：', '- 备注：'))
        self.assertTrue(any('Demo 复盘' in e for e in errors))


class ReadoutTests(unittest.TestCase):
    def run_check(self, readout=READOUT, plan=PLAN, log=LOG):
        return check_readout.check(readout, plan, log)

    def test_log_parsed(self):
        self.assertEqual(len(LOG), 10)
        self.assertEqual(LOG['P10']['type'], '解读')

    def test_example_passes(self):
        errors, warnings = self.run_check()
        self.assertEqual(errors, [])

    def test_template_fails(self):
        text = (R / 'templates' / 'pilot-readout.md').read_text(encoding='utf-8')
        self.assertGreater(len(self.run_check(readout=text)[0]), 3)

    def test_inference_cannot_be_cited(self):
        text = READOUT.replace('证据：P6,P7', '证据：P6,P10')
        self.assertTrue(any('解读' in e for e in self.run_check(text)[0]))

    def test_posthoc_metric_cannot_be_evidence(self):
        text = READOUT.replace('证据：P4,P5', '证据：P4,P9')
        errors, _ = self.run_check(text)
        self.assertTrue(any('M9' in e and '事后指标' in e for e in errors))

    def test_posthoc_metric_must_be_listed_as_exploratory(self):
        text = READOUT.replace('- P9（M9 夜间使用 11 次）：方案未登记该指标，仅提示可能存在加班时使用；是否值得下一轮登记待讨论。', '待填')
        _, warnings = self.run_check(text)
        self.assertTrue(any('探索性发现' in w for w in warnings))

    def test_business_verified_needs_control(self):
        text = READOUT.replace('- 因果归因：有对照', '- 因果归因：无对照仅相关')
        self.assertTrue(any('因果归因' in e for e in self.run_check(text)[0]))

    def test_attribution_must_match_plan_design(self):
        plan = PLAN.replace('- 对照设计：同期对照。', '- 对照设计：无对照。')
        self.assertTrue(any('不能写“有对照”' in e for e in self.run_check(plan=plan)[0]))

    def test_verified_requires_sample_size(self):
        log = dict(LOG)
        log['P2'] = dict(log['P2'], n='')
        self.assertTrue(any('使用与采用判为已验证' in e for e in self.run_check(log=log)[0]))

    def test_proceed_requires_all_axes_verified(self):
        text = READOUT.replace('建议结论：Iterate', '建议结论：Proceed')
        self.assertTrue(any('三轴均为已验证' in e for e in self.run_check(text)[0]))

    def test_proceed_can_pass(self):
        text = (READOUT.replace('建议结论：Iterate', '建议结论：Proceed')
                .replace('护栏与可持续：部分｜证据：P6,P7', '护栏与可持续：已验证｜证据：P6,P7')
                .replace('- 扩大范围建议：', '- 扩大范围建议：扩大到理赔二组，仍限印刷体车损'))
        self.assertEqual(self.run_check(text)[0], [])

    def test_triggered_stop_blocks_proceed(self):
        text = (READOUT.replace('建议结论：Iterate', '建议结论：Proceed')
                .replace('护栏与可持续：部分｜证据：P6,P7', '护栏与可持续：已验证｜证据：P6,P7')
                .replace('- 扩大范围建议：', '- 扩大范围建议：x')
                .replace('- 触发的停止条件：无', '- 触发的停止条件：S1'))
        errors, _ = self.run_check(text)
        self.assertTrue(any('不能 Proceed' in e for e in errors))
        self.assertTrue(any('护栏与可持续判为已验证' in e for e in errors))

    def test_iterate_needs_followups(self):
        text = READOUT.replace('- 补验证：护栏轴补两项', '- 备注：护栏轴补两项')
        self.assertTrue(any('补验证' in e for e in self.run_check(text)[0]))

    def test_unknown_id(self):
        text = READOUT.replace('证据：P2,P3', '证据：P2,P99')
        self.assertTrue(any('P99' in e for e in self.run_check(text)[0]))

    def test_requires_comparison_section(self):
        text = READOUT.replace('## 对照事前登记', '## 其他').replace('- 成功判据', '- x')
        self.assertTrue(any('对照事前登记' in e for e in self.run_check(text)[0]))


class EffectTests(unittest.TestCase):
    def test_unpaired_separated_groups(self):
        control = [17, 18, 16, 19, 17, 18, 20, 16, 17, 18]
        treat = [11, 12, 10, 13, 11, 12, 14, 10, 11, 12]
        out = calc_effect.summarize(control, treat, reps=2000)
        self.assertLess(out['effect_median_treatment_minus_control'], -4)
        self.assertTrue(out['interval_excludes_zero'])
        self.assertTrue(any('n<20' in n for n in out['notes']))

    def test_overlapping_groups_include_zero(self):
        a = [10, 12, 11, 13, 10, 12, 11, 13]
        b = [11, 12, 10, 13, 12, 11, 10, 13]
        out = calc_effect.summarize(a, b, reps=2000)
        self.assertFalse(out['interval_excludes_zero'])

    def test_paired(self):
        c = [10, 12, 14, 16, 18]
        t = [8, 9, 11, 13, 14]
        out = calc_effect.summarize(c, t, paired=True, reps=2000)
        self.assertEqual(out['effect_median_treatment_minus_control'], -3)
        with self.assertRaises(ValueError):
            calc_effect.summarize([1, 2], [1], paired=True)

    def test_deterministic_with_seed(self):
        a, b = [1, 2, 3, 4, 5], [2, 3, 4, 5, 6]
        self.assertEqual(calc_effect.summarize(a, b, seed=7, reps=500), calc_effect.summarize(a, b, seed=7, reps=500))


class ManifestTests(unittest.TestCase):
    def test_detects_missing_and_changed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'a').mkdir()
            (root / 'a' / 'x.md').write_text('x')
            (root / 'y.md').write_text('y')
            expected = manifest.collect(root)
            (root / 'a' / 'x.md').unlink()
            (root / 'y.md').write_text('changed')
            self.assertEqual(manifest.compare(expected, manifest.collect(root)), (['a/x.md'], ['y.md'], []))


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-I', *map(str, args)], capture_output=True, text=True)

    def test_example_exit_codes(self):
        r = self.run_cli(R / 'scripts' / 'check_plan.py', EX / 'plan.md')
        self.assertEqual(r.returncode, 0, r.stdout)
        r = self.run_cli(R / 'scripts' / 'check_readout.py', EX / 'readout.md', '--plan', EX / 'plan.md',
                         '--log', EX / 'log.md')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_template_exit_code(self):
        r = self.run_cli(R / 'scripts' / 'check_plan.py', R / 'templates' / 'pilot-plan.md')
        self.assertEqual(r.returncode, 1)

    def test_calc_effect_cli(self):
        r = self.run_cli(R / 'scripts' / 'calc_effect.py', '--control', '17,18,16,19,17', '--treatment', '11,12,10,13,11',
                         '--reps', '500')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('bootstrap_interval', r.stdout)


if __name__ == '__main__':
    unittest.main()
