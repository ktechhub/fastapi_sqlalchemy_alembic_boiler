import random


def generate_verification_code(n=5):
    return "".join(random.choice("01234567899876543210") for i in range(n))


def generate_random_code(n=5):
    return "".join(
        random.choice("0123456789qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM")
        for i in range(n)
    )
