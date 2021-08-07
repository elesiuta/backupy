import sys
import time
import psutil

pid = int(sys.argv[1])
ppid = int(sys.argv[2])
backupy_backend = psutil.Process(pid)
backupy_frontend = psutil.Process(ppid)

while backupy_backend.is_running():
    if backupy_backend.parent() is not None and backupy_backend.parent().is_running() and backupy_frontend.is_running():
        time.sleep(0.1)
    else:
        backupy_backend.terminate()
