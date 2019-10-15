import os
import argparse
import csv
import zlib
import shutil
import re
import json
import time
import datetime
import typing
import sys

def replaceSurrogates(string: str) -> str:
    return string.encode('utf16', 'surrogatepass').decode('utf16', 'replace')

def colourString(string: str, colour: str) -> str:
    colours = {
        "HEADER" : '\033[95m',
        "OKBLUE" : '\033[94m',
        "OKGREEN" : '\033[92m',
        "WARNING" : '\033[93m',
        "FAIL" : '\033[91m',
        "ENDC" : '\033[0m',
        "BOLD" : '\033[1m',
        "UNDERLINE" : '\033[4m'
    }
    string = replaceSurrogates(string)
    return colours[colour] + string + colours["ENDC"]

def prettyCrc(prev: int) -> str:
    return "%X" %(prev & 0xFFFFFFFF)

def prettySize(size: float) -> str:
    if size > 10**9:
        return "{:<10}".format("%s GB" %(round(size/10**9, 2)))
    elif size > 10**6:
        return "{:<10}".format("%s MB" %(round(size/10**6, 2)))
    elif size > 10**3:
        return "{:<10}".format("%s KB" %(round(size/10**3, 2)))
    else:
        return "{:<10}".format("%s B" %(size))

def writeCsv(fName: str, data: list, enc = None, delimiter = ",") -> None:
    if not os.path.isdir(os.path.dirname(fName)):
        os.makedirs(os.path.dirname(fName))
    with open(fName, "w", newline="", encoding=enc, errors="backslashreplace") as f:
        writer = csv.writer(f, delimiter=delimiter)
        for row in data:
            writer.writerow(row)

def readJson(fName: str) -> dict:
    if os.path.exists(fName):
        with open(fName, "r", errors="ignore") as json_file:
            data = json.load(json_file)
        return data
    return {}

def writeJson(fName: str, data: dict) -> None:
    if not os.path.isdir(os.path.dirname(fName)):
        os.makedirs(os.path.dirname(fName))
    with open(fName, "w", errors="ignore") as json_file:
        json.dump(data, json_file, indent=1, separators=(',', ': '))


class ArgparseCustomFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text[:2] == 'F!':
            return text.splitlines()[1:]
        return argparse.HelpFormatter._split_lines(self, text, width)


class ConfigObject:
    def __init__(self, config: dict):
        # default config (copy argparse)
        self.source = None
        self.dest = None
        self.m = "mirror"
        self.c = "KS"
        self.r = 1
        self.d = False
        self.suppress = False
        self.goahead = True
        self.norun = False
        self.save = False
        self.load = False
        # default config (additional)
        self.conflict_dir = ".backupy"
        self.config_dir = ".backupy"
        self.cleanup = True
        self.filter_list_test = [re.compile(x) for x in [r'.+', r'^[a-z]+$', r'^\d+$']]
        self.backup_time_override = False
        self.csv = True
        self.load_json = True
        self.save_json = True
        # load config
        for key in config:
            self.__setattr__(key, config[key])
        # suppress logging
        if self.suppress:
            self.csv, self.save_json = False, False


class DirInfo:
    def __init__(self, directory: str, crc_mode: int,  config_dir: str, ignored_folders: list = []):
        self.file_dicts = {}
        self.empty_dirs = []
        self.loaded_dicts = {}
        self.loaded_diffs = []
        self.dir = directory
        self.crc_mode = crc_mode
        self.config_dir = config_dir
        self.ignored_paths = []
        for f in ignored_folders:
            p = os.path.abspath(os.path.join(directory, f))
            self.ignored_paths.append(p)

    def crc(self, fileName: str, prev: int = 0) -> int:
        with open(fileName,"rb") as f:
            for line in f:
                prev = zlib.crc32(line, prev)
        return prev

    def dirStats(self) -> dict:
        total_crc = 0
        file_count = 0
        dir_count = 0
        total_file_size = 0
        total_folder_size = 0
        for dir_path, sub_dir_list, file_list in os.walk(self.dir):
            if os.path.abspath(dir_path) not in self.ignored_paths:
                sub_dir_list.sort()
                dir_count += len(sub_dir_list)
                file_count += len(file_list)
                total_folder_size += os.path.getsize(dir_path)
                for f in sorted(file_list):
                    full_path = os.path.join(dir_path, f)
                    total_file_size += os.path.getsize(full_path)
                    total_crc += self.crc(full_path)
                    total_crc %= (0xFFFFFFFF + 1)
        return {"total_crc": total_crc, "file_count": file_count, "dir_count": dir_count, "total_file_size": total_file_size, "total_folder_size": total_folder_size}

    def scan(self) -> None:
        if os.path.isdir(self.dir):
            self.file_dicts = {}
            for dir_path, subdir_list, file_list in os.walk(self.dir):
                if os.path.abspath(dir_path) not in self.ignored_paths:
                    subdir_list.sort()
                    for subdir in subdir_list:
                        full_path = os.path.join(dir_path, subdir)
                        if len(os.listdir(full_path)) == 0:
                            relativePath = os.path.relpath(full_path, self.dir)
                            self.empty_dirs.append(relativePath)
                    for fName in sorted(file_list):
                        full_path = os.path.join(dir_path, fName)
                        relativePath = os.path.relpath(full_path, self.dir)
                        size = os.path.getsize(full_path)
                        mtime = os.path.getmtime(full_path)
                        if relativePath in self.loaded_dicts:
                            if self.loaded_dicts[relativePath]["size"] == size and self.loaded_dicts[relativePath]["mtime"] == mtime:
                                self.file_dicts[relativePath] = self.loaded_dicts[relativePath]
                            else:
                                self.file_dicts[relativePath] = {"size": size, "mtime": mtime}
                                self.loaded_diffs.append([relativePath, str(self.loaded_dicts[relativePath])])
                            if self.crc_mode == 3 and "crc" not in self.file_dicts[relativePath]:
                                self.file_dicts[relativePath]["crc"] = self.crc(full_path)
                        else:
                            self.file_dicts[relativePath] = {"size": size, "mtime": mtime}
                            self.loaded_diffs.append([relativePath, str(self.file_dicts[relativePath])])
                            if self.crc_mode == 3:
                                self.file_dicts[relativePath]["crc"] = self.crc(full_path)

    def getDirDict(self) -> dict:
        return self.file_dicts

    def getLoadedDiffs(self) -> list:
        return self.loaded_diffs

    def saveJson(self):
        writeJson(os.path.join(self.dir, self.config_dir, "dirinfo.json"), self.file_dicts)

    def loadJson(self):
        self.loaded_dicts = readJson(os.path.join(self.dir, self.config_dir, "dirinfo.json"))

    def scanCrc(self, relativePath: str) -> int:
        full_path = os.path.join(self.dir, relativePath)
        if ["crc"] not in self.file_dicts[relativePath]:
            self.file_dicts[relativePath]["crc"] = self.crc(full_path)
        return self.file_dicts[relativePath]["crc"]

    def fileMatch(self, f: str, file_dict1: dict, file_dict2: dict, secondInfo, crc_mode: int) -> bool:
        if crc_mode == 3:
            if file_dict1["crc"] == file_dict2["crc"]:
                return True
            else:
                return False
        if file_dict1["size"] == file_dict2["size"]:
            if file_dict1["mtime"] == file_dict2["mtime"]:
                if crc_mode == 2 and self.scanCrc(f) != secondInfo.scanCrc(f):
                    return False
                return True
            else:
                diff = abs(int(file_dict1["mtime"]) - int(file_dict2["mtime"]))
                if diff <= 1 or diff == 3600:
                    if crc_mode == 2 and self.scanCrc(f) != secondInfo.scanCrc(f):
                        return False
                    return True
                else:
                    return False

    def dirCompare(self, secondInfo, moves: bool = False, filter_list = False) -> tuple:
        file_list = list(self.file_dicts)
        second_dict = secondInfo.getDirDict()
        second_list = list(second_dict)
        crc_mode = min(self.crc_mode, secondInfo.crc_mode)
        if filter_list:
            file_list = filter(lambda x: any([True if r.match(x) else False for r in filter_list]), file_list)
            second_list = filter(lambda x: any([True if r.match(x) else False for r in filter_list]), second_list)
        selfOnly = []
        secondOnly = []
        changed = []
        moved = []
        for f in file_list:
            if f in second_list:
                if not self.fileMatch(f, self.file_dicts[f], second_dict[f], secondInfo, crc_mode):
                    changed.append(f)
            else:
                selfOnly.append(f)
        for f in second_list:
            if not f in file_list:
                secondOnly.append(f)
        if moves:
            for f1 in selfOnly:
                for f2 in secondOnly:
                    if self.fileMatch(f, self.file_dicts[f1], second_dict[f2], secondInfo, crc_mode):
                        selfOnly.remove(f1)
                        secondOnly.remove(f2)
                        moved.append({"source": f1, "dest": f2})
        return selfOnly, secondOnly, changed, moved


class BackupManager:
    def __init__(self, args):
        # init logging
        self.log = []
        self.backup_time = datetime.datetime.now().strftime("%y%m%d-%H%M")
        # init config
        if type(args) != dict:
            args = vars(args)
        self.config = ConfigObject(args)
        # save or load
        if self.config.save:
            self.saveJson()
        elif self.config.load:
            self.loadJson()
        # copy and check source & dest
        self.source_root = self.config.source
        if not os.path.isdir(self.source_root):
            print(colourString("Invalid source directory: " + self.source_root, "FAIL"))
            sys.exit()
        self.dest_root = self.config.dest
        if self.dest_root == None:
            print(colourString("Destination directory not provided", "FAIL"))
            sys.exit()
        # debugging
        self.log.append(["CONFIG", str(vars(self.config))])
        if self.config.backup_time_override:
            self.backup_time = self.config.backup_time_override

    def printFileInfo(self, header: str, f: str, d: dict):
        self.log.append([header, f] + [str(d[f])])
        s = colourString(header, "OKBLUE") + replaceSurrogates(f) + "\n\t"
        s = s + colourString(" Size: ", "OKBLUE") + prettySize(d[f]["size"])
        s = s + colourString(" Modified: ", "OKBLUE") + time.ctime(d[f]["mtime"])
        if "crc" in d[f]:
            s = s + colourString(" Hash: ", "OKBLUE") + prettyCrc(d[f]["crc"])
        print(s)

    def printFiles(self, l: list, d: dict):
        for f in l:
            self.printFileInfo("File: ", f, d)

    def printChangedFiles(self, l: list, d1: dict, d2: dict):
        for f in l:
            self.printFileInfo("Source: ", f, d1)
            self.printFileInfo("Dest: ", f, d2)

    def printMovedFiles(self, l: list, d1: dict, d2: dict):
        for f in l:
            self.printFileInfo("Source: ", f["source"], d1)
            self.printFileInfo("Dest: ", f["dest"], d2)

    def removeFiles(self, root: str, files: list):
        for f in files:
            try:
                self.log.append(["removeFile()", root, f])
                if not self.config.norun:
                    path = os.path.join(root, f)
                    os.remove(path)
                    if self.config.cleanup:
                        head = os.path.dirname(path)
                        if len(os.listdir(head)) == 0:
                            os.removedirs(head)
            except Exception as e:
                self.log.append(["REMOVE ERROR", str(e)])
                print(e)

    def copyFile(self, source_root: str, dest_root: str, source_file: str, dest_file: str):
        try:
            self.log.append(["copyFile()", source_root, dest_root, source_file, dest_file])
            if not self.config.norun:
                dest = os.path.join(dest_root, dest_file)
                if not os.path.isdir(os.path.dirname(dest)):
                    os.makedirs(os.path.dirname(dest))
                shutil.copy2(os.path.join(source_root, source_file), dest)
        except Exception as e:
            self.log.append(["COPY ERROR", str(e)])
            print(e)

    def copyFiles(self, source_root: str, dest_root: str, source_files: str, dest_files: str):
        for i in range(len(source_files)):
            self.copyFile(source_root, dest_root, source_files[i], dest_files[i])
    
    def moveFile(self, source_root: str, dest_root: str, source_file: str, dest_file: str):
        try:
            self.log.append(["moveFile()", source_root, dest_root, source_file, dest_file])
            if not self.config.norun:
                source = os.path.join(source_root, source_file)
                dest = os.path.join(dest_root, dest_file)
                if not os.path.isdir(os.path.dirname(dest)):
                    os.makedirs(os.path.dirname(dest))
                shutil.move(source, dest)
                if self.config.cleanup:
                    head = os.path.dirname(source)
                    if len(os.listdir(head)) == 0:
                        os.removedirs(head)
        except Exception as e:
            self.log.append(["MOVE ERROR", str(e)])
            print(e)

    def moveFiles(self, moved: list, reverse: bool = False):
        # conflicts shouldn't happen since moved is a subset of files from sourceOnly and destOnly
        for f in moved:
            if reverse:
                dest = self.source_root
                oldLoc = f["source"]
                newLoc = f["dest"]
            else:
                dest = self.dest_root
                oldLoc = f["dest"]
                newLoc = f["source"]
            self.moveFile(dest, dest, oldLoc, newLoc)

    def getConflictDest(self, root: str, fpath: str) -> str:
        conflict_path = os.path.join(self.config.conflict_dir, self.backup_time, fpath)
        return conflict_path

    def handleConflicts(self, source, dest, source_dict, dest_dict, changed, conflict_resolution):
        for fp in changed:
            cp = self.getConflictDest(dest, fp)
            if conflict_resolution == "AO":
                if dest_dict[fp]["mtime"] < source_dict[fp]["mtime"]:
                    self.moveFile(dest, dest, fp, cp)
                    self.copyFile(source, dest, fp, fp)
                else:
                    self.copyFile(source, dest, fp, cp)
            elif conflict_resolution == "AS":
                self.copyFile(source, dest, fp, cp)
            elif conflict_resolution == "AD":
                self.moveFile(dest, dest, fp, cp)
                self.copyFile(source, dest, fp, fp)
            elif conflict_resolution == "KN":
                if dest_dict[fp]["mtime"] < source_dict[fp]["mtime"]:
                    self.copyFile(source, dest, fp, fp)
            elif conflict_resolution == "KS":
                self.copyFile(source, dest, fp, fp)
            elif conflict_resolution == "KD":
                pass
            else:
                break

    def handleSyncConflicts(self, source, dest, source_dict, dest_dict, changed, conflict_resolution):
        for fp in changed:
            cp = self.getConflictDest(dest, fp)
            if conflict_resolution == "AO":
                if dest_dict[fp]["mtime"] < source_dict[fp]["mtime"]:
                    self.moveFile(dest, dest, fp, cp)
                    self.copyFile(source, dest, fp, fp)
                else:
                    self.moveFile(source, source, fp, cp)
                    self.copyFile(dest, source, fp, fp)
            elif conflict_resolution == "AS":
                self.moveFile(source, source, fp, cp)
                self.copyFile(dest, source, fp, fp)
            elif conflict_resolution == "AD":
                self.moveFile(dest, dest, fp, cp)
                self.copyFile(source, dest, fp, fp)
            elif conflict_resolution == "KN":
                if dest_dict[fp]["mtime"] < source_dict[fp]["mtime"]:
                    self.copyFile(source, dest, fp, fp)
                else:
                    self.copyFile(dest, source, fp, fp)
            elif conflict_resolution == "KS":
                self.copyFile(source, dest, fp, fp)
            elif conflict_resolution == "KD":
                self.copyFile(dest, source, fp, fp)
            else:
                break

    def saveJson(self):
        self.config.save, self.config.load = False, False
        writeJson(os.path.join(self.config.source, self.config.config_dir, "config.json"), vars(self.config))

    def loadJson(self):
        config = readJson(os.path.join(self.config.source, self.config.config_dir, "config.json"))
        self.config = ConfigObject(config)

    def backup(self):
        # scan directories
        source = DirInfo(self.source_root, self.config.r, self.config.config_dir, [self.config.conflict_dir])
        dest = DirInfo(self.dest_root, self.config.r, self.config.config_dir, [self.config.conflict_dir])
        if self.config.load_json:
            source.loadJson()
            dest.loadJson()
        source.scan()
        source_dict = source.getDirDict()
        dest.scan()
        dest_dict = dest.getDirDict()
        dest_diffs = dest.getLoadedDiffs()
        if self.config.m != "sync" and len(dest_diffs) >= 1:
            self.log.append(["WARNING, THE FOLLOWING FILES IN DESTINATION HAVE CHANGED SINCE LAST SCAN"])
            self.log += dest_diffs
            print(colourString("Some files in the destination folder have changed since the last scan, see log for details", "WARNING"))
            if self.config.csv:
                writeCsv(os.path.join(self.source_root, self.config.config_dir, "log-" + self.backup_time + ".csv"), self.log)
        sourceOnly, destOnly, changed, moved = source.dirCompare(dest, self.config.d)
        if self.config.save_json:
            source.saveJson()
            dest.saveJson()
        # print differences
        print(colourString("Source Only", "HEADER"))
        self.log.append("Source Only")
        self.printFiles(sourceOnly, source_dict)
        print(colourString("Destination Only", "HEADER"))
        self.log.append("Destination Only")
        self.printFiles(destOnly, dest_dict)
        print(colourString("File Conflicts", "HEADER"))
        self.log.append("File Conflicts")
        self.printChangedFiles(changed, source_dict, dest_dict)
        if self.config.d:
            print(colourString("Moved Files", "HEADER"))
            self.log.append("Moved Files")
            self.printMovedFiles(moved, source_dict, dest_dict)
        # wait for go ahead
        if not self.config.goahead:
            go = input("Continue (y/N)? ")
            if go[0].lower() != "y":
                self.log.append("Aborted")
                if self.config.csv:
                    writeCsv(os.path.join(self.source_root, self.config.config_dir, "log-" + self.backup_time + ".csv"), self.log)
                return 1
        # Backup operations
        if self.config.m == "mirror":
            self.copyFiles(self.source_root, self.dest_root, sourceOnly, sourceOnly)
            self.removeFiles(self.dest_root, destOnly)
            if self.config.d:
                self.moveFiles(moved)
            self.handleConflicts(self.source_root, self.dest_root, source_dict, dest_dict, changed, self.config.c)
        elif self.config.m == "backup":
            self.copyFiles(self.source_root, self.dest_root, sourceOnly, sourceOnly)
            if self.config.d:
                self.moveFiles(moved)
            self.handleConflicts(self.source_root, self.dest_root, source_dict, dest_dict, changed, self.config.c)
        elif self.config.m == "sync":
            self.copyFiles(self.source_root, self.dest_root, sourceOnly, sourceOnly)
            self.copyFiles(self.dest_root, self.source_root, destOnly, destOnly)
            if self.config.d:
                self.moveFiles(moved)
            self.handleSyncConflicts(self.source_root, self.dest_root, source_dict, dest_dict, changed, self.config.c)
        self.log.append("Completed")
        if self.config.csv:
            writeCsv(os.path.join(self.source_root, self.config.config_dir, "log-" + self.backup_time + ".csv"), self.log)


def main():
    parser = argparse.ArgumentParser(description="Simple python script for backing up directories", formatter_class=ArgparseCustomFormatter)
    parser.add_argument("source", action="store", type=str,
                        help="Path of source")
    parser.add_argument("dest", action="store", type=str, nargs="?", default=None,
                        help="Path of destination")
    parser.add_argument("-m", type=str, default="mirror", metavar="mode", choices=["mirror", "backup", "sync"],
                        help="F!\n"
                             "Backup mode (str):\n"
                             "How to handle files that exist only on one side?\n"
                             "mirror (default)\n"
                             " [source -> destination, delete destination only files]\n"
                             "backup\n"
                             " [source -> destination, keep destination only files]\n"
                             "sync\n"
                             " [source <-> destination]")
    parser.add_argument("-c", type=str, default="KS", metavar="mode", choices=["KS", "KD", "KN", "NO", "AS", "AD", "AO"],
                        help="F!\n"
                             "Conflict resolution mode (str):\n"
                             "How to handle files that exist on both sides but differ?\n"
                             "KS [keep source] (default)\n"
                             "KD [keep dest]\n"
                             "KN [keep newer]\n"
                             "NO [do nothing]\n"
                             "AS [archive source]\n"
                             "AD [archive dest]\n"
                             "AN [archive older]")
    parser.add_argument("-r", type=int, default=1, metavar="mode", choices=[1, 2, 3],
                        help="F!\n"
                             "CRC mode (int):\n"
                             "Compare file hashes\n"
                             "1 none (default)\n"
                             "2 only for files with matching size and date\n"
                             "3 all files")
    parser.add_argument("-d", action="store_true",
                        help="Try and detect moved files")
    parser.add_argument("--suppress", action="store_true",
                        help="Suppress logging; by default logs are written to source/.backupy/log-yymmdd-HHMM.csv and /.backupy/dirinfo.json")
    parser.add_argument("--goahead", action="store_true",
                        help="Go ahead without prompting for confirmation")
    parser.add_argument("-n", "--norun", action="store_true",
                        help="Simulate the run")
    parser.add_argument("-s", "--save", action="store_true",
                        help="Save configuration in source")
    parser.add_argument("-l", "--load", action="store_true",
                        help="Load configuration from source")
    args = parser.parse_args()
    backup_manager = BackupManager(args)
    backup_manager.backup()
    print("Backup complete!")

if __name__ == "__main__":
    sys.exit(main())


# TODO
# 1. Increase test coverage
# 2. Release gooey build
# 3. Copy/remove empty directories using file rules