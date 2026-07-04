PRICES = {
    "apple": 0.50,
    "bread": 2.25,
    "milk": 1.75,
}

def get_price(item):
    if item not in PRICES:
        raise KeyError(f"No price found for {item}")
    return PRICES[item]

def calculate_subtotal(item, quantity):
    price = get_price(item)
    return price * quantity  

def apply_tax(subtotal, tax_rate=0.08):
    return subtotal + (subtotal * tax_rate)