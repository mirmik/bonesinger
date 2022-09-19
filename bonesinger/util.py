
def strong_key_format(line, keys):
    for key, value in keys.items():
        line = line.replace("{{" + key + "}}", value)
    return line


def merge_dicts(*dict_args):
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result
