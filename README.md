# [BackuPy](#backupy)
  - [Installation](#installation)
  - [Features](#features)
  - [Design Goals](#design-goals)
  - [Usage Description](#usage-description)
  - [Command Line Interface](#command-line-interface)
  - [Extra Configuration Options](#extra-configuration-options)
  - [Building From Source](#building-from-source)
## [Installation](#installation)
- Install the latest release from PyPI (supports all platforms with Python and has no other dependencies)
```
pip install backupy --upgrade
```
## [Features](#features)
- Backup, Mirror, and Sync Modes
- Compare files using attributes or CRCs
- View changed file tree with curses
- Detection and alerts of corrupted files
- Detection and alerts of unexpected file modifications on destination outside of backups and mirrors, or sync conflicts (a file was modified on both sides since the last sync)
- JSON formatted database for tracking files and CSV formatted logs
- Files are always safe by default, being moved to an identically structured archive directory before being deleted or overwritten
- Filter files with regular expressions
## [Design Goals](#design-goals)
- Backups should be future proof and verifiable, even without BackuPy
  - uses [file-based increments](https://wiki.archlinux.org/index.php/Synchronization_and_backup_programs#File-based_increments) and human readable database/log files that are also easy to parse
- Code should be simple and easy to verify to ensure predicable and reliable operation
  - a callgraph is available under analysis
  - all the source code is under backupy
- Follow the principle of least astonishment
  - clear backup behaviour between directories, the current status of files and how they will be handled upon execution should be perfectly obvious
- Avoid feature creep and duplicating other programs
  - no delta-transfer (but you can use rsync as a backend or monkey patch the copy function to use any other program)
  - no network storage or FUSE support (these must be mounted by another program for BackuPy to see them)
  - no backup encryption (use encrypted storage)
  - no filesystem monitoring (this is not a continuous backup/sync program)
## [Usage Description](#usage-description)
- Source and destination directories can be any directory accessible via the computer's file system
- Destination can be empty or contain files from a previous backup (even one made without BackuPy), matching files on both sides will be skipped
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
- Test your settings first with the "dry-run" flag
- By default, you will always be notified of any changes, unexpected modifications, sync conflicts, or file corruption before being prompted to continue, cancel, or skip selected files
- You can also "restore" files with BackuPy by swapping your source and destination
## [Command Line Interface](#command-line-interface)
```
usage: backupy [options] -- <source> <dest>
       backupy <source> <dest> [options]
       backupy <source> --load [-c mode] [--dbscan] [--dry-run]
       backupy -h | --help

BackuPy: A simple backup program in python with an emphasis on data integrity
and transparent behaviour

positional arguments:
  source       Path to source
  dest         Path to destination

optional arguments:
  -h, --help   show this help message and exit

file mode options:

  -m mode      Main mode: for files that exist only on one side
                 MIRROR (default)
                   [source-only -> destination, delete destination-only]
                 BACKUP
                   [source-only -> destination, keep destination-only]
                 SYNC
                   [source-only -> destination, destination-only -> source]
  -s mode      Selection mode: for files that exist on both sides but differ
                 SOURCE (default)
                   [copy source to destination]
                 DEST
                   [copy destination to source]
                 NEW
                   [copy newer to opposite side]
                 NO
                   [do nothing]
  -c mode      Compare mode: for detecting which files differ
                 ATTR (default)
                   [compare file attributes: mod-time and size]
                 ATTR+
                   [compare file attributes and record CRC for changed files]
                 CRC
                   [compare file attributes and CRC for every file]

misc file options:

  --sync-delete
               Use the database to propagate deletions since the last sync
  --fi regex [regex ...]
               Filter: Only include files matching the regular expression(s)
               (include all by default, searches file paths)
  --fe regex [regex ...]
               Filter: Exclude files matching the regular expression(s)
               (exclude has priority over include, searches file paths)
  --noarchive  Disable archiving files before overwriting/deleting to:
                  <source|dest>/.backupy/Archives/yymmdd-HHMM/
                  <source|dest>/.backupy/Trash/yymmdd-HHMM/
  --nomoves    Do not detect when files are moved or renamed

execution options:

  --noprompt   Complete run without prompting for confirmation
  -d, --dbscan
               Only scan files to check and update their database entries
  -n, --dry-run
               Perform a dry run with no changes made to your files
  -q, --qconflicts
               Quit if database conflicts are detected (always notified)
                 -> unexpected changes on destination (backup and mirror)
                 -> sync conflict (file modified on both sides since last sync)
                 -> file corruption (ATTR+ or CRC compare modes)
  -v, --verify
               Verify CRC of copied files

backend options (experimental):

  --cold       Do not read files from destination and only use local databases
  --rsync      Use rsync backend

configuration options:

  --nolog      Disable writing log and file databases to:
                  <source>/.backupy/Logs/log-yymmdd-HHMM.csv
                  <source|dest>/.backupy/database.json
  -p, --posix  Force posix style paths on non-posix operating systems
  -k, --save   Save configuration to <source>/.backupy/config.json
  -l, --load   Load configuration from <source>/.backupy/config.json
```
## [Extra Configuration Options](#extra-configuration-options)
- Some options can only be set from the config.json file
  - source_unique_id & dest_unique_id
    - unique id for each folder, used when write_database_x2 is enabled, each assigned a random string by default
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
    - print program status updates to stdout, default = True
  - write_database_x2
    - write both source and destination databases to each side using their unique id, useful for syncing groups of more than two folders, default = False
  - write_log_dest
    - write a copy of the log to \<dest\>/\<log_dir\>/log-yymmdd-HHMM-dest.csv, default = False
## [Building From Source](#building-from-source)
- Run tests with
```
python setup.py test
```
- Building a python package
```
python setup.py sdist
```
- Building an executable with the GUI (deprecated, may rewrite with flutter)
```
pyinstaller build.spec
```
- You can package the executable on Windows by running setup.iss with Inno Setup
