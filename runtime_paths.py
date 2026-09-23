"""Writable data location shared by the packaged application and its logger."""
import os
from pathlib import Path
import sys


def packaged_data_dir():
    override = os.getenv('ALLMANAGERC_DATA_DIR')
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'AllManagerC'
    if sys.platform == 'win32':
        return Path(os.environ.get('APPDATA', str(Path.home()))) / 'AllManagerC'
    return Path.home() / '.local' / 'share' / 'AllManagerC'
