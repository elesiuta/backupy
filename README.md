# [BackuPy](#backupy)
  - [Installation](#installation)
  - [Features](#features)
  - [Design Goals](#design-goals)
  - [Usage Description](#usage-description)
  - [Command Line Interface](#command-line-interface)
  - [Configuration File](#configuration-file)
  - [Building From Source](#building-from-source)
## [Installation](#installation)
- Install the latest release from PyPI (supports all platforms with Python and has no dependencies outside the standard library)
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
- Filter files with regular expressions
- Files are always safe by default, being moved to an identically structured archive directory before being deleted or overwritten
## [Design Goals](#design-goals)
- Backups should be future proof and verifiable, even without BackuPy
  - uses [file-based increments](https://wiki.archlinux.org/index.php/Synchronization_and_backup_programs#File-based_increments) and human readable database/log files that are also easy to parse
- Code should be simple and easy to verify to ensure predicable and reliable operation
  - a callgraph is available in `analysis/callgraph.svg`
  - there are only three, easy to follow functions (under `FileManager` in `backupy/fileman.py`) that ever touch your files, no more, no less, three shall be the number of thou functions, and the number of the functions shall be three
  - use trustworthy dependencies
- Follow the principle of least astonishment
  - clear backup behaviour between directories, the current status of files and how they will be handled upon execution should be perfectly obvious
- Avoid feature creep and duplicating other programs
  - no delta-transfer (extend with another backend)
  - no network storage or FUSE support (these must be mounted by another program for BackuPy to see them)
  - no backup encryption (use encrypted storage)
  - no filesystem monitoring (this is not a continuous backup/sync program)
- Easily extensible with other backends
  - all the low level functions used for file operations are under `FileOps` from `backupy.utils` for easy monkey patching (see `example_extension.py`)
## [Usage Description](#usage-description)
- Source and destination directories can be any directory accessible via the computer's file system
  - Destination can be empty or contain files from a previous backup (even one made without BackuPy), matching files on both sides will be skipped
  - Use the `--posix` flag if you plan on using BackuPy between Windows and any other OS
- `Main modes` (how to handle new and deleted files)
  - `Backup mode:` copies files that are only in source to destination
  - `Mirror mode:` copies files that are only in source to destination and deletes files that are only in destination
  - `Sync mode:` copies files that are only in source to destination and copies files that are only in destination to source
    - you may also want to use `--sync-delete` to propagate deletions
    - see `write_database_x2` in the [configuration file](#configuration-file) if syncing more than two folders
- `Selection modes` (which file to select in cases where different versions exist on both sides)
  - `Source mode:` copy source files to destination
  - `Destination mode:` copy destination files to source
  - `Newer mode:` copy newer files based on last modified time
  - `None mode:` don't copy either, differing files will only be logged for manual intervention
- `Compare modes` (how to detect which files have changed)
  - `Attribute mode:` compare file attributes (size and last modified time)
  - `Attribute+ mode:` compare file attributes and calculate CRCs only for new and changed files for future verification
  - `CRC mode:` compare file attributes and CRC for every file, and checks previously stored CRCs to detect corruption
    - you may also want to use `--verify` to verify the CRC of files after they're copied
- Test your options first with the `--dry-run` flag
- See [Command Line Interface](#command-line-interface) and [Configuration File](#configuration-file) below for all available options
- By default, you will always be notified of any changes, unexpected modifications, sync conflicts, or file corruption before being prompted to continue, cancel, or skip selected files
  - it is recommended to use `--qconflicts` if using `--noprompt`, especially if also using `--noarchive`
- By default, you will be prompted before any changes are made to your files and
  - overwritten files will be moved to `<source|dest>/.backupy/Archives/yymmdd-HHMM/<original path>`
  - deleted files will be moved to `<source|dest>/.backupy/Trash/yymmdd-HHMM/<original path>`
- Symbolic links to folders are never followed and always copied verbatim
- Symbolic links to files are followed by default, copying the referenced file, use `--nofollow` to copy symbolic links to files verbatim
- To restore files, just copy them over from your destination to source (or swap source and destination in BackuPy)
## [Command Line Interface](#command-line-interface)
```
usage: backupy [options] -- <source> <dest>
       backupy <source> <dest> [options]
       backupy <source> --load [-c mode] [--dbscan] [--dry-run]
       backupy -h | --help | --version

positional arguments:
  source       Path to source
  dest         Path to destination

optional arguments:
  -h, --help   show this help message and exit
  --version    show program's version number and exit

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
  --nofollow   Do not follow symlinks when copying files
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

  --cold       Do not scan files on destination and only use local databases
  --rsync      Use rsync for copying files

configuration options:

  --nolog      Disable writing log and file databases to:
                  <source>/.backupy/Logs/log-yymmdd-HHMM.csv
                  <source|dest>/.backupy/database.json
  -p, --posix  Force posix style paths on non-posix operating systems
  -k, --save   Save configuration to <source>/.backupy/config.json and exit
  -l, --load   Load configuration from <source>/.backupy/config.json and run

BackuPy is a simple backup program in python with an emphasis on data 
integrity and transparent behaviour - https://github.com/elesiuta/backupy 

BackuPy comes with ABSOLUTELY NO WARRANTY. This is free software, and you are 
welcome to redistribute it under certain conditions. See the GNU General 
Public Licence for details.
```
## [Configuration File](#configuration-file)
- The config file is saved to, and loaded from `<source>/.backupy/config.json`
  - it contains all the options from the command line interface along with some additional options
  - the only CLI options that can be used with `--load` and can override settings in `config.json` are `-c mode`, `--dbscan`, and `--dry-run`
    - the overrides can enable `--dbscan` or `--dry-run` but not disable
  - see `backupy/config.py` for where all the options and defaults are stored in code
  - below is a description of all the other options that are available
- `source_unique_id` & `dest_unique_id`
  - unique id for each folder, used when `write_database_x2` is enabled, each assigned a random string by default
- `archive_dir` = ".backupy/Archive"
  - can be any subdirectory
- `config_dir` = ".backupy"
  - can't be changed under normal operation
- `log_dir` = ".backupy/Logs"
  - can be any subdirectory
- `trash_dir` = ".backupy/Trash"
  - can be any subdirectory
- `cleanup_empty_dirs` = True
  - delete directories when they become empty
- `root_alias_log` = True
  - abbreviate absolute paths to source and dest with `<source>` and `<dest>` in logs
- `stdout_status_bar` = True
  - show progress status bar
- `verbose` = True
  - print list of differences between directories to stdout
- `write_database_x2` = False
  - write both source and destination databases to each side using their `unique_id`, useful for syncing groups of more than two folders or with the `--sync-delete` flag
- `write_log_dest` = False
  - write a copy of the log to `<dest>/<log_dir>/log-yymmdd-HHMM-dest.csv`
- `write_log_summary` = False
  - alternative log structure, written in addition to standard log
- `nocolour` = False
  - disable colour when printing to stdout
## [Building From Source](#building-from-source)
- Run tests with
```
python setup.py test
```
- Building a python package
```
python setup.py sdist
```
- Building an executable with the GUI (depends on [Gooey](https://pypi.org/project/Gooey/)) (deprecated, may rewrite with flutter)
```
pyinstaller build.spec
```
- You can package the executable on Windows by running setup.iss with Inno Setup
