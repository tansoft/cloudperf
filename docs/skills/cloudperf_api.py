#!/usr/bin/env python3
import os, sys, json, requests

CONFIG_PATH = os.path.expanduser("~/.cloudperf/config.json")
TOKEN_PATH = os.path.expanduser("~/.cloudperf/.token")

def load_config():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    return {
        "api_base": os.environ.get("CLOUDPERF_API_BASE", cfg.get("api_base", "")).rstrip("/"),
        "username": os.environ.get("CLOUDPERF_USERNAME", cfg.get("username", "")),
        "password": os.environ.get("CLOUDPERF_PASSWORD", cfg.get("password", "")),
    }

def load_token():
    if os.path.exists(TOKEN_PATH):
        return open(TOKEN_PATH).read().strip()
    return ""

def save_token(token):
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(token)

def login(cfg):
    r = requests.get(f"{cfg['api_base']}/api/login", params={"username": cfg["username"], "password": cfg["password"]})
    r.raise_for_status()
    data = r.json()
    token = f"{data['token']}|{data['user']}|{data['auth']}"
    save_token(token)
    return token

def call_api(cfg, fn, params, retry=True):
    token = load_token()
    if not token:
        token = login(cfg)
    r = requests.get(f"{cfg['api_base']}/api/{fn}", params=params, cookies={"cp_token": token}, headers={"User-Agent": "cloudperf-skill"})
    if r.status_code == 403 and retry:
        save_token("")
        return call_api(cfg, fn, params, retry=False)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: cloudperf_api.py <function> [param=value ...]", file=sys.stderr)
        sys.exit(1)
    fn = sys.argv[1]
    params = {}
    for arg in sys.argv[2:]:
        k, v = arg.split("=", 1)
        params[k] = v
    cfg = load_config()
    if not cfg["api_base"]:
        print("Error: api_base not configured. Set CLOUDPERF_API_BASE or create ~/.cloudperf/config.json", file=sys.stderr)
        sys.exit(1)
    # hack for performance api with rawData=1 flag
    if fn == "rawdata":
        fn = "performance"
        params["rawData"] = 1
    result = call_api(cfg, fn, params)
    print(json.dumps(result, ensure_ascii=False, indent=2))
