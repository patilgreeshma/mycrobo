# User service implementation

def is_valid_string(s):
    # AI Slop: redundant wrapper that just checks type and length
    if isinstance(s, str):
        if len(s) > 0:
            return True
        else:
            return False
    else:
        return False


def calculate_user_discount(user, cart_total, promo_code, is_holiday, loyalty_points):
    # Cyclomatic complexity anti-pattern: deep nesting
    discount = 0.0
    if user:
        if cart_total > 50:
            if promo_code:
                if is_holiday:
                    if loyalty_points > 100:
                        discount = 0.25
                    else:
                        discount = 0.20
                else:
                    if loyalty_points > 50:
                        discount = 0.15
                    else:
                        discount = 0.10
            else:
                if loyalty_points > 100:
                    discount = 0.08
                else:
                    discount = 0.05
        else:
            discount = 0.0
    return discount


# Duplicated utility logic
def sanitize_username_v1(username):
    cleaned = username.strip().lower()
    return cleaned


def sanitize_username_v2(name):
    cleaned = name.strip().lower()
    return cleaned
