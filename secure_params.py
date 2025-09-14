# Copyright 2025 Renouvaud
# License GPL-3.0 or later (https://www.gnu.org/licenses/gpl-3.0)

""" Local functions """
from general import read_json

def get_apikey(path, inst, env):
    secure_params = read_json(f"{path}secure_params.json")
    api_keys = secure_params["api_keys"]
    
    for key, value in api_keys.items():
        if key == f"api_key_{inst}_{env}":
            return value

def get_sru_link(path, env):
    secure_params = read_json(f"{path}secure_params.json")
    sru_links = secure_params["sru_link"]

    for key, value in sru_links.items():
        if key == f"url_{env}":
            return value
