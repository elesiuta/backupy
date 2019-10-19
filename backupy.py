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


### String manipulation functions ###

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

### File IO functions ###

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


class CopyStatus:
    def __init__(self, total: int, verbose: bool, progress_bar: bool = False):
        self.verbose = verbose
        self.progress_bar = progress_bar
        terminal_width = shutil.get_terminal_size()[0]
        if terminal_width < 16:
            self.verbose = False
        elif terminal_width < 80:
            self.progress_bar = True
        if self.verbose:
            if self.progress_bar:
                self.bar_len = min(68, terminal_width - 15)
                self.progress_scaled = 0
                self.progress = 0
                self.total = total
                sys.stdout.write("Copying: [" + "-"*self.bar_len + "]\b" + "\b"*self.bar_len)
                sys.stdout.flush()
            else:
                char_display = terminal_width - 4
                self.progress = 0
                self.total = str(total)
                self.digits = str(len(self.total))
                self.title = "Copying file "
                progress_str = str("{:>" + self.digits + "}").format(self.progress) + "/" + self.total + ": "
                self.msg_len = char_display - len(progress_str) - len(self.title)
                self.neg_msg_len = -1 * (self.msg_len - 25)
                sys.stdout.write("\r" + self.title + progress_str + " "*self.msg_len)
                sys.stdout.flush()

    def update(self, msg:str):
        if self.verbose:
            if self.progress_bar:
                self.progress += 1
                bar_progression = int(self.bar_len * self.progress // self.total) - self.progress_scaled
                self.progress_scaled += bar_progression
                sys.stdout.write("#" * bar_progression)
                sys.stdout.flush()
            else:
                self.progress += 1
                if len(msg) > self.msg_len:
                    msg = msg[:20] + "....." + msg[self.neg_msg_len:]
                else:
                    msg = msg + " " * int(self.msg_len - len(msg))
                progress_str = str("{:>" + self.digits + "}").format(self.progress) + "/" + self.total + ": "
                sys.stdout.write("\r" + self.title + progress_str + ": " + msg)
                sys.stdout.flush()

    def endProgress(self):
        if self.verbose:
            if self.progress_bar:
                sys.stdout.write("#" * (self.bar_len - self.progress_scaled) + "]\n")
                sys.stdout.flush()
            else:
                sys.stdout.write("\rCompleted!   " + " " * self.msg_len + "\n")
                sys.stdout.flush()


class ConfigObject:
    def __init__(self, config: dict):
        # default config (copy argparse)
        self.source = None
        self.dest = None
        self.m = "mirror"
        self.c = "source"
        self.r = "none"
        self.d = False
        self.noarchive = False
        self.suppress = False
        self.goahead = False
        self.norun = False
        self.save = False
        self.load = False
        # default config (additional)
        self.archive_dir = ".backupy"
        self.config_dir = ".backupy"
        self.cleanup = True
        self.filter_list_test = "[re.compile(x) for x in [r'.+', r'^[a-z]+$', r'^\d+$']]"
        self.backup_time_override = False
        self.csv = True
        self.load_json = True
        self.save_json = True
        self.verbose = True
        # load config
        for key in config:
            self.__setattr__(key, config[key])
        # suppress logging
        if self.suppress:
            self.csv, self.save_json = False, False


class DirInfo:
    def __init__(self, directory: str, crc_mode: int,  config_dir: str, ignored_folders: list = []):
        self.file_dicts = {}
        self.loaded_dicts = {}
        self.loaded_diffs = []
        self.dir = directory
        self.crc_mode = crc_mode
        self.config_dir = config_dir
        self.ignored_folders = ignored_folders[:]

    def getDirDict(self) -> dict:
        return self.file_dicts

    def getLoadedDiffs(self) -> list:
        return self.loaded_diffs

    def saveJson(self):
        writeJson(os.path.join(self.dir, self.config_dir, "dirinfo.json"), self.file_dicts)

    def loadJson(self):
        self.loaded_dicts = readJson(os.path.join(self.dir, self.config_dir, "dirinfo.json"))

    def crc(self, fileName: str, prev: int = 0) -> int:
        with open(fileName,"rb") as f:
            for line in f:
                prev = zlib.crc32(line, prev)
        return prev

    def scanCrc(self, relativePath: str) -> int:
        if "crc" not in self.file_dicts[relativePath]:
            full_path = os.path.join(self.dir, relativePath)
            self.file_dicts[relativePath]["crc"] = self.crc(full_path)
        return self.file_dicts[relativePath]["crc"]

    def dirStats(self) -> dict:
        total_crc = 0
        file_count = 0
        dir_count = 0
        total_file_size = 0
        total_folder_size = 0
        for dir_path, sub_dir_list, file_list in os.walk(self.dir):
            for folder in sub_dir_list:
                if folder in self.ignored_folders:
                    sub_dir_list.remove(folder)
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
                for folder in subdir_list:
                    if folder in self.ignored_folders:
                        subdir_list.remove(folder)
                subdir_list.sort()
                for subdir in subdir_list:
                    full_path = os.path.join(dir_path, subdir)
                    if len(os.listdir(full_path)) == 0:
                        relativePath = os.path.relpath(full_path, self.dir)
                        self.file_dicts[relativePath] = {"size": 0, "mtime": 0, "crc": 0, "dir": True}
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
                        if self.crc_mode == "all" and "crc" not in self.file_dicts[relativePath]:
                            self.file_dicts[relativePath]["crc"] = self.crc(full_path)
                    else:
                        self.file_dicts[relativePath] = {"size": size, "mtime": mtime}
                        self.loaded_diffs.append([relativePath, str(self.file_dicts[relativePath])])
                        if self.crc_mode == "all":
                            self.file_dicts[relativePath]["crc"] = self.crc(full_path)

    def fileMatch(self, f: str, file_dict1: dict, file_dict2: dict, secondInfo, crc_mode: str) -> bool:
        if crc_mode == "all":
            if file_dict1["crc"] == file_dict2["crc"]:
                return True
            else:
                return False
        if file_dict1["size"] == file_dict2["size"]:
            if file_dict1["mtime"] == file_dict2["mtime"]:
                if crc_mode == "match" and self.scanCrc(f) != secondInfo.scanCrc(f):
                    return False
                return True
            else:
                diff = abs(int(file_dict1["mtime"]) - int(file_dict2["mtime"]))
                if diff <= 1 or diff == 3600:
                    if crc_mode == "match" and self.scanCrc(f) != secondInfo.scanCrc(f):
                        return False
                    return True
                else:
                    return False

    def dirCompare(self, secondInfo, moves: bool = False, filter_list = False) -> tuple:
        file_list = list(self.file_dicts)
        second_dict = secondInfo.getDirDict()
        second_list = list(second_dict)
        if self.crc_mode == secondInfo.crc_mode:
            crc_mode = self.crc_mode
        else:
            # this shouldn't happen, but "match" is safe if crc_modes differ
            crc_mode = "match"
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
                    # should empty dirs be moved?
                    # if "dir" not in self.file_dicts[f1] and "dir" not in second_dict[f2]:
                    if self.fileMatch(f, self.file_dicts[f1], second_dict[f2], secondInfo, crc_mode):
                        moved.append({"source": f1, "dest": f2})
            for pair in moved:
                selfOnly.remove(pair["source"])
                secondOnly.remove(pair["dest"])
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
        # copy norun value to survive load
        norun = self.config.norun
        # load config
        if self.config.load:
            self.loadJson()
        # set norun = True iff flag was set, no other args survive a load
        if norun:
            self.config.norun = norun
        # check source & dest
        if not os.path.isdir(self.config.source):
            print(colourString("Invalid source directory: " + self.config.source, "FAIL"))
            sys.exit()
        if self.config.dest == None:
            print(colourString("Destination directory not provided or config failed to load", "FAIL"))
            sys.exit()
        self.config.source = os.path.abspath(self.config.source)
        self.config.dest = os.path.abspath(self.config.dest)
        # save config
        if self.config.save:
            self.saveJson()
        # debugging/testing
        self.log.append(["CONFIG", str(vars(self.config))])
        if self.config.backup_time_override:
            self.backup_time = self.config.backup_time_override

    ### Saving/loading/logging/printing methods ###

    def saveJson(self):
        self.config.save, self.config.load = False, False
        writeJson(os.path.join(self.config.source, self.config.config_dir, "config.json"), vars(self.config))
        print(colourString("Config saved", "OKGREEN"))
        sys.exit()

    def loadJson(self):
        current_source = self.config.source
        config_dir = os.path.abspath(os.path.join(self.config.source, self.config.config_dir, "config.json"))
        config = readJson(config_dir)
        print(colourString("Loaded config from:\n" + config_dir, "OKGREEN"))
        self.config = ConfigObject(config)
        if os.path.abspath(current_source) != os.path.abspath(self.config.source):
            print(colourString("The specified source does not match the loaded config file, exiting", "FAIL"))
            sys.exit()

    def writeLog(self):
        if self.config.csv:
            writeCsv(os.path.join(self.config.source, self.config.config_dir, "log-" + self.backup_time + ".csv"), self.log)

    def colourPrint(self, msg, colour):
        if self.config.verbose:
            print(colourString(msg, colour))

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
            self.printFileInfo("  Dest: ", f, d2)

    def printMovedFiles(self, l: list, d1: dict, d2: dict):
        for f in l:
            self.printFileInfo("Source: ", f["source"], d1)
            self.printFileInfo("  Dest: ", f["dest"], d2)

    ### File operation methods (only use these methods to perform operations) ###

    def removeFile(self, root: str, fPath: str):
        try:
            self.log.append(["removeFile()", root, fPath])
            if not self.config.norun:
                path = os.path.join(root, fPath)
                if os.path.isdir(path):
                    os.rmdir(path)
                else:
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
                source = os.path.join(source_root, source_file)
                dest = os.path.join(dest_root, dest_file)
                if os.path.isdir(source):
                    os.makedirs(dest)
                else:
                    if not os.path.isdir(os.path.dirname(dest)):
                        os.makedirs(os.path.dirname(dest))
                    shutil.copy2(source, dest)
        except Exception as e:
            self.log.append(["COPY ERROR", str(e)])
            print(e)

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

    ### Batch file operation methods (do not perform file operations directly) ###

    def removeFiles(self, root: str, files: list):
        self.colourPrint("Removing unique files from:\n%s" %(root), "OKBLUE")
        for f in files:
            self.removeFile(root, f)

    def copyFiles(self, source_root: str, dest_root: str, source_files: str, dest_files: str):
        self.colourPrint("Copying unique files from:\n%s\nto:\n%s" %(source_root, dest_root), "OKBLUE")
        copy_status = CopyStatus(len(source_files), self.config.verbose)
        for i in range(len(source_files)):
            copy_status.update(source_files[i])
            self.copyFile(source_root, dest_root, source_files[i], dest_files[i])
        copy_status.endProgress()

    def moveFiles(self, source_root: str, dest_root: str, source_files: str, dest_files: str):
        self.colourPrint("Archiving unique files from:\n%s" %(source_root), "OKBLUE")
        for i in range(len(source_files)):
            self.moveFile(source_root, dest_root, source_files[i], dest_files[i])

    def movedFiles(self, moved: list, reverse: bool = False):
        # conflicts shouldn't happen since moved is a subset of files from sourceOnly and destOnly
        # depends on source_info.dirCompare(dest_info) otherwise source and dest will be reversed
        self.colourPrint("Moving files on destination to match source", "OKBLUE")
        for f in moved:
            if reverse:
                dest = self.config.source
                oldLoc = f["source"]
                newLoc = f["dest"]
            else:
                dest = self.config.dest
                oldLoc = f["dest"]
                newLoc = f["source"]
            self.moveFile(dest, dest, oldLoc, newLoc)

    def archiveFile(self, root_path: str, file_path: str):
        if not self.config.noarchive:
            archive_path = os.path.join(self.config.archive_dir, self.backup_time, file_path)
            self.moveFile(root_path, root_path, file_path, archive_path)

    def handleConflicts(self, source, dest, source_dict, dest_dict, changed):
        self.colourPrint("Handling file conflicts", "OKBLUE")
        copy_status = CopyStatus(len(changed), self.config.verbose)
        for fp in changed:
            copy_status.update(fp)
            if self.config.c == "source":
                self.archiveFile(dest, fp)
                self.copyFile(source, dest, fp, fp)
            elif self.config.c == "dest":
                self.archiveFile(source, fp)
                self.copyFile(dest, source, fp, fp)
            elif self.config.c == "new":
                if source_dict[fp]["mtime"] > dest_dict[fp]["mtime"]:
                    self.archiveFile(dest, fp)
                    self.copyFile(source, dest, fp, fp)
                else:
                    self.archiveFile(source, fp)
                    self.copyFile(dest, source, fp, fp)
            else:
                break
        copy_status.endProgress()

    ### Main backup/mirror/sync method ###

    def backup(self):
        if self.config.norun:
            print(colourString("Simulation Run", "HEADER"))
        # scan directories
        source = DirInfo(self.config.source, self.config.r, self.config.config_dir, [self.config.archive_dir])
        dest = DirInfo(self.config.dest, self.config.r, self.config.config_dir, [self.config.archive_dir])
        if self.config.load_json:
            source.loadJson()
            dest.loadJson()
        source.scan()
        source_dict = source.getDirDict()
        dest.scan()
        dest_dict = dest.getDirDict()
        dest_diffs = dest.getLoadedDiffs()
        if self.config.m != "sync" and len(dest_diffs) >= 1:
            self.log.append(["CHANGES ON DESTINATION SINCE LAST SCAN"])
            self.log += dest_diffs
            print(colourString("Some files in the destination folder have changed since the last scan, this may include files from the previous backup, see log for details", "WARNING"))
            self.writeLog()
        sourceOnly, destOnly, changed, moved = source.dirCompare(dest, self.config.d)
        if self.config.save_json:
            source.saveJson()
            dest.saveJson()
        # print differences
        print(colourString("Source Only: %s" %(len(sourceOnly)), "HEADER"))
        self.log.append("Source Only")
        self.printFiles(sourceOnly, source_dict)
        print(colourString("Destination Only: %s" %(len(destOnly)), "HEADER"))
        self.log.append("Destination Only")
        self.printFiles(destOnly, dest_dict)
        print(colourString("File Conflicts: %s" %(len(changed)), "HEADER"))
        self.log.append("File Conflicts")
        self.printChangedFiles(changed, source_dict, dest_dict)
        if self.config.d:
            print(colourString("Moved Files: %s" %(len(moved)), "HEADER"))
            self.log.append("Moved Files")
            self.printMovedFiles(moved, source_dict, dest_dict)
        # wait for go ahead
        if not self.config.goahead:
            simulation = ""
            if self.config.norun:
                simulation = "simulated "
            if len(sourceOnly) == 0 and len(destOnly) == 0 and len(changed) == 0 and len(moved) == 0:
                print(colourString("Directories already match, completed!", "OKGREEN"))
                self.log.append(["No changes found"])
                self.writeLog()
                return 0
            print(colourString("Scan complete, continue with %s%s (y/N)?" %(simulation, self.config.m), "OKGREEN"))
            go = input("> ")
            if go[0].lower() != "y":
                self.log.append("Aborted")
                self.writeLog()
                print(colourString("Run aborted", "WARNING"))
                return 1
        # Backup operations
        self.log.append("Start " + self.config.m)
        print(colourString("Starting " + self.config.m, "OKGREEN"))
        if self.config.m == "mirror":
            self.copyFiles(self.config.source, self.config.dest, sourceOnly, sourceOnly)
            if self.config.noarchive:
                self.removeFiles(self.config.dest, destOnly)
            else:
                recycle_bin = os.path.join(self.config.dest, self.config.archive_dir, "Deleted", self.backup_time)
                self.moveFiles(self.config.dest, recycle_bin, destOnly, destOnly)
            if self.config.d:
                self.movedFiles(moved)
            self.handleConflicts(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        elif self.config.m == "backup":
            self.copyFiles(self.config.source, self.config.dest, sourceOnly, sourceOnly)
            if self.config.d:
                self.movedFiles(moved)
            self.handleConflicts(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        elif self.config.m == "sync":
            self.copyFiles(self.config.source, self.config.dest, sourceOnly, sourceOnly)
            self.copyFiles(self.config.dest, self.config.source, destOnly, destOnly)
            if self.config.d:
                self.movedFiles(moved)
            self.handleConflicts(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        self.log.append("Completed")
        self.writeLog()
        print(colourString("Completed!", "OKGREEN"))


def main():
    parser = argparse.ArgumentParser(description="BackuPy: A small python program for backing up directories with an emphasis on clear rules, simple usage and logging changes", formatter_class=ArgparseCustomFormatter)
    parser.add_argument("source", action="store", type=str,
                        help="Path of source")
    parser.add_argument("dest", action="store", type=str, nargs="?", default=None,
                        help="Path of destination")
    parser.add_argument("-m", type=str.lower, default="mirror", metavar="mode", choices=["mirror", "backup", "sync"],
                        help="F!\n"
                             "Backup mode:\n"
                             "How to handle files that exist only on one side?\n"
                             "  MIRROR (default)\n"
                             "    [source-only -> destination, delete destination-only]\n"
                             "  BACKUP\n"
                             "    [source-only -> destination, keep destination-only]\n"
                             "  SYNC\n"
                             "    [source-only -> destination, destination-only -> source]")
    parser.add_argument("-c", type=str.lower, default="source", metavar="mode", choices=["source", "dest", "new", "no"],
                        help="F!\n"
                             "Conflict resolution mode:\n"
                             "How to handle files that exist on both sides but differ?\n"
                             "  SOURCE (default)\n"
                             "    [copy source to destination]\n"
                             "  DEST\n"
                             "    [copy destination to source]\n"
                             "  NEW\n"
                             "    [copy newer to opposite side]\n"
                             "  NO\n"
                             "    [do nothing]")
    parser.add_argument("-r", type=str.lower, default="none", metavar="mode", choices=["none", "match", "all"],
                        help="F!\n"
                             "CRC mode:\n"
                             "How to compare files that exist on both sides?\n"
                             "  NONE (default)\n"
                             "    [only compare file size and time, fastest]\n"
                             "  MATCH\n"
                             "    [only compare CRC for files with matching size and time]\n"
                             "  ALL\n"
                             "    [compare CRC first for all files, slowest]")
    parser.add_argument("-d", action="store_true",
                        help="Try and detect moved files")
    parser.add_argument("--noarchive", action="store_true",
                        help="Disable archiving, by default files are moved to /.backupy/yymmdd-HHMM/ on their respective side before being removed or overwritten")
    parser.add_argument("--suppress", action="store_true",
                        help="Suppress logging; by default logs are written to source/.backupy/log-yymmdd-HHMM.csv and /.backupy/dirinfo.json")
    parser.add_argument("--goahead", action="store_true",
                        help="Go ahead without prompting for confirmation")
    parser.add_argument("-n", "--norun", action="store_true",
                        help="Simulate the run according to your configuration")
    parser.add_argument("-s", "--save", action="store_true",
                        help="Save configuration in source")
    parser.add_argument("-l", "--load", action="store_true",
                        help="Load configuration from source")
    args = parser.parse_args()
    backup_manager = BackupManager(args)
    backup_manager.backup()


if __name__ == "__main__":
    sys.exit(main())


# TODO
# 1. Increase test coverage
# 2. Release gooey build
