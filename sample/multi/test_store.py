import pytest
from inventory import Inventory
from pricing import calculate_subtotal, apply_tax
from discounts import get_discount_rate, apply_discount
from order import Order


# ── Inventory ──
def test_add_and_get_stock():
    inv = Inventory()
    inv.add_stock("apple", 10)
    assert inv.get_quantity("apple") == 10

def test_has_enough_exact_match():
    inv = Inventory()
    inv.add_stock("apple", 5)
    assert inv.has_enough("apple", 5) is True

def test_has_enough_insufficient():
    inv = Inventory()
    inv.add_stock("apple", 3)
    assert inv.has_enough("apple", 5) is False


# ── Pricing ──
def test_calculate_subtotal():
    assert calculate_subtotal("apple", 4) == pytest.approx(2.00)

def test_apply_tax_adds_not_subtracts():
    assert apply_tax(100, tax_rate=0.08) == pytest.approx(108.0)


# ── Discounts ──
def test_discount_rate_boundary_20():
    assert get_discount_rate(20) == 0.05

def test_discount_rate_boundary_50():
    assert get_discount_rate(50) == 0.10

def test_apply_discount_reduces_total():
    assert apply_discount(100, 0.10) == pytest.approx(90.0)


# ── Order (integration across all modules) ──
def test_order_full_flow():
    inv = Inventory()
    inv.add_stock("bread", 10)

    order = Order(inv)
    order.add_item("bread", 4)  # 4 * 2.25 = 9.00 subtotal, no discount (< 20), + 8% tax
    total = order.checkout()

    assert total == pytest.approx(9.72)
    assert inv.get_quantity("bread") == 6

def test_order_rejects_insufficient_stock():
    inv = Inventory()
    inv.add_stock("milk", 2)
    order = Order(inv)
    with pytest.raises(ValueError):
        order.add_item("milk", 5)
