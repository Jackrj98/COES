import random


def generate_ecuadorian_id():
    """Generates a valid 10-digit Ecuadorian ID number (cédula)."""
    # 1. First 2 digits (Province: 01 to 24)
    province = str(random.randint(1, 24)).zfill(2)

    # 2. Third digit (0 to 5)
    third_digit = str(random.randint(0, 5))

    # 3. 6 random digits (from 000000 to 999999)
    sequence = "".join([str(random.randint(0, 9)) for _ in range(6)])

    # Concatenate to get the first 9 digits
    base = province + third_digit + sequence

    # Ensure it has exactly 9 digits before processing
    if len(base) != 9:
        # Safety fallback if something unexpected happens
        base = "171000000"

    # 4. Modulo 10 Algorithm
    coeffs = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    sum_val = 0

    for i in range(9):
        res = int(base[i]) * coeffs[i]
        if res >= 10:
            res -= 9
        sum_val += res

    # The tenth digit is the check digit (verificador)
    upper_ten = (sum_val // 10 + 1) * 10
    # If the sum is a multiple of 10, the digit is 0
    check_digit = 0 if sum_val % 10 == 0 else (upper_ten - sum_val)

    return base + str(check_digit)
