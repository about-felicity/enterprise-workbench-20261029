"""Deterministic hypothetical arithmetic; no actual product price claims."""

from decimal import Decimal

MARKER = "[[UNIT_PRICE_EXAMPLE]]"


def example():
    price_a, volume_a = Decimal(79), Decimal(500)
    price_b, volume_b = Decimal(45), Decimal(200)
    unit_a, unit_b = price_a / volume_a, price_b / volume_b
    comparison = "低于" if unit_a < unit_b else "高于" if unit_a > unit_b else "等于"
    return (
        f"只看一个假设的算账例子：A的到手总价为{price_a}元、容量为{volume_a}毫升，"
        f"B的到手总价为{price_b}元、容量为{volume_b}毫升。"
        f"每毫升价格等于到手总价除以总毫升数，A为{unit_a}元/毫升，B为{unit_b}元/毫升，"
        f"所以A的单位容量价格{comparison}B。以上数字只是计算示例，不是任何实际产品的售价，也不表示产品效果。"
    )


def bind(value):
    if isinstance(value, str):
        return value.replace(MARKER + "。", example()).replace(MARKER, example())
    if isinstance(value, list):
        return [bind(item) for item in value]
    if isinstance(value, dict):
        return {key: bind(item) for key, item in value.items()}
    return value
