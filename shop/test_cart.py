import pytest

from cart import Cart


def test_empty_cart_total_is_zero():
    assert Cart().total() == 0


def test_subtotal_sums_price_times_qty():
    cart = Cart()
    cart.add("mug", 20.00, qty=2)
    cart.add("notebook", 60.00)
    assert cart.subtotal() == 100.00


def test_total_adds_tax_without_coupon():
    cart = Cart()
    cart.add("notebook", 60.00)
    assert cart.total() == 66.00


def test_coupon_is_applied_before_tax():
    cart = Cart()
    cart.add("mug", 20.00, qty=2)
    cart.add("notebook", 60.00)
    cart.apply_coupon("SAVE20")
    # 100.00 - 20% = 80.00, plus 10% tax = 88.00
    assert cart.total() == 88.00


def test_unknown_coupon_is_rejected():
    with pytest.raises(ValueError):
        Cart().apply_coupon("FREE")
