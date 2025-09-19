import pytest
from data_processor import unique_digits


def test_unique_digits_int():
    assert unique_digits(123456) == [1, 2, 3, 4, 5, 6]
    assert unique_digits(333221) == [3, 2, 1]
    assert unique_digits(0) == [0]


def test_unique_digits_float():
    assert unique_digits(12.3456) == [1, 2, 3, 4, 5, 6]
    assert unique_digits(3332.21) == [3, 2, 1]
    assert unique_digits(0.5) == [0, 5]


def test_unique_digits_mixed():
    assert unique_digits("a1b2c3d1e2f3") == [1, 2, 3]
    assert unique_digits("test654test") == [6, 5, 4]
    assert unique_digits("") == []
    assert unique_digits("abcdef") == []


def test_unique_digits_invalid():
    with pytest.raises(TypeError):
        unique_digits(None)
    with pytest.raises(TypeError):
        unique_digits({"key": "value"})
    with pytest.raises(TypeError):
        unique_digits([1, 2, 3])
    with pytest.raises(TypeError):
        unique_digits(True)
