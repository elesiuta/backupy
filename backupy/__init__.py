from .backupman import BackupManager
from .cli import main
from .utils import getVersion


def createJob(config: dict) -> BackupManager:
    """Create a new job for a given configuration, returns a BackupManager object"""
    return BackupManager(config)


def run(config: dict):
    """Execute backupy for a given configuration"""
    backup_man = BackupManager(config)
    backup_man.run()


def start_gui():
    from .gui import main_gui
    main_gui()
