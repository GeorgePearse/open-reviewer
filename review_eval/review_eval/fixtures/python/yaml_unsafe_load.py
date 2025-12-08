# BAD: Using yaml.load() instead of yaml.safe_load()
# Expected issues: yaml.load, safe_load, arbitrary code execution
import yaml


def load_config(config_path: str):
    with open(config_path) as f:
        # This is dangerous - yaml.load can execute arbitrary code
        return yaml.load(f)
