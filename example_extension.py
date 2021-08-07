# example backupy extension to copy files using rsync
# you can run this script directly or use example_extension_setup.py to install
import subprocess
import backupy

def main():
    backupy.utils.FileOps.copy = lambda source, dest: subprocess.run(["rsync", "--archive", source, dest])
    backupy.main()

if __name__ == "__main__":
    main()
