import os
import shutil
for m in ["mirror", "sync", "backup"]:
    for m2 in ["source", "dest", "new", "no"]:
        os.makedirs(m + "-" + m2)
        shutil.copytree("dir A", m + "-" + m2 + "/dir A")
        shutil.copytree("dir B", m + "-" + m2 + "/dir B")
