import os
import backupy
source_list = []
for source in source_list:
    if os.path.isdir(source):
        backup_manager = backupy.BackupManager({"source": source, "load": True})
        backup_manager.backup()
os.system("pause")
