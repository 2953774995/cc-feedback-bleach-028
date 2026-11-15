#!/usr/bin/env python3
"""HTML 清洗差异报表验收探针。

契约：
  from bleach.report import clean_report
  res = clean_report([snippet1, snippet2])
  res.items    [{index, before, after, changed}]
  res.tags     {被移除的标签: 出现次数}
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
FAIL = 0


def probe(code, desc, fn):
    global FAIL
    try:
        fn()
        print(f"[PASS] {code} {desc}")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {code} {desc}\n        {type(exc).__name__}: {exc}")
        FAIL += 1


def main():
    try:
        from bleach.report import clean_report  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] P0 导入 bleach.report 失败：{type(exc).__name__}: {exc}")
        print("-" * 60)
        print("探针汇总：0/4 通过")
        return 1

    DIRTY = "<script>x</script><p>正文</p>"
    CLEAN = "<p>正文</p>"

    def p1():
        res = clean_report([CLEAN])
        assert res.items[0]["changed"] is False, res.items

    def p2():
        res = clean_report([DIRTY])
        assert "<script>" not in res.items[0]["after"], res.items

    def p3():
        res = clean_report([DIRTY])
        assert res.tags.get("script", 0) >= 1, res.tags

    def p4():
        import bleach
        assert bleach.clean("<b>x</b>", tags=[]) == "&lt;b&gt;x&lt;/b&gt;"

    probe("P1", "干净片段标记未变", p1)
    probe("P2", "危险标签被清掉", p2)
    probe("P3", "移除标签统计", p3)
    probe("P4", "既有 clean 不变", p4)

    print("-" * 60)
    print(f"探针汇总：{4 - FAIL}/4 通过")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
