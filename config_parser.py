separator = "="

def _load_config():
    properties = {}
    with open('config.properties', mode='rt', encoding='utf-8') as f:
        for line in f:
            if separator in line:
                name, value = line.split(separator, 1)
                properties[name.strip()] = value.strip()

    return properties

properties = _load_config()