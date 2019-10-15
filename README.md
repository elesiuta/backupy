# backupy

```
usage: backupy [-h] [-m mode] [-c mode] [-r mode] [-d] [--suppress]
               [--goahead] [-n] [-s] [-l]
               source [dest]

Simple python script for backing up directories

positional arguments:
  source       Path of source
  dest         Path of destination

optional arguments:
  -h, --help   show this help message and exit
  -m mode      Backup mode (str):
               How to handle files that exist only on one side?
               mirror (default)
                [source -> destination, delete destination only files]
               backup
                [source -> destination, keep destination only files]
               sync
                [source <-> destination]
  -c mode      Conflict resolution mode (str):
               How to handle files that exist on both sides but differ?
               KS [keep source] (default)
               KD [keep dest]
               KN [keep newer]
               NO [do nothing]
               AS [archive source]
               AD [archive dest]
               AN [archive older]
  -r mode      CRC mode (int):
               Compare file hashes
               1 none (default)
               2 only for files with matching size and date
               3 all files
  -d           Try and detect moved files
  --suppress   Suppress logging; by default logs are written to
               source/.backupy/log-yymmdd-HHMM.csv and /.backupy/dirinfo.json
  --goahead    Go ahead without prompting for confirmation
  -n, --norun  Simulate the run
  -s, --save   Save configuration in source
  -l, --load   Load configuration from source
```
