from inventory import Inventory
from pricing import calculate_subtotal, apply_tax
from discounts import get_discount_rate, apply_discount


class Order:
    def __init__(self, inventory: Inventory):
        self.inventory = inventory
        self.items = {}

    def add_item(self, item, quantity):
        if not self.inventory.has_enough(item, quantity):
            raise ValueError(f"Not enough {item} in stock")
        self.items[item] = self.items.get(item, 0) + quantity

    def calculate_total(self):
        subtotal = 0
        for item, quantity in self.items.items():
            subtotal += calculate_subtotal(item, quantity)

        discount_rate = get_discount_rate(subtotal)
        discounted = apply_discount(subtotal, discount_rate)
        final_total = apply_tax(discounted)
        return round(final_total, 2)

    def checkout(self):
        for item, quantity in self.items.items():
            self.inventory.remove_stock(item, quantity)
        total = self.calculate_total()
        self.items.clear()
        return total
