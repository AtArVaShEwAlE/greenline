class Inventory:
    def __init__(self):
        self.stock = {}

    def add_stock(self, item, quantity):
        if item in self.stock:
            self.stock[item] += quantity
        else:
            self.stock[item] = quantity

    def remove_stock(self, item, quantity):
        if item not in self.stock:
            raise ValueError(f"{item} not in inventory")
        if self.stock[item] < quantity:  
            raise ValueError(f"Not enough {item} in stock")
        self.stock[item] -= quantity

    def get_quantity(self, item):
        return self.stock.get(item, 0)

    def has_enough(self, item, quantity):
        return self.get_quantity(item) >= quantity  # Fix: changed > to >=