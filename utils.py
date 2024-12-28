# utils.py
import json
import os

def save_settings(settings):
    with open('settings.json', 'w', encoding='utf-8') as f:
        json.dump(settings, f)

def load_settings():
    if os.path.exists('settings.json'):
        with open('settings.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"model": "gpt-3.5-turbo-16k"} #gpt-3.5-turbo, gpt-3.5-turbo-16k
