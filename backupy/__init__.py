from .backupman import BackupManager

__all__ = ["create_job", "main", "run", "start_gui", "version"]


def create_job(config: dict) -> BackupManager:
    """Create a new job for a given configuration, returns a BackupManager object"""
    return BackupManager(config)


def main():
    """Start the CLI"""
    import sys
    from .cli import main
    if __name__ == "__main__":
        sys.exit(main())


def run(config: dict) -> int:
    """Execute BackuPy for a given configuration"""
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
