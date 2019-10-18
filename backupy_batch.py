import system
import backupy
source_list = []
for source in source_list:
    backup_manager = BackupManager({"source": source, "l": True})
    backup_manager.backup()
os.system("pause")
