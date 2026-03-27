"""
utils.py

Common utility functions used across modules.
"""


def clamp(value, min_value, max_value):
    """
    Clamp a value to a specified range.

    Parameters
    ----------
    value : float
        Input value
    min_value : float
        Lower bound
    max_value : float
        Upper bound

    Returns
    -------
    float
        Clamped value
    """
    return max(min_value, min(max_value, value))