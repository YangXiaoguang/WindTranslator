from typing import List


def parse_chapter_range(spec: str, total: int) -> List[int]:
    """
    Parse a chapter range spec into a sorted list of 0-based indices.

    Accepted formats (1-based, inclusive):
      "1-10"     → chapters 1 to 10
      "5"        → chapter 5 only
      "1,3,5-8"  → chapters 1, 3, 5, 6, 7, 8
    """

    def _to_int(s: str) -> int:
        try:
            return int(s)
        except ValueError:
            raise ValueError(f"章节范围格式错误：'{s}' 不是有效数字")

    indices: set = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            raw_lo, raw_hi = part.split("-", 1)
            lo, hi = _to_int(raw_lo.strip()), _to_int(raw_hi.strip())
            if lo < 1 or hi > total or lo > hi:
                raise ValueError(
                    f"范围 {lo}-{hi} 超出有效章节数（1-{total}），"
                    f"请先用 --list 查看章节列表"
                )
            indices.update(range(lo - 1, hi))
        else:
            n = _to_int(part)
            if n < 1 or n > total:
                raise ValueError(
                    f"章节 {n} 超出有效范围（1-{total}），"
                    f"请先用 --list 查看章节列表"
                )
            indices.add(n - 1)

    if not indices:
        raise ValueError(f"章节范围 '{spec}' 未匹配任何章节")
    return sorted(indices)
