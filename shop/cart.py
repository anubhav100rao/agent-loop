"""Shopping cart for the shop checkout."""

TAX_RATE = 0.10  # 10% sales tax

COUPONS = {  # code -> percent off
    "SAVE10": 10,
    "SAVE20": 20,
}


class Cart:
    def __init__(self):
        self.items = []  # list of (item, price, qty)
        self.discount_pct = 0

    def add(self, item, price, qty=1):
        if qty < 1:
            raise ValueError("qty must be at least 1")
        self.items.append((item, price, qty))

    def apply_coupon(self, code):
        if code not in COUPONS:
            raise ValueError(f"unknown coupon: {code}")
        self.discount_pct = COUPONS[code]

    def subtotal(self):
        return sum(price * qty for _, price, qty in self.items)

    def total(self):
        """Amount charged: coupon comes off first, then tax is added."""
        subtotal = self.subtotal()
        tax = subtotal * TAX_RATE
        discount = subtotal * self.discount_pct / 100
        return round(subtotal + tax - discount, 2)
