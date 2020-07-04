from .backupman import BackupManager
from .cli import main
from .utils import getVersion

__all__ = ["create_job", "run", "start_gui"]


def create_job(config: dict) -> BackupManager:
    """Create a new job for a given configuration, returns a BackupManager object"""
    return BackupManager(config)


def run(config: dict) -> int:
    """Execute backupy for a given configuration"""
    backup_man = BackupManager(config)
    return backup_man.run()


def start_gui():
    """Launch the GUI"""
    from .gui import main_gui
    main_gui()
