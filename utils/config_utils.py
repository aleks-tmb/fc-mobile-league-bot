import os

CONFIG = {}

def read_config():
    global CONFIG
    file_path = 'config.txt'
    if not os.path.exists(file_path):
        print("Config does not exist.")
        return

    try:
        with open(file_path, 'r') as file:
            for line in file.readlines():
                key, value = line.strip().split('=')
                CONFIG[key] = value
    except Exception as e:
        print(f"Error reading config: {e}")
        return
