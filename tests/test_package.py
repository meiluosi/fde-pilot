import re
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_links(self):
        for p in R.rglob('*.md'):
            for dest in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
                if '://' in dest or dest.startswith('#'):
                    continue
                with self.subTest(file=str(p.relative_to(R)), link=dest):
                    self.assertTrue((p.parent / dest.split('#')[0]).exists())

    def test_frontmatter(self):
        text = (R / 'SKILL.md').read_text(encoding='utf-8')
        m = re.match(r'^---\nname: ([a-z-]+)\ndescription: (.+)\n---\n', text)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), 'fde-pilot')
        self.assertLessEqual(len(m.group(2)), 1024)

    def test_portable_paths(self):
        files = list((R / 'references').glob('*.md')) + [R / 'SKILL.md']
        for p in files:
            self.assertNotIn('/Users/', p.read_text(encoding='utf-8'))

    def test_templates_exist(self):
        for name in ('pilot-plan', 'kickoff-check', 'pilot-log', 'midpoint-review', 'pilot-readout'):
            self.assertTrue((R / 'templates' / (name + '.md')).exists())

    def test_series_doc_matches_sibling_conventions(self):
        text = (R / 'references' / 'series.md').read_text(encoding='utf-8')
        for token in ('fde-ramp', 'fde-problem-framing', 'fde-comms', 'fde-demo', 'fde-pilot'):
            self.assertIn(token, text)


if __name__ == '__main__':
    unittest.main()
