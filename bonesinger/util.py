import random
import string


def strong_key_format(line, keys):
    for key, value in keys.items():
        line = line.replace("{{" + key + "}}", value)
    return line


def merge_dicts(*dict_args):
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def merge_dicts_and_lists(*dict_args):
    """ Deep merge dicts common way, but extend lists if it has some keys. """
    result = {}
    for dictionary in dict_args:
        for key, value in dictionary.items():
            if key in result and isinstance(result[key], dict):
                result[key] = merge_dicts(result[key], value)
            elif key in result and isinstance(result[key], list):
                result[key] = result[key] + value
            else:
                result[key] = value
    return result


def generate_random_string(length=8):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
