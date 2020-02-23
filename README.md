# BackuPy
## Quick Start
```
pip install backupy
backupy -h
```
## Installation
- Install the latest version from PyPI
```
pip install backupy --upgrade
```
- Or install the python package from the GitHub release page
- Or run the python file directly, all you need is backupy.py
- Or run it with the GUI, in which case you run backupy_gui.py from the same directory as backupy.py
- Or you can run BackuPy-Setup.exe from the GitHub release page to install it with the GUI for Windows 
## Features
- Backup, Mirror, and Sync Modes
- Compare files using attributes or CRCs
- Detection and alerts of corrupted files
- JSON formatted database for tracking files (human readable and easy to parse)
- Detection and alerts of unexpected file modifications on destination outside of backups and mirrors, or sync conflicts (a file was modified on both sides since the last sync)
- Files are always copied to an identically structured archive directory before being deleted or overwritten by default
- Easy to read logs as csv files
- Save and load your configuration
- Perform a dry run to test your configuration
- Works on both new and existing backup directories
- Filter file paths with regular expressions
## Under the Hood
- Easy to use in scripts (see backupy_batch.py for an example)
- Clear and easy to verify code, the only functions that touch your files are: copyFile(), moveFile(), and  removeFile()
- OS independent and console version only uses the Python standard library
- GUI available through Gooey and PySimpleGUI
## Usage Description
- Source and destination directories can be any accessible directory
- Destination can be empty or contain files from a previous backup, matching files on both sides will be skipped
- Main modes (how to handle new and deleted files)
  - Backup mode: copies files that are only in source to destination
  - Mirror mode: copies files that are only in source to destination and deletes files that are only in destination
  - Sync mode: copies files that are only in source to destination and copies files that are only in destination to source
- Selection modes (which file to select in cases where different versions exist on both sides)
  - Source mode: copy source files to destination
  - Destination mode: copy destination files to source
  - Newer mode: copy newer files based on last modified time
  - None mode: don't copy either, differing files will only be logged for manual intervention
- Compare modes (how to detect which files have changed)
  - Attribute mode: compare file attributes (size and last modified time)
  - Attribute+ mode: compare file attributes and calculate CRCs only for new and changed files for future verification
  - CRC mode: compare file attributes and CRC for every file, and checks previously stored CRCs to detect corruption
- Test your settings first with the 'norun' flag
## Example Usage
- Just type backupy followed by your source and destination directories, and any combination of options
- If you're unsure how something works, include "--norun" to see what would happen without actually doing anything
```
backupy "path/to/your/source directory/" "path/to/destination/" --norun
```
## Command Line Interface
```
usage: backupy [options] -- <source> <dest>
       backupy <source> <dest> [options]
       backupy <source> --load [--norun]
       backupy -h | --help

BackuPy: A simple backup program in python with an emphasis on data integrity
and transparent behaviour

positional arguments:
  source       Path of source
  dest         Path of destination

optional arguments:
  -h, --help   show this help message and exit
  -m mode      Main mode:
               How to handle files that exist only on one side?
                 MIRROR (default)
                   [source-only -> destination, delete destination-only]
                 BACKUP
                   [source-only -> destination, keep destination-only]
                 SYNC
                   [source-only -> destination, destination-only -> source]
  -s mode      Selection mode:
               How to handle files that exist on both sides but differ?
                 SOURCE (default)
                   [copy source to destination]
                 DEST
                   [copy destination to source]
                 NEW
                   [copy newer to opposite side]
                 NO
                   [do nothing]
  -c mode      Compare mode:
               How to detect files that exist on both sides but differ?
                 ATTR (default)
                   [compare file attributes: mod-time and size]
                 ATTR+
                   [compare file attributes and only store new CRC data]
                 CRC
                   [compare file attributes and CRC for every file]
  -f regex [regex ...]
               Filter: Only include files matching the regular expression(s)
               (include all by default)
  -ff regex [regex ...]
               Filter False: Exclude files matching the regular expression(s)
               (exclude has priority over include)
  --noarchive  Disable archiving files before overwriting/deleting to:
                 <source|dest>/.backupy/Archives/yymmdd-HHMM/
                 <source|dest>/.backupy/Trash/yymmdd-HHMM/
  --nolog      Disable writing to:
                 <source>/.backupy/Logs/log-yymmdd-HHMM.csv
                 <source|dest>/.backupy/database.json
  --nomoves    Do not detect when files are moved or renamed
  --noprompt   Complete run without prompting for confirmation
  --norun      Perform a dry run according to your configuration
  --save       Save configuration to <source>/.backupy/config.json
  --load       Load configuration from <source>/.backupy/config.json
```
## Extra Configuration Options
- Some options can only be set from the config file
  - archive_dir
    - can be any subdirectory, default = ".backupy/Archive"
  - config_dir
    - can't be changed under normal operation, default = ".backupy"
  - log_dir
    - can be any subdirectory, default = ".backupy/Logs"
  - trash_dir
    - can be any subdirectory, default = ".backupy/Trash"
  - cleanup_empty_dirs
    - delete directories when they become empty, default = True 
  - root_alias_log
    - replace source and dest paths with "\<source\>" and "\<dest\>" in logs, default = True
  - stdout_status_bar
    - show progress status bar, default = True
  - verbose
    - print more updates to stdout, default = True
  - force_posix_path_sep
    - always use a forward slash in paths, useful for keeping the same database on a drive shared between multiple operating systems, default = False
  - set_blank_crc_on_copy
    - normally database entries are copied along with files, this removes the CRC from the copied entry forcing BackuPy to calculate and check the CRC on the next run (with ATTR+) to ensure the copy was successful (CRC mode would calculate and check it regardless, but takes much longer since it would also recheck every file), default = False
  - quit_on_db_conflict
    - causes the run to automatically abort if there is any unexpected file modifications, sync conflicts, or file corruption detected, recommended if running with noprompt, default = False
## Building From Source
- Run tests with
```
python setup.py test
```
- Building a python package
```
python setup.py sdist
```
- Building an executable with the GUI
```
pyinstaller build.spec
```
- You can package the executable on Windows by running setup.iss with Inno Setup
## Links
- https://github.com/elesiuta/backupy
- https://pypi.org/project/BackuPy/
