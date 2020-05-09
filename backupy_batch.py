import os
import backupy
source_list = []
for source in source_list:
    if os.path.isdir(source):
        backupy.run({"source": source, "load": True})
os.system("pause")
