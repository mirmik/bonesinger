
def strong_key_format(line, keys):
    for key, value in keys.items():
        line = line.replace("{{" + key + "}}", value)
    return line
