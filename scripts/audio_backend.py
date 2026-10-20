"""Load the private audio-preparer submodule only when preparing audio."""
import importlib.util
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent.parent / 'modules' / 'audio-preparer'


def load_preparer():
    package = BACKEND_ROOT / 'audio_preparer'
    entry = package / '__init__.py'
    if not entry.is_file():
        raise RuntimeError('Audio preparation module is missing. Run '
                           '`git submodule update --init --recursive` with access to '
                           'the private audio-preparer repository.')
    name = '_weekly_mixtape_audio_preparer'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, entry, submodule_search_locations=[str(package)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise
    return sys.modules[name].prepare_audio
