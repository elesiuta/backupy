import dataclasses
import typing
from .backupman import BackupManager
from .cli import main
from .config import ConfigDataClass
from .utils import version

__all__ = ["create_job", "run", "start_gui"]


def create_job(config: typing.Union[dict, ConfigDataClass]) -> BackupManager:
    """Create a new job for a given configuration, returns a BackupManager object"""
    if type(config) != dict:
        config = dataclasses.asdict(config)
    return BackupManager(config)


def run(config: typing.Union[dict, ConfigDataClass]) -> int:
    """Execute backupy for a given configuration"""
    if type(config) != dict:
        config = dataclasses.asdict(config)
    backup_man = BackupManager(config)
    return backup_man.run()


def start_gui():
    """Launch the GUI (DEPRECATED)"""
    from .gui import main_gui
    main_gui()
