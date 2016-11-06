import random


def true_by_percentage(percentage):
    rand = random.randint(0, 9999)
    return rand < percentage * 100
