from .backupman import BackupManager
from .utils import FileOps

__all__ = ["create_job", "main", "run", "start_gui", "version"]


def create_job(config: dict) -> BackupManager:
    """Create a new job for a given configuration (see config.json or config.py for key names), returns a BackupManager object"""
    return BackupManager(config)


def main():
    """Start the CLI"""
    import sys
    from .cli import main
    sys.exit(main())


def run(config: dict) -> int:
    """Execute backupy for a given configuration (see config.json or config.py for key names), returns exit status"""
    backup_man = BackupManager(config)
    return backup_man.run()


def start_gui():
    """Launch the GUI (DEPRECATED)"""
    from .gui import main_gui
    main_gui()


def version() -> str:
    """Get BackuPy version"""
    from .utils import getVersion
    return getVersion()
