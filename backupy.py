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
import unicodedata


#########################
### File IO functions ###
#########################

def writeCsv(fName: str, data: list) -> None:
    if not os.path.isdir(os.path.dirname(fName)):
        os.makedirs(os.path.dirname(fName))
    with open(fName, "w", newline="", encoding="utf-8", errors="backslashreplace") as f:
        writer = csv.writer(f, delimiter=",")
        for row in data:
            writer.writerow(row)

def readJson(fName: str) -> dict:
    if os.path.exists(fName):
        with open(fName, "r", encoding="utf-8", errors="surrogateescape") as json_file:
            data = json.load(json_file)
        return data
    return {}

def writeJson(fName: str, data: dict) -> None:
    if not os.path.isdir(os.path.dirname(fName)):
        os.makedirs(os.path.dirname(fName))
    with open(fName, "w", encoding="utf-8", errors="surrogateescape") as json_file:
        json.dump(data, json_file, indent=1, separators=(',', ': '))


######################################################
### Classes for helping the command line interface ###
######################################################


class ArgparseCustomFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text[:2] == 'F!':
            return text.splitlines()[1:]
        return argparse.HelpFormatter._split_lines(self, text, width)


class StatusBar:
    def __init__(self, total: int, verbose: bool, progress_bar: bool = False):
        self.verbose = verbose
        self.progress_bar = progress_bar
        terminal_width = shutil.get_terminal_size()[0]
        if terminal_width < 16:
            self.verbose = False
        elif total < 0:
            self.progress_bar = False
        if self.verbose:
            if self.progress_bar:
                self.bar_len = min(68, terminal_width - 15)
                self.progress_scaled = 0
                self.progress = 0
                self.total = total # note self.total is an int when progress_bar is true
                sys.stdout.write("Copying: [" + "-"*self.bar_len + "]\b" + "\b"*self.bar_len)
                sys.stdout.flush()
            else:
                self.char_display = terminal_width - 2
                self.progress = 0
                self.total = str(total) # note self.total is a str when progress_bar is false
                if self.total == "-1":
                    self.title = "Scanning file "
                    progress_str = str(self.progress) + ": "
                    self.msg_len = self.char_display - len(progress_str) - len(self.title)
                else:
                    self.digits = str(len(self.total))
                    self.title = "Copying file "
                    progress_str = str("{:>" + self.digits + "}").format(self.progress) + "/" + self.total + ": "
                    self.msg_len = self.char_display - len(progress_str) - len(self.title)
                msg = " " * self.msg_len
                print(self.title + progress_str + msg, end="\r")

    def getStringMaxWidth(self, string: str) -> int:
        width = 0
        for char in string:
            if unicodedata.east_asian_width(char) in ["W", "F", "A"]:
                width += 2
            else:
                width += 1
        return width

    def update(self, msg:str) -> None:
        if self.verbose:
            if self.progress_bar:
                self.progress += 1
                bar_progression = int(self.bar_len * self.progress // self.total) - self.progress_scaled
                self.progress_scaled += bar_progression
                sys.stdout.write("#" * bar_progression)
                sys.stdout.flush()
            else:
                self.progress += 1
                if self.total == "-1":
                    progress_str = str(self.progress) + ": "
                    self.msg_len = self.char_display - len(progress_str) - len(self.title)
                else:
                    progress_str = str("{:>" + self.digits + "}").format(self.progress) + "/" + self.total + ": "
                while self.getStringMaxWidth(msg) > self.msg_len:
                    splice = (len(msg) - 4) // 2
                    msg = msg[:splice] + "..." + msg[-splice:]
                msg = msg + " " * int(self.msg_len - self.getStringMaxWidth(msg))
                print(self.title + progress_str + msg, end="\r")

    def endProgress(self) -> None:
        if self.verbose:
            if self.progress_bar:
                sys.stdout.write("#" * (self.bar_len - self.progress_scaled) + "]\n")
                sys.stdout.flush()
            else:
                if self.total == "-1":
                    title = "Scanning completed!"
                # elif self.total == "0":
                #     title = "No action necessary"
                else:
                    title = "File operations completed!"
                print(title + " " * (self.char_display - len(title)))


###########################
### Config helper class ###
###########################


class ConfigObject:
    def __init__(self, config: dict):
        # default config (from argparse)
        self.source = None
        self.dest = None
        self.main_mode = "mirror"
        self.select_mode = "source"
        self.compare_mode = "attr"
        self.nomoves = False
        self.noarchive = False
        self.nolog = False
        self.noprompt = False
        self.norun = False
        self.save = False
        self.load = False
        # default config (additional)
        self.archive_dir = ".backupy"
        self.config_dir = ".backupy"
        self.cleanup = True
        self.filter_list = False
        self.filter_list_example = r"[re.compile(x) for x in [r'.+', r'^[a-z]+$', r'^\d+$']]"
        self.backup_time_override = False
        self.csv = True
        self.load_json = True
        self.save_json = True
        self.verbose = True
        # load config
        for key in config:
            self.__setattr__(key, config[key])
        # disable logging of files and changes
        if self.nolog:
            self.csv, self.save_json = False, False


########################################
### Directory scanning and comparing ###
########################################


class DirInfo:
    def __init__(self, directory: str, compare_mode: str,  config_dir: str, ignored_folders: list = []):
        self.file_dicts = {}
        self.loaded_dicts = {}
        self.loaded_diffs = {}
        self.missing_files = {}
        self.dir = directory
        self.compare_mode = compare_mode
        self.config_dir = config_dir
        self.ignored_folders = ignored_folders[:]

    def getDirDict(self) -> dict:
        return self.file_dicts

    def getLoadedDiffs(self) -> dict:
        return self.loaded_diffs

    def getMissingFiles(self) -> dict:
        return self.missing_files

    def saveJson(self) -> None:
        writeJson(os.path.join(self.dir, self.config_dir, "database.json"), self.file_dicts)

    def loadJson(self) -> None:
        self.loaded_dicts = readJson(os.path.join(self.dir, self.config_dir, "database.json"))

    def updateDictCopy(self, source_root: str, dest_root: str, source_file: str, dest_file: str, secondInfo: 'DirInfo') -> None:
        if self.dir == source_root and secondInfo.dir == dest_root:
            secondInfo.file_dicts[dest_file] = self.file_dicts[source_file]
        elif self.dir == dest_root and secondInfo.dir == source_root:
            self.file_dicts[dest_file] = secondInfo.file_dicts[source_file]
        else:
            raise Exception("Update Dict Error")

    def updateDictMove(self, source_root: str, dest_root: str, source_file: str, dest_file: str, secondInfo: 'DirInfo') -> None:
        if source_root == dest_root == self.dir:
            self.file_dicts[dest_file] = self.file_dicts.pop(source_file)
        elif source_root == dest_root == secondInfo.dir:
            secondInfo.file_dicts[dest_file] = secondInfo.file_dicts.pop(source_file)
        elif source_root == self.dir and dest_root != secondInfo.dir:
            _ = self.file_dicts.pop(source_file)
        elif source_root == secondInfo.dir and dest_root != self.dir:
            _ = secondInfo.file_dicts.pop(source_file)
        else:
            raise Exception("Update Dict Error")

    def updateDictRemove(self, root: str, fPath: str, secondInfo: 'DirInfo') -> None:
        if root == self.dir:
            _ = self.file_dicts.pop(fPath)
        elif root == secondInfo.dir:
            _ = secondInfo.file_dicts.pop(fPath)
        else:
            raise Exception("Update Dict Error")

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

    def timeMatch(self, t1: float, t2: float, exact_only: bool = False) -> bool:
        if t1 == t2:
            return True
        elif exact_only:
            return False
        diff = abs(int(t1) - int(t2))
        if diff <= 1 or diff == 3600:
            return True
        else:
            return False

    def scanDir(self, verbose: bool) -> None:
        if os.path.isdir(self.dir):
            self.file_dicts = {}
            scan_status = StatusBar(-1, verbose)
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
                    scan_status.update(relativePath)
                    size = os.path.getsize(full_path)
                    mtime = os.path.getmtime(full_path)
                    if relativePath in self.loaded_dicts:
                        if self.loaded_dicts[relativePath]["size"] == size and self.timeMatch(self.loaded_dicts[relativePath]["mtime"], mtime, True):
                            self.file_dicts[relativePath] = self.loaded_dicts[relativePath]
                        else:
                            self.file_dicts[relativePath] = {"size": size, "mtime": mtime}
                            self.loaded_diffs[relativePath] = self.loaded_dicts[relativePath]
                        if self.compare_mode == "crc" and "crc" not in self.file_dicts[relativePath]:
                            self.file_dicts[relativePath]["crc"] = self.crc(full_path)
                    else:
                        self.file_dicts[relativePath] = {"size": size, "mtime": mtime}
                        self.loaded_diffs[relativePath] = {"size": 0, "mtime": 0}
                        if self.compare_mode == "crc":
                            self.file_dicts[relativePath]["crc"] = self.crc(full_path)
            scan_status.endProgress()
            for relativePath in self.loaded_dicts:
                if relativePath not in self.file_dicts:
                    self.missing_files[relativePath] = self.loaded_dicts[relativePath]

    def fileMatch(self, f: str, file_dict1: dict, file_dict2: dict, secondInfo: 'DirInfo', compare_mode: str) -> bool:
        if compare_mode == "crc":
            if file_dict1["crc"] == file_dict2["crc"]:
                return True
            else:
                return False
        if file_dict1["size"] == file_dict2["size"]:
            if self.timeMatch(file_dict1["mtime"], file_dict2["mtime"]):
                if compare_mode == "both" and self.scanCrc(f) != secondInfo.scanCrc(f):
                    return False
                return True
        return False

    def dirCompare(self, secondInfo: 'DirInfo', no_moves: bool = False, filter_list: typing.Union[str, bool] = False) -> tuple:
        file_list = list(self.file_dicts)
        second_dict = secondInfo.getDirDict()
        second_list = list(second_dict)
        if self.compare_mode == secondInfo.compare_mode:
            compare_mode = self.compare_mode
        else:
            # this shouldn't happen, but "both" is safe if compare_modes differ
            compare_mode = "both"
        if type(filter_list) == str:
            filter_list = eval(filter_list)
            if type(filter_list) == list:
                file_list = filter(lambda x: any([True if r.match(x) else False for r in filter_list]), file_list)
                second_list = filter(lambda x: any([True if r.match(x) else False for r in filter_list]), second_list)
        selfOnly = []
        secondOnly = []
        changed = []
        moved = []
        for f in file_list:
            if f in second_list:
                if not self.fileMatch(f, self.file_dicts[f], second_dict[f], secondInfo, compare_mode):
                    changed.append(f)
            else:
                selfOnly.append(f)
        for f in second_list:
            if not f in file_list:
                secondOnly.append(f)
        if not no_moves:
            for f1 in selfOnly:
                for f2 in secondOnly:
                    # should empty dirs be moved?
                    # if "dir" not in self.file_dicts[f1] and "dir" not in second_dict[f2]:
                    if self.fileMatch(f, self.file_dicts[f1], second_dict[f2], secondInfo, compare_mode):
                        moved.append({"source": f1, "dest": f2})
                        _ = secondInfo.missing_files.pop(f1, 1)
                        _ = self.missing_files.pop(f2, 1)
            for pair in moved:
                selfOnly.remove(pair["source"])
                secondOnly.remove(pair["dest"])
        return selfOnly, secondOnly, changed, moved


##################
### Main class ###
##################


class BackupManager:
    def __init__(self, args: typing.Union[argparse.Namespace, dict], gui: bool = False):
        # init logging
        self.log = []
        self.backup_time = datetime.datetime.now().strftime("%y%m%d-%H%M")
        # init gui flag
        self.gui = gui
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
            print(self.colourString("Invalid source directory: " + self.config.source, "FAIL"))
            sys.exit()
        if self.config.dest == None:
            print(self.colourString("Destination directory not provided or config failed to load", "FAIL"))
            sys.exit()
        self.config.source = os.path.abspath(self.config.source)
        self.config.dest = os.path.abspath(self.config.dest)
        # init DirInfo vars
        self.source = None
        self.dest = None
        # save config
        if self.config.save:
            self.saveJson()
        # debugging/testing
        self.log.append(["CONFIG", str(vars(self.config))])
        if self.config.backup_time_override:
            self.backup_time = self.config.backup_time_override

    ######################################
    ### Saving/loading/logging methods ###
    ######################################

    def saveJson(self) -> None:
        self.config.save, self.config.load = False, False
        writeJson(os.path.join(self.config.source, self.config.config_dir, "config.json"), vars(self.config))
        print(self.colourString("Config saved", "OKGREEN"))
        sys.exit()

    def loadJson(self) -> None:
        current_source = self.config.source
        config_dir = os.path.abspath(os.path.join(self.config.source, self.config.config_dir, "config.json"))
        config = readJson(config_dir)
        print(self.colourString("Loaded config from:\n" + config_dir, "OKGREEN"))
        self.config = ConfigObject(config)
        if os.path.abspath(current_source) != os.path.abspath(self.config.source):
            print(self.colourString("The specified source does not match the loaded config file, exiting", "FAIL"))
            sys.exit()

    def writeLog(self, db: bool = False) -> None:
        if self.config.csv:
            writeCsv(os.path.join(self.config.source, self.config.config_dir, "log-" + self.backup_time + ".csv"), self.log)
        if self.config.save_json and db:
            self.source.saveJson()
            self.dest.saveJson()

    ###################################
    ### String manipulation methods ###
    ###################################

    def replaceSurrogates(self, string: str) -> str:
        return string.encode("utf-8", "surrogateescape").decode("utf-8", "replace")

    def colourString(self, string: str, colour: str) -> str:
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
        string = self.replaceSurrogates(string)
        if self.gui:
            return string
        return colours[colour] + string + colours["ENDC"]

    def prettyCrc(self, prev: int) -> str:
        return "%X" %(prev & 0xFFFFFFFF)

    def prettySize(self, size: float) -> str:
        if size > 10**9:
            return "{:<10}".format("%s GB" %(round(size/10**9, 2)))
        elif size > 10**6:
            return "{:<10}".format("%s MB" %(round(size/10**6, 2)))
        elif size > 10**3:
            return "{:<10}".format("%s KB" %(round(size/10**3, 2)))
        else:
            return "{:<10}".format("%s B" %(size))

    ########################
    ### Printing methods ###
    ########################

    def colourPrint(self, msg: str, colour: str) -> None:
        if self.config.verbose:
            if colour == "NONE":
                print(msg)
            else:
                print(self.colourString(msg, colour))

    def printFileInfo(self, header: str, f: str, d: dict, sub_header: str = "", skip_info: bool = False) -> None:
        self.log.append([header, f] + [str(d[f])])
        if header == "":
            s = ""
        else:
            s = self.colourString(header, "OKBLUE") + self.replaceSurrogates(f)
            if not skip_info:
                s = s + "\n"
        if not skip_info:
            s = s + self.colourString(sub_header, "OKBLUE") + "\t"
            s = s + self.colourString(" Size: ", "OKBLUE") + self.prettySize(d[f]["size"])
            s = s + self.colourString(" Modified: ", "OKBLUE") + time.ctime(d[f]["mtime"])
            if "crc" in d[f]:
                s = s + self.colourString(" Hash: ", "OKBLUE") + self.prettyCrc(d[f]["crc"])
        print(s)

    def printFiles(self, l: list, d: dict) -> None:
        for f in l:
            self.printFileInfo("File: ", f, d)

    def printChangedFiles(self, l: list, d1: dict, d2: dict) -> None:
        for f in l:
            self.printFileInfo("File: ", f, d1, " Source")
            self.printFileInfo("", f, d2, "   Dest")

    def printMovedFiles(self, l: list, d1: dict, d2: dict) -> None:
        for f in l:
            self.printFileInfo("Source: ", f["source"], d1, skip_info=True)
            self.printFileInfo("  Dest: ", f["dest"], d2)

    def printDbConflicts(self, l: list, d: dict, ddb: dict) -> None:
        for f in l:
            self.printFileInfo("File: ", f, d, "   Dest")
            self.printFileInfo("", f, ddb, "     DB")

    def printSyncDbConflicts(self, l: list, d1: dict, d2: dict, d1db: dict, d2db: dict) -> None:
        for f in l:
            self.printFileInfo("File: ", f, d1, " Source")
            self.printFileInfo("", f, d1db, "     DB")
            self.printFileInfo("", f, d2, "   Dest")
            self.printFileInfo("", f, d2db, "     DB")

    #############################################################################
    ### File operation methods (only use these methods to perform operations) ###
    #############################################################################

    def removeFile(self, root: str, fPath: str) -> None:
        try:
            self.log.append(["removeFile()", root, fPath])
            self.source.updateDictRemove(root, fPath, self.dest)
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
            self.log.append(["REMOVE ERROR", str(e), str(locals())])
            print(e)

    def copyFile(self, source_root: str, dest_root: str, source_file: str, dest_file: str) -> None:
        try:
            self.log.append(["copyFile()", source_root, dest_root, source_file, dest_file])
            self.source.updateDictCopy(source_root, dest_root, source_file, dest_file, self.dest)
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
            self.log.append(["COPY ERROR", str(e), str(locals())])
            print(e)

    def moveFile(self, source_root: str, dest_root: str, source_file: str, dest_file: str) -> None:
        try:
            self.log.append(["moveFile()", source_root, dest_root, source_file, dest_file])
            self.source.updateDictMove(source_root, dest_root, source_file, dest_file, self.dest)
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
            self.log.append(["MOVE ERROR", str(e), str(locals())])
            print(e)

    ##############################################################################
    ### Batch file operation methods (do not perform file operations directly) ###
    ##############################################################################

    def removeFiles(self, root: str, files: list) -> None:
        self.colourPrint("Removing %s unique files from:\n%s" %(len(files), root), "OKBLUE")
        for f in files:
            self.removeFile(root, f)
        self.colourPrint("Removal completed!", "NONE")

    def copyFiles(self, source_root: str, dest_root: str, source_files: str, dest_files: str) -> None:
        self.colourPrint("Copying %s unique files from:\n%s\nto:\n%s" %(len(source_files), source_root, dest_root), "OKBLUE")
        copy_status = StatusBar(len(source_files), self.config.verbose)
        for i in range(len(source_files)):
            copy_status.update(source_files[i])
            self.copyFile(source_root, dest_root, source_files[i], dest_files[i])
        copy_status.endProgress()

    def moveFiles(self, source_root: str, dest_root: str, source_files: str, dest_files: str) -> None:
        self.colourPrint("Archiving %s unique files from:\n%s" %(len(source_files), source_root), "OKBLUE")
        for i in range(len(source_files)):
            self.moveFile(source_root, dest_root, source_files[i], dest_files[i])
        self.colourPrint("Archiving completed!", "NONE")

    def movedFiles(self, moved: list, reverse: bool = False) -> None:
        # conflicts shouldn't happen since moved is a subset of files from sourceOnly and destOnly
        # depends on source_info.dirCompare(dest_info) otherwise source and dest keys will be reversed
        self.colourPrint("Moving %s files on destination to match source" %(len(moved)), "OKBLUE")
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
        self.colourPrint("Moving completed!", "NONE")

    def archiveFile(self, root_path: str, file_path: str) -> None:
        if not self.config.noarchive:
            archive_path = os.path.join(self.config.archive_dir, self.backup_time, file_path)
            self.moveFile(root_path, root_path, file_path, archive_path)

    def handleChanges(self, source: str, dest: str, source_dict: dict, dest_dict:dict, changed: list) -> None:
        self.colourPrint("Handling %s file changes per selection mode" %(len(changed)), "OKBLUE")
        copy_status = StatusBar(len(changed), self.config.verbose)
        for fp in changed:
            copy_status.update(fp)
            if self.config.select_mode == "source":
                self.archiveFile(dest, fp)
                self.copyFile(source, dest, fp, fp)
            elif self.config.select_mode == "dest":
                self.archiveFile(source, fp)
                self.copyFile(dest, source, fp, fp)
            elif self.config.select_mode == "new":
                if source_dict[fp]["mtime"] > dest_dict[fp]["mtime"]:
                    self.archiveFile(dest, fp)
                    self.copyFile(source, dest, fp, fp)
                else:
                    self.archiveFile(source, fp)
                    self.copyFile(dest, source, fp, fp)
            else:
                break
        copy_status.endProgress()

    ######################################
    ### Main backup/mirror/sync method ###
    ######################################

    def backup(self):
        if self.config.norun:
            print(self.colourString("Dry Run", "HEADER"))
        # init dir scanning and load previous scan data if available
        self.source = DirInfo(self.config.source, self.config.compare_mode, self.config.config_dir, [self.config.archive_dir])
        self.dest = DirInfo(self.config.dest, self.config.compare_mode, self.config.config_dir, [self.config.archive_dir])
        database_load_success = False
        if self.config.load_json:
            self.source.loadJson()
            self.dest.loadJson()
            if self.source.loaded_dicts != {} or self.dest.loaded_dicts != {}:
                database_load_success = True
        # scan directories, this is where CRC mode = all takes place
        self.colourPrint("Scanning files on source:\n%s" %(self.config.source), "OKBLUE")
        self.source.scanDir(self.config.verbose)
        source_dict = self.source.getDirDict()
        source_diffs = self.source.getLoadedDiffs()
        self.colourPrint("Scanning files on destination:\n%s" %(self.config.dest), "OKBLUE")
        self.dest.scanDir(self.config.verbose)
        dest_dict = self.dest.getDirDict()
        dest_diffs = self.dest.getLoadedDiffs()
        # compare directories, this is where CRC mode = both takes place
        self.colourPrint("Comparing directories...", "OKGREEN")
        sourceOnly, destOnly, changed, moved = self.source.dirCompare(self.dest, self.config.nomoves, self.config.filter_list)
        # print database conflicts, note: this is intended to prevent collisions from files being modified independently on both sides and does not detect deletions, it can also be triggered by time zone or dst changes
        if database_load_success:
            self.log.append(["### DATABASE CONFLICTS ###"])
            if self.config.main_mode == "sync":
                sync_conflicts = []
                for f in source_diffs:
                    if f in dest_diffs:
                        sync_conflicts.append(f)
                if len(sync_conflicts) >= 1:
                    print(self.colourString("WARNING: found files modified in both source and destination since last scan", "WARNING"))
                print(self.colourString("Sync Database Conflicts: %s" %(len(sync_conflicts)), "HEADER"))
                self.printSyncDbConflicts(sync_conflicts, source_dict, dest_dict, source_diffs, dest_diffs)
            else:
                if len(dest_diffs) >= 1:
                    print(self.colourString("WARNING: found files modified in the destination since last scan", "WARNING"))
                print(self.colourString("Destination Database Conflicts: %s" %(len(dest_diffs)), "HEADER"))
                self.printDbConflicts(list(dest_diffs.keys()), dest_dict, dest_diffs)
        # prepare diff messages
        if self.config.noarchive:
            archive_msg = "delete"
        else:
            archive_msg = "archive"
        if self.config.main_mode == "sync":
            dest_msg = "(copy to source)"
        elif self.config.main_mode == "backup":
            dest_msg = "(left as is)"
        elif self.config.main_mode == "mirror":
            dest_msg = "(to be " + archive_msg + "d)"
        if self.config.select_mode == "source":
            change_msg = "(" + archive_msg + " dest and copy from source)"
        elif self.config.select_mode == "dest":
            change_msg = "(" + archive_msg + " source and copy from dest)"
        elif self.config.select_mode == "new":
            change_msg = "(" + archive_msg + " older and copy newer)"
        elif self.config.select_mode == "no":
            change_msg = "(left as is)"
        # print differences
        print(self.colourString("Source Only (copy to dest): %s" %(len(sourceOnly)), "HEADER"))
        self.log.append(["### SOURCE ONLY ###"])
        self.printFiles(sourceOnly, source_dict)
        print(self.colourString("Destination Only %s: %s" %(dest_msg, len(destOnly)), "HEADER"))
        self.log.append(["### DESTINATION ONLY ###"])
        self.printFiles(destOnly, dest_dict)
        print(self.colourString("File Changes %s: %s" %(change_msg, len(changed)), "HEADER"))
        self.log.append(["### FILE CHANGES ###"])
        self.printChangedFiles(changed, source_dict, dest_dict)
        if not self.config.nomoves:
            print(self.colourString("Moved Files (move on dest to match source): %s" %(len(moved)), "HEADER"))
            self.log.append(["### MOVED FILES ###"])
            self.printMovedFiles(moved, source_dict, dest_dict)
        # wait for go ahead
        if not self.config.noprompt:
            simulation = ""
            if self.config.norun:
                simulation = " dry run"
            if len(sourceOnly) == 0 and len(destOnly) == 0 and len(changed) == 0 and len(moved) == 0:
                print(self.colourString("Directories already match, completed!", "OKGREEN"))
                self.log.append(["### NO CHANGES FOUND ###"])
                self.writeLog(db=True)
                return 0
            print(self.colourString("Scan complete, continue with %s%s (y/N)?" %(self.config.main_mode, simulation), "OKGREEN"))
            self.writeLog() # for inspection before decision if necessary
            go = input("> ")
            if go[0].lower() != "y":
                self.log.append(["### ABORTED ###"])
                self.writeLog()
                print(self.colourString("Run aborted", "WARNING"))
                return 1
        # backup operations
        if self.config.norun:
            self.log.append(["### START " + self.config.main_mode.upper() + " DRY RUN ###"])
        else:
            self.log.append(["### START " + self.config.main_mode.upper() + " ###"])
        print(self.colourString("Starting " + self.config.main_mode, "OKGREEN"))
        if self.config.main_mode == "mirror":
            self.copyFiles(self.config.source, self.config.dest, sourceOnly, sourceOnly)
            if self.config.noarchive:
                self.removeFiles(self.config.dest, destOnly)
            else:
                recycle_bin = os.path.join(self.config.dest, self.config.archive_dir, "Deleted", self.backup_time)
                self.moveFiles(self.config.dest, recycle_bin, destOnly, destOnly)
            if not self.config.nomoves:
                self.movedFiles(moved)
            self.handleChanges(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        elif self.config.main_mode == "backup":
            self.copyFiles(self.config.source, self.config.dest, sourceOnly, sourceOnly)
            if not self.config.nomoves:
                self.movedFiles(moved)
            self.handleChanges(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        elif self.config.main_mode == "sync":
            self.copyFiles(self.config.source, self.config.dest, sourceOnly, sourceOnly)
            self.copyFiles(self.config.dest, self.config.source, destOnly, destOnly)
            if not self.config.nomoves:
                self.movedFiles(moved)
            self.handleChanges(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        self.log.append(["### COMPLETED ###"])
        self.writeLog(db=True)
        print(self.colourString("Completed!", "OKGREEN"))


def main():
    parser = argparse.ArgumentParser(description="BackuPy: A small python program for backing up directories with an emphasis on clear rules, simple usage and logging changes", formatter_class=ArgparseCustomFormatter)
    parser.add_argument("source", action="store", type=str,
                        help="Path of source")
    parser.add_argument("dest", action="store", type=str, nargs="?", default=None,
                        help="Path of destination")
    parser.add_argument("-m", type=str.lower, dest="main_mode", default="mirror", metavar="mode", choices=["mirror", "backup", "sync"],
                        help="F!\n"
                             "Main mode:\n"
                             "How to handle files that exist only on one side?\n"
                             "  MIRROR (default)\n"
                             "    [source-only -> destination, delete destination-only]\n"
                             "  BACKUP\n"
                             "    [source-only -> destination, keep destination-only]\n"
                             "  SYNC\n"
                             "    [source-only -> destination, destination-only -> source]")
    parser.add_argument("-s", type=str.lower, dest="select_mode", default="source", metavar="mode", choices=["source", "dest", "new", "no"],
                        help="F!\n"
                             "Selection mode:\n"
                             "How to handle files that exist on both sides but differ?\n"
                             "  SOURCE (default)\n"
                             "    [copy source to destination]\n"
                             "  DEST\n"
                             "    [copy destination to source]\n"
                             "  NEW\n"
                             "    [copy newer to opposite side]\n"
                             "  NO\n"
                             "    [do nothing]")
    parser.add_argument("-c", type=str.lower, dest="compare_mode", default="attr", metavar="mode", choices=["attr", "both", "crc"],
                        help="F!\n"
                             "Compare mode:\n"
                             "How to detect files that exist on both sides but differ?\n"
                             "  ATTR (default)\n"
                             "    [compare file attributes: mod-time and size]\n"
                             "  BOTH\n"
                             "    [compare file attributes first, then check CRC]\n"
                             "  CRC\n"
                             "    [compare CRC only, ignoring file attributes]")
    parser.add_argument("--nomoves", action="store_true",
                        help="Do not detect moved or renamed files")
    parser.add_argument("--noarchive", action="store_true",
                        help="F!\n"
                             "Disable archiving files before deleting/overwriting to:\n"
                             "  <source|dest>/.backupy/yymmdd-HHMM/\n")
    parser.add_argument("--nolog", action="store_true",
                        help="F!\n"
                             "Disable writing to:\n"
                             "  <source>/.backupy/log-yymmdd-HHMM.csv\n"
                             "  <source|dest>/.backupy/database.json")
    parser.add_argument("--noprompt", action="store_true",
                        help="Complete run without prompting for confirmation")
    parser.add_argument("--norun", action="store_true",
                        help="Perform a dry run according to your configuration")
    parser.add_argument("--save", action="store_true",
                        help="Save configuration in source")
    parser.add_argument("--load", action="store_true",
                        help="Load configuration from source")
    args = parser.parse_args()
    backup_manager = BackupManager(args)
    backup_manager.backup()


if __name__ == "__main__":
    sys.exit(main())
