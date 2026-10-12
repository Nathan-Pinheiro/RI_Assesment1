import os
import sys
import yaml


CONFIG_FILENAME = 'config.yaml'


def find_config_path():
    """Localise config/config.yml dans le share installé (avec fallback source)."""
    try:
        from ament_index_python.packages import get_package_share_directory
        share = get_package_share_directory('ri_a1')
        candidate = os.path.join(share, 'config', CONFIG_FILENAME)
        if os.path.isfile(candidate):
            return candidate
    except Exception:
        pass

    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(here, '..', 'config', CONFIG_FILENAME)
    if os.path.isfile(candidate):
        return candidate

    return None


def load_config():
    """Charge config.yml et le retourne en dict. {} si introuvable."""
    path = find_config_path()
    if path is None:
        print(f'[config] {CONFIG_FILENAME} introuvable',
              file=sys.stderr, flush=True)
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
        print(f'[config] chargé depuis {path}',
              file=sys.stderr, flush=True)
        return cfg
    except Exception as e:
        print(f'[config] erreur lecture {path}: {e}',
              file=sys.stderr, flush=True)
        return {}