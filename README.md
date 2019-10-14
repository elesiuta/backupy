# backupy

```
usage: backu.py [-h] [-m mode] [-c conflict-resolution] [-d] [--crc mode]
                [--cleanup True|False] [-n] [-w] [--goahead]
                source dest

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
  -w, --csv             Write log.csv in os.getcwd() of results
  --goahead             Go ahead without prompting for confirmation
```
