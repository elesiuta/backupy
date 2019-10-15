# backupy

```
usage: backupy [-h] [-m mode] [-c mode] [-r mode] [-d] [--noarchive]
               [--suppress] [--goahead] [-n] [-s] [-l]
               source [dest]

Simple python script for backing up directories

positional arguments:
  source       Path of source
  dest         Path of destination

optional arguments:
  -h, --help   show this help message and exit
  -m mode      Backup mode:
               How to handle files that exist only on one side?
                 MIRROR (default)
                   [source-only -> destination, delete destination-only]
                 BACKUP
                   [source-only -> destination, keep destination-only]
                 SYNC
                   [source-only -> destination, destination-only -> source]
  -c mode      Conflict resolution mode:
               How to handle files that exist on both sides but differ?
                 SOURCE (default)
                   [copy source to destination]
                 DEST
                   [copy destination to source]
                 NEW
                   [copy newer to opposite side]
                 NO
                   [do nothing]
  -r mode      CRC mode:
               How to compare files that exist on both sides?
                 NONE (default)
                   [only compare file size and time, fastest]
                 MATCH
                   [only compare CRC for files with matching size and time]
                 ALL
                   [compare CRC first for all files, slowest]
  -d           Try and detect moved files
  --noarchive  Disable archiving, by default files are moved to
               /.backupy/yymmdd-HHMM/ on their respective side before being
               overwritten
  --suppress   Suppress logging; by default logs are written to
               source/.backupy/log-yymmdd-HHMM.csv and /.backupy/dirinfo.json
  --goahead    Go ahead without prompting for confirmation
  -n, --norun  Simulate the run
  -s, --save   Save configuration in source
  -l, --load   Load configuration from source
```
