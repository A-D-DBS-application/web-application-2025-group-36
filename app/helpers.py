def get_display(choices, value):
    for val, label in choices:
        if val == value:
            return label
    return str(value)
