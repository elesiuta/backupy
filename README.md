# BackuPy
## Features
- Backup, Mirror, and Sync Modes
- Compare files using attributes or CRCs
- Files are always archived before being deleted or overwritten by default
- JSON formatted database for tracking files
- Concise logs as csv files
- Save and load your configuration
- Perform a dry run to test your configuration
- Works on both new and existing backup directories
- Filter files with regular expressions
## Under the hood
- Easy to use in scripts
- Clear and easy to verify code, the only functions that touch your files are: copyFile(), moveFile(), and  removeFile()
- Console version uses only the Python standard library
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
## Command Line Interface
```
usage: backupy [options] -- <source> <dest>
       backupy <source> <dest> [options]
       backupy <source> --load [--norun]
       backupy -h | --help

BackuPy: A simple backup program in python with an emphasis on transparent
behaviour

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
## Links
- https://github.com/elesiuta/backupy
- https://pypi.org/project/BackuPy/
