"""生成或校验 MANIFEST.json（文件路径 -> sha256）。用于发现安装时缺失子目录、文件被改动。

不能证明内容正确，也不防恶意篡改（清单本身在同一目录）。
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

SKIP_DIRS = {'.git', '__pycache__', '.venv', 'node_modules'}
SKIP_FILES = {'.DS_Store', 'MANIFEST.json'}


def collect(root):
    out = {}
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if p.is_dir() or SKIP_DIRS & set(rel.parts) or p.name in SKIP_FILES or p.suffix == '.pyc':
            continue
        out[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def compare(expected, actual):
    missing = sorted(set(expected) - set(actual))
    changed = sorted(k for k in expected if k in actual and expected[k] != actual[k])
    extra = sorted(set(actual) - set(expected))
    return missing, changed, extra


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', action='store_true', help='生成 MANIFEST.json')
    g.add_argument('--check', action='store_true', help='按 MANIFEST.json 校验')
    a = p.parse_args()
    root = a.root.resolve()
    actual = collect(root)
    path = root / 'MANIFEST.json'
    if a.write:
        path.write_text(json.dumps(actual, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        print('已写入 %s（%d 个文件）' % (path, len(actual)))
        return
    if not path.exists():
        print('错误：没有 MANIFEST.json')
        sys.exit(1)
    expected = json.loads(path.read_text(encoding='utf-8'))
    missing, changed, extra = compare(expected, actual)
    for m in missing:
        print('缺失：' + m)
    for c in changed:
        print('已改动：' + c)
    for e in extra:
        print('多出（清单未记录）：' + e)
    if missing or changed:
        print('校验未通过：缺失 %d，改动 %d。安装时请复制完整目录。' % (len(missing), len(changed)))
        sys.exit(1)
    print('校验通过（多出 %d 个文件，未计入）' % len(extra))


if __name__ == '__main__':
    main()
