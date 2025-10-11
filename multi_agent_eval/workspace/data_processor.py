from core import get_digits
from utils import get_unique
from validation import validate_input


def unique_digits(input):
    """Return all the unique digits in the input as a list of integers"""
    validate_input(input)
    return get_unique(get_digits(input))

