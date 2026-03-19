import pytest
from epub_translator.utils.chapter_range import parse_chapter_range


def test_single_chapter():
    assert parse_chapter_range("3", 10) == [2]


def test_range():
    assert parse_chapter_range("2-5", 10) == [1, 2, 3, 4]


def test_comma_list():
    assert parse_chapter_range("1,3,5", 10) == [0, 2, 4]


def test_mixed():
    assert parse_chapter_range("1,3,5-7", 10) == [0, 2, 4, 5, 6]


def test_full_range():
    assert parse_chapter_range("1-5", 5) == [0, 1, 2, 3, 4]


def test_out_of_bounds_raises():
    with pytest.raises(ValueError, match="超出有效范围"):
        parse_chapter_range("11", 10)


def test_range_lo_gt_hi_raises():
    with pytest.raises(ValueError, match="超出有效章节数"):
        parse_chapter_range("5-3", 10)


def test_invalid_number_raises():
    with pytest.raises(ValueError, match="不是有效数字"):
        parse_chapter_range("abc", 10)


def test_empty_spec_raises():
    with pytest.raises(ValueError, match="未匹配任何章节"):
        parse_chapter_range(",,,", 10)
