import random

# Define a global variable for the interval
interval = 1800

def set_interval(new_interval):
    global interval
    interval = new_interval

def get_interval():
    global interval
    return interval

def set_random_interval(min_value, max_value):
    global interval
    interval = random.randint(min_value, max_value)