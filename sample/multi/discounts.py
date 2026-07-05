def get_discount_rate(total):
    if total >= 100:
        return 0.20
    elif total >= 50:
        return 0.10
    elif total >= 20:  
        return 0.05
    else:
        return 0.0

def apply_discount(total, discount_rate):
    return total - (total * discount_rate)