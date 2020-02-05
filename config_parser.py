separator = "="
properties = {}

def load_config():
    with open('config.properties') as f:
        for line in f:
            if separator in line:
                name, value = line.split(separator, 1)
                properties[name.strip()] = value.strip()
