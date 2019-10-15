# backupy

```
usage: backupy [-h] [-m mode] [-c conflict-resolution] [-d] [--crc mode]
                  [--cleanup True|False] [-n] [--suppress] [--goahead] [-s]
                  [-l]
                  source [dest]

Simple python script for backing up directories

positional arguments:
  source                Path of source
  dest                  Path of destination

optional arguments:
  -h, --help            show this help message and exit
  -m mode               How to handle files that exist only on one side?
                        Available modes: mirror [source -> destination, delete
                        destination only files] (default), backup [source ->
                        destination, keep destination only files] sync [source
                        <-> destination]
  -c conflict-resolution
                        How to handle files that exist on both sides but
                        differ? Available modes: KS [keep source] (default),
                        KD [keep dest], KN [keep newer], NO [do nothing], AS
                        [archive source], AD [archive dest], AN [archive
                        older]
  -d                    Try and detect moved files
  --crc mode            Compare file hashes, available modes: 1: none
                        (default) 2: matching date and time 3: all files
  --cleanup True|False  Remove directory if empty after a file move or
                        deletion (default: True)
  -n, --norun           Simulate the run
  --suppress            Suppress logging; by default logs are written to
                        source/.backupy/log-yymmdd-HHMM.csv and
                        /.backupy/dirinfo.json
  --goahead             Go ahead without prompting for confirmation
  -s, --save            Save configuration in source
  -l, --load            Load configuration from source
```
