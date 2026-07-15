# scanner_backend/manager_config.py
import os
import configparser
from .const import CONFIG_FILE, DEFAULT_SETTINGS, DEFAULT_RULES


def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE, encoding='utf-8')

    if 'Settings' not in config: config['Settings'] = {}
    if 'Rules' not in config: config['Rules'] = {}

    # 补全默认值。Beta 早期把部分 Settings 默认值写进 Rules；
    # 这里保持读取兼容，但把新的默认值放回正确 section。
    for k, v in DEFAULT_SETTINGS.items():
        if k not in config['Settings']:
            config['Settings'][k] = config['Rules'].get(k, v)

    for k, v in DEFAULT_RULES.items():
        if k not in config['Rules']:
            config['Rules'][k] = v
    return config


def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
    except Exception as e:
        print(f"Config Error: {e}")
