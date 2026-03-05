import os
import yaml
from pathlib import Path

config_dir = Path.home() / "AppData" / "Local" / "ngrok"
config_dir.mkdir(parents=True, exist_ok=True)
config_path = config_dir / "ngrok.yml"

config = {}
if config_path.exists():
    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

config["authtoken"] = "cr_3AHlrwb5URKLD9LrjLGePlbV9MT"
config["version"] = "2"

with open(config_path, "w") as f:
    yaml.dump(config, f)

print(f"Token written to {config_path}")
