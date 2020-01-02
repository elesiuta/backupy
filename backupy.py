# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# https://github.com/elesiuta/backupy

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

def getVersion() -> str:
    return "1.0.3"


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

def writeJson(fName: str, data: dict, subdir: bool = True) -> None:
    if subdir and not os.path.isdir(os.path.dirname(fName)):
        os.makedirs(os.path.dirname(fName))
    with open(fName, "w", encoding="utf-8", errors="surrogateescape") as json_file:
        json.dump(data, json_file, indent=1, separators=(',', ': '))

####################
### Localisation ###
####################

def getString(text: str) -> str:
    # import locale
    # logic for localisation goes here, set language with either a global or singleton
    # store strings in a dictionary or use this as an alias for gettext
    return text


######################################################
### Classes for helping the command line interface ###
######################################################


class ArgparseCustomFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text[:2] == 'F!':
            return text.splitlines()[1:]
        return argparse.HelpFormatter._split_lines(self, text, width)


class StatusBar:
    def __init__(self, title: str, total: int, stdout_status_bar: bool, simplified_bar: bool = False, gui: bool = False):
        self.title = title
        self.total = total
        self.stdout_status_bar = stdout_status_bar
        self.simplified_bar = simplified_bar
        self.gui = gui
        terminal_width = shutil.get_terminal_size()[0]
        if terminal_width < 16:
            self.stdout_status_bar = False
        elif total < 0:
            self.simplified_bar = False
        if self.stdout_status_bar:
            if self.simplified_bar:
                self.bar_len = min(68, terminal_width - 15)
                self.progress_scaled = 0
                self.progress = 0
                sys.stdout.write(getString(self.title) + ": [" + "-"*self.bar_len + "]\b" + "\b"*self.bar_len)
                sys.stdout.flush()
            else:
                self.char_display = terminal_width - 2
                self.progress = 0
                if self.total == -1:
                    self.title_str = getString(self.title) + " "
                    progress_str = str(self.progress) + ": "
                    self.msg_len = self.char_display - len(progress_str) - len(self.title_str)
                else:
                    self.digits = str(len(str(self.total)))
                    self.title_str = getString(self.title) + " "
                    progress_str = str("{:>" + self.digits + "}").format(self.progress) + "/" + str(self.total) + ": "
                    self.msg_len = self.char_display - len(progress_str) - len(self.title_str)
                msg = " " * self.msg_len
                print(self.title_str + progress_str + msg, end="\r")
        elif self.gui and total > 0:
            self.progress = 0
            print("progress: %s/%s" %(self.progress, self.total))

    def getStringMaxWidth(self, string: str) -> int:
        width = 0
        for char in string:
            if unicodedata.east_asian_width(char) in ["W", "F", "A"]:
                width += 2
            else:
                width += 1
        return width

    def update(self, msg:str) -> None:
        if self.stdout_status_bar:
            if self.simplified_bar and self.total != 0:
                self.progress += 1
                bar_progression = int(self.bar_len * self.progress // self.total) - self.progress_scaled
                self.progress_scaled += bar_progression
                sys.stdout.write("#" * bar_progression)
                sys.stdout.flush()
            else:
                self.progress += 1
                if self.total == -1:
                    progress_str = str(self.progress) + ": "
                    self.msg_len = self.char_display - len(progress_str) - len(self.title_str)
                else:
                    progress_str = str("{:>" + self.digits + "}").format(self.progress) + "/" + str(self.total) + ": "
                while self.getStringMaxWidth(msg) > self.msg_len:
                    splice = (len(msg) - 4) // 2
                    msg = msg[:splice] + "..." + msg[-splice:]
                msg = msg + " " * int(self.msg_len - self.getStringMaxWidth(msg))
                print(self.title_str + progress_str + msg, end="\r")
        elif self.gui:
            self.progress += 1
            print("progress: %s/%s" %(self.progress, self.total))

    def endProgress(self) -> None:
        if self.stdout_status_bar:
            if self.simplified_bar:
                sys.stdout.write("#" * (self.bar_len - self.progress_scaled) + "]\n")
                sys.stdout.flush()
            else:
                if self.title == "Copying":
                    title_str = getString("File operations completed!")
                else:
                    title_str = getString(self.title + " completed!")
                # if self.total == 0:
                #     title_str = "No action necessary"
                print(title_str + " " * (self.char_display - len(title_str)))
        elif self.gui and self.total > 0:
            self.progress = self.total
            print("progress: %s/%s" %(self.progress, self.total))


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
        self.archive_dir = ".backupy/Archive"
        self.config_dir = ".backupy"
        self.log_dir = ".backupy/Logs"
        self.trash_dir = ".backupy/Trash"
        self.cleanup_empty_dirs = True
        self.filters = None
        self.filters_example0 = r"[r'.+', r'^[a-z]+$', r'^\d+$'] # provide a list of regular expressions, only matching files will be included"
        self.filters_example1 = r"[re.compile(x, 0) for x in [r'.+', r'^[a-z]+$', r'^\d+$']] # specify a flags value"
        self.filters_example2 = {
            "include": r"[re.compile(x) for x in [r'.+', r'^[a-z]+$', r'^\d+$']] # include list is optional, omit to include all",
            "exclude": r"[re.compile(x) for x in [r'.+', r'^[a-z]+$', r'^\d+$']] # exclude list has higher priority, omit to exclude none"
        }
        self.filters_example3 = """{
            "include": r"[re.compile(x) for x in [r'.+', r'^[a-z]+$', r'^\d+$']],
            "exclude": r"[re.compile(x) for x in [r'.+', r'^[a-z]+$', r'^\d+$']]"
        } # you can also encapsulate it in a string for the CLI, newlines not required"""
        self.backup_time_override = False
        self.csv = True
        self.root_alias_log = True
        self.load_json = True
        self.save_json = True
        self.stdout_status_bar = True
        self.verbose = True
        self.quit_on_db_conflict = False
        # load config
        for key in config:
            self.__setattr__(key, config[key])
        # normalize paths (these should be relative, not absolute!)
        self.archive_dir = os.path.normpath(self.archive_dir)
        self.config_dir = os.path.normpath(self.config_dir)
        self.log_dir = os.path.normpath(self.log_dir)
        self.trash_dir = os.path.normpath(self.trash_dir)
        # disable logging of files and changes
        if self.nolog:
            self.csv, self.save_json = False, False


########################################
### Directory scanning and comparing ###
########################################


class DirInfo:
    def __init__(self, directory: str, compare_mode: str,  config_dir: str, ignored_toplevel_folders: list = [], gui: bool = False):
        self.file_dicts = {}
        self.loaded_dicts = {}
        self.loaded_diffs = {}
        self.missing_files = {}
        self.dir = directory
        self.compare_mode = compare_mode
        self.config_dir = config_dir
        self.ignored_toplevel_folders = list(set(ignored_toplevel_folders[:] + [config_dir]))
        self.gui = gui

    def getDirDict(self) -> dict:
        return self.file_dicts

    def getLoadedDicts(self) -> dict:
        return self.loaded_dicts

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

    def pathMatch(self, path: str, path_list: list) -> bool:
        # is path in path_list (or a subdir of one in it)
        if os.path.isabs(path):
            relpath, abspath = os.path.relpath(path, self.dir), path
        else:
            relpath, abspath = path, os.path.join(self.dir, path)
        for p in path_list:
            # p = os.path.normpath(p)
            # if os.path.isabs(p):
            #     if os.path.commonpath([p, abspath]) == p:
            #         return True
            # else:
            if os.path.commonpath([p, relpath]) == p:
                return True
        return False

    def scanDir(self, stdout_status_bar: bool) -> None:
        if os.path.isdir(self.dir):
            self.file_dicts = {}
            total = sum([len(f) for r, d, f in os.walk(self.dir)])
            scan_status = StatusBar("Scanning", total, stdout_status_bar, gui=self.gui)
            for dir_path, subdir_list, file_list in os.walk(self.dir):
                if self.pathMatch(dir_path, self.ignored_toplevel_folders):
                    subdir_list.clear()
                    continue
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
                        if self.compare_mode == "crc":
                            self.file_dicts[relativePath]["crc"] = self.crc(full_path)
            scan_status.endProgress()
            for relativePath in self.loaded_dicts:
                if not self.pathMatch(relativePath, self.ignored_toplevel_folders):
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

    def dirCompare(self, secondInfo: 'DirInfo', no_moves: bool = False, filters: typing.Union[str, list, dict, None] = None) -> tuple:
        # init variables
        file_list = list(self.file_dicts)
        second_dict = secondInfo.getDirDict()
        second_list = list(second_dict)
        selfOnly = []
        secondOnly = []
        changed = []
        moved = []
        if self.compare_mode == secondInfo.compare_mode:
            compare_mode = self.compare_mode
        else:
            # this shouldn't happen, but "both" is safe if compare_modes differ
            compare_mode = "both"
        # apply filters
        filter_list = None
        filter_false_list = None
        if type(filters) == str:
            filters = eval(filters)
        if type(filters) == dict:
            if "inlcude" in filters:
                filter_list = filters["include"]
                if type(filter_list) == str:
                    filter_list = eval(filter_list)
            if "exlucde" in filters:
                filter_false_list = filters["exclude"]
                if type(filter_false_list) == str:
                    filter_false_list = eval(filter_false_list)
        if type(filter_list) == list:
            for i in range(len(filter_list)):
                if type(filter_list[i]) == str:
                    filter_list[i] = re.compile[filter_list[i]]
                if type(filter_list[i]) != re.Pattern:
                    filter_list = None
                    break
        if type(filter_false_list) == list:
            for i in range(len(filter_false_list)):
                if type(filter_false_list[i]) == str:
                    filter_false_list[i] = re.compile[filter_false_list[i]]
                if type(filter_false_list[i]) != re.Pattern:
                    filter_false_list = None
                    break
        if type(filter_list) == list:
            file_list = filter(lambda x: any([True if r.match(x) else False for r in filter_list]), file_list)
            second_list = filter(lambda x: any([True if r.match(x) else False for r in filter_list]), second_list)
        if type(filter_false_list) == list:
            file_list = filter(lambda x: all([False if r.match(x) else True for r in filter_false_list]), file_list)
            second_list = filter(lambda x: all([False if r.match(x) else True for r in filter_false_list]), second_list)
        # compare
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
        # gui imports
        if self.gui:
            from backupy_gui import colourize, simplePrompt
            self.gui_colourize = colourize
            self.gui_simplePrompt = simplePrompt
        # init config
        if type(args) != dict:
            args = vars(args)
        self.config = ConfigObject(args)
        # copy norun value to survive load
        norun = self.config.norun
        # load config (be careful if using a non-default config_dir!)
        if self.config.load:
            self.loadJson()
        # set norun = True iff flag was set, no other args survive a load
        if norun:
            self.config.norun = norun
        # check source & dest
        if not os.path.isdir(self.config.source):
            print(self.colourString(getString("Invalid source directory: ") + self.config.source, "FAIL"))
            sys.exit()
        if self.config.dest is None:
            print(self.colourString(getString("Destination directory not provided or config failed to load"), "FAIL"))
            sys.exit()
        self.config.source = os.path.abspath(self.config.source)
        self.config.dest = os.path.abspath(self.config.dest)
        # init DirInfo vars
        self.source = None
        self.dest = None
        # save config
        if self.config.save:
            self.saveJson()
        # gui modifications
        if self.gui:
            self.config.stdout_status_bar = False
        # debugging/testing
        self.log.append([getString("### SETTINGS ###")])
        if self.config.backup_time_override:
            self.backup_time = self.config.backup_time_override
        self.log.append([getString("Time:"), self.backup_time,
                         getString("Version:"), getVersion(),
                         getString("Config:"), str(vars(self.config))])

    ######################################
    ### Saving/loading/logging methods ###
    ######################################

    def saveJson(self) -> None:
        self.config.save, self.config.load = False, False
        writeJson(os.path.join(self.config.source, self.config.config_dir, "config.json"), vars(self.config))
        print(self.colourString(getString("Config saved"), "OKGREEN"))
        sys.exit()

    def loadJson(self) -> None:
        current_source = self.config.source
        config_dir = os.path.abspath(os.path.join(self.config.source, self.config.config_dir, "config.json"))
        config = readJson(config_dir)
        print(self.colourString(getString("Loaded config from:") + "\n" + config_dir, "OKGREEN"))
        self.config = ConfigObject(config)
        if self.config.source is None or os.path.abspath(current_source) != os.path.abspath(self.config.source):
            print(self.colourString(getString("A config file matching the specified source was not found"), "FAIL"))
            sys.exit()

    def writeLog(self, db: bool = False) -> None:
        if self.config.csv:
            if self.config.root_alias_log:
                for i in range(2, len(self.log)):
                    for j in range(len(self.log[i])):
                        if type(self.log[i][j]) == str:
                            self.log[i][j] = self.log[i][j].replace(self.config.source, getString("<source>"))
                            self.log[i][j] = self.log[i][j].replace(self.config.dest, getString("<dest>"))
            writeCsv(os.path.join(self.config.source, self.config.log_dir, "log-" + self.backup_time + ".csv"), self.log)
        if self.config.save_json and db:
            self.source.saveJson()
            self.dest.saveJson()

    def abortRun(self) -> int:
        self.log.append([getString("### ABORTED ###")])
        self.writeLog()
        print(self.colourString(getString("Run aborted"), "WARNING"))
        return 1

    ###################################
    ### String manipulation methods ###
    ###################################

    def replaceSurrogates(self, string: str) -> str:
        return string.encode("utf-8", "surrogateescape").decode("utf-8", "replace")

    def colourString(self, string: str, colour: str) -> str:
        string = self.replaceSurrogates(string)
        if self.gui:
            return self.gui_colourize(string, colour)
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
        header, sub_header = getString(header), getString(sub_header)
        if f in d:
            self.log.append([header.strip(), sub_header.strip(), f] + [str(d[f])])
            missing = False
        else:
            self.log.append([header.strip(), sub_header.strip(), f] + [getString("Missing")])
            missing = True
        if header == "":
            s = ""
        else:
            s = self.colourString(header, "OKBLUE") + self.replaceSurrogates(f)
            if not skip_info:
                s = s + "\n"
        if not skip_info:
            s = s + self.colourString(sub_header, "OKBLUE") + " "*(8-len(sub_header))
            if not missing:
                s = s + self.colourString(getString(" Size: "), "OKBLUE") + self.prettySize(d[f]["size"])
                s = s + self.colourString(getString(" Modified: "), "OKBLUE") + time.ctime(d[f]["mtime"])
                if "crc" in d[f]:
                    s = s + self.colourString(getString(" Hash: "), "OKBLUE") + self.prettyCrc(d[f]["crc"])
            else:
                s = s + self.colourString(getString(" Missing"), "OKBLUE")
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
                if self.config.cleanup_empty_dirs:
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
                if self.config.cleanup_empty_dirs:
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
        self.colourPrint(getString("Removing %s unique files from:\n%s") %(len(files), root), "OKBLUE")
        for f in files:
            self.removeFile(root, f)
        self.colourPrint(getString("Removal completed!"), "NONE")

    def copyFiles(self, source_root: str, dest_root: str, source_files: str, dest_files: str) -> None:
        self.colourPrint(getString("Copying %s unique files from:\n%s\nto:\n%s") %(len(source_files), source_root, dest_root), "OKBLUE")
        copy_status = StatusBar("Copying", len(source_files), self.config.stdout_status_bar, gui=self.gui)
        for i in range(len(source_files)):
            copy_status.update(source_files[i])
            self.copyFile(source_root, dest_root, source_files[i], dest_files[i])
        copy_status.endProgress()

    def moveFiles(self, source_root: str, dest_root: str, source_files: str, dest_files: str) -> None:
        self.colourPrint(getString("Archiving %s unique files from:\n%s") %(len(source_files), source_root), "OKBLUE")
        for i in range(len(source_files)):
            self.moveFile(source_root, dest_root, source_files[i], dest_files[i])
        self.colourPrint(getString("Archiving completed!"), "NONE")

    def movedFiles(self, moved: list, reverse: bool = False) -> None:
        # conflicts shouldn't happen since moved is a subset of files from sourceOnly and destOnly
        # depends on source_info.dirCompare(dest_info) otherwise source and dest keys will be reversed
        self.colourPrint(getString("Moving %s files on destination to match source") %(len(moved)), "OKBLUE")
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
        self.colourPrint(getString("Moving completed!"), "NONE")

    def archiveFile(self, root_path: str, file_path: str) -> None:
        if not self.config.noarchive:
            archive_path = os.path.join(self.config.archive_dir, self.backup_time, file_path)
            self.moveFile(root_path, root_path, file_path, archive_path)

    def handleChanges(self, source: str, dest: str, source_dict: dict, dest_dict:dict, changed: list) -> None:
        self.colourPrint(getString("Handling %s file changes per selection mode") %(len(changed)), "OKBLUE")
        copy_status = StatusBar("Copying", len(changed), self.config.stdout_status_bar, gui=self.gui)
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
            print(self.colourString(getString("Dry Run"), "HEADER"))
        # init dir scanning and load previous scan data if available
        self.source = DirInfo(self.config.source, self.config.compare_mode, self.config.config_dir,
                              [self.config.archive_dir, self.config.log_dir, self.config.trash_dir],
                              self.gui)
        self.dest = DirInfo(self.config.dest, self.config.compare_mode, self.config.config_dir,
                            [self.config.archive_dir, self.config.log_dir, self.config.trash_dir],
                            self.gui)
        database_load_success = False
        if self.config.load_json:
            self.source.loadJson()
            self.dest.loadJson()
            if self.source.loaded_dicts != {} or self.dest.loaded_dicts != {}:
                database_load_success = True
        # scan directories, this is where CRC mode = all takes place
        self.colourPrint(getString("Scanning files on source:\n%s") %(self.config.source), "OKBLUE")
        self.source.scanDir(self.config.stdout_status_bar)
        self.colourPrint(getString("Scanning files on destination:\n%s") %(self.config.dest), "OKBLUE")
        self.dest.scanDir(self.config.stdout_status_bar)
        # compare directories, this is where CRC mode = both takes place
        self.colourPrint(getString("Comparing directories..."), "OKGREEN")
        sourceOnly, destOnly, changed, moved = self.source.dirCompare(self.dest, self.config.nomoves, self.config.filters)
        # get databases
        source_dict = self.source.getDirDict()
        source_diffs = self.source.getLoadedDiffs()
        source_missing = self.source.getMissingFiles()
        source_loaded_db = self.source.getLoadedDicts()
        dest_dict = self.dest.getDirDict()
        dest_diffs = self.dest.getLoadedDiffs()
        dest_missing = self.dest.getMissingFiles()
        dest_loaded_db = self.dest.getLoadedDicts()
        # print database conflicts, including both collisions from files being modified independently on both sides and unexpected missing files
        # note: this only notifies the user so they can intervene, it does not handle them in any special way, treating them as regular file changes, it can also be triggered by time zone or dst changes
        if database_load_success:
            self.log.append([getString("### DATABASE CONFLICTS ###")])
            if self.config.main_mode == "sync":
                sync_conflicts = []
                for f in source_diffs:
                    if f in dest_diffs:
                        sync_conflicts.append(f)
                sync_conflicts += sorted(list(set(list(source_missing.keys()) + list(dest_missing.keys()))))
                if len(sync_conflicts) >= 1:
                    print(self.colourString(getString("WARNING: found files modified in both source and destination since last scan"), "WARNING"))
                print(self.colourString(getString("Sync Database Conflicts: %s") %(len(sync_conflicts)), "HEADER"))
                self.printSyncDbConflicts(sync_conflicts, source_dict, dest_dict, source_loaded_db, dest_loaded_db)
                if self.config.quit_on_db_conflict and len(sync_conflicts) >= 1:
                    return self.abortRun()
            else:
                dest_conflicts = list(dest_diffs.keys()) + list(dest_missing.keys())
                if len(dest_diffs) >= 1:
                    print(self.colourString(getString("WARNING: found files modified in the destination since last scan"), "WARNING"))
                print(self.colourString(getString("Destination Database Conflicts: %s") %(len(dest_diffs)), "HEADER"))
                self.printDbConflicts(dest_conflicts, dest_dict, dest_loaded_db)
                if self.config.quit_on_db_conflict and len(dest_conflicts) >= 1:
                    return self.abortRun()
        # prepare diff messages
        if self.config.noarchive:
            archive_msg = getString("delete")
        else:
            archive_msg = getString("archive")
        if self.config.main_mode == "sync":
            dest_msg = getString("(copy to source)")
        elif self.config.main_mode == "backup":
            dest_msg = getString("(left as is)")
        elif self.config.main_mode == "mirror":
            dest_msg = getString("(to be %sd)" %(archive_msg))
        if self.config.select_mode == "source":
            change_msg = getString("(%s dest and copy from source)" %(archive_msg))
        elif self.config.select_mode == "dest":
            change_msg = getString("(%s source and copy from dest)" %(archive_msg))
        elif self.config.select_mode == "new":
            change_msg = getString("(%s older and copy newer)" %(archive_msg))
        elif self.config.select_mode == "no":
            change_msg = getString("(left as is)")
        if self.config.norun:
            simulation_msg = getString(" dry run")
        else:
            simulation_msg = ""
        # print differences
        print(self.colourString(getString("Source Only (copy to dest): %s") %(len(sourceOnly)), "HEADER"))
        self.log.append([getString("### SOURCE ONLY ###")])
        self.printFiles(sourceOnly, source_dict)
        print(self.colourString(getString("Destination Only %s: %s") %(dest_msg, len(destOnly)), "HEADER"))
        self.log.append([getString("### DESTINATION ONLY ###")])
        self.printFiles(destOnly, dest_dict)
        print(self.colourString(getString("Changed Files %s: %s") %(change_msg, len(changed)), "HEADER"))
        self.log.append([getString("### CHANGED FILES ###")])
        self.printChangedFiles(changed, source_dict, dest_dict)
        if not self.config.nomoves:
            print(self.colourString(getString("Moved Files (move on dest to match source): %s") %(len(moved)), "HEADER"))
            self.log.append([getString("### MOVED FILES ###")])
            self.printMovedFiles(moved, source_dict, dest_dict)
        # exit if directories already match
        if len(sourceOnly) == 0 and len(destOnly) == 0 and len(changed) == 0 and len(moved) == 0:
            print(self.colourString(getString("Directories already match, completed!"), "OKGREEN"))
            self.log.append([getString("### NO CHANGES FOUND ###")])
            self.writeLog(db=True)
            return 0
        # wait for go ahead
        if not self.config.noprompt:
            self.writeLog()
            if self.gui:
                go = self.gui_simplePrompt(getString("Scan complete, continue with %s%s?") %(self.config.main_mode, simulation_msg))
            else:
                print(self.colourString(getString("Scan complete, continue with %s%s (y/N)?") %(self.config.main_mode, simulation_msg), "OKGREEN"))
                go = input("> ")
            if go[0].lower() != "y":
                return self.abortRun()
        # backup operations
        self.log.append([getString("### START ") + self.config.main_mode.upper() + simulation_msg.upper() + " ###"])
        print(self.colourString(getString("Starting ") + self.config.main_mode, "OKGREEN"))
        if self.config.main_mode == "mirror":
            self.copyFiles(self.config.source, self.config.dest, sourceOnly, sourceOnly)
            if self.config.noarchive:
                self.removeFiles(self.config.dest, destOnly)
            else:
                recycle_bin = os.path.join(self.config.dest, self.config.trash_dir, self.backup_time)
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
        self.log.append([getString("### COMPLETED ###")])
        self.writeLog(db=True)
        print(self.colourString(getString("Completed!"), "OKGREEN"))
        return 0


def main():
    parser = argparse.ArgumentParser(description=getString("BackuPy: A simple backup program in python with an emphasis on transparent behaviour"), formatter_class=ArgparseCustomFormatter)
    parser.add_argument("source", action="store", type=str,
                        help=getString("Path of source"))
    parser.add_argument("dest", action="store", type=str, nargs="?", default=None,
                        help=getString("Path of destination"))
    parser.add_argument("-m", type=str.lower, dest="main_mode", default="mirror", metavar="mode", choices=["mirror", "backup", "sync"],
                        help=getString("F!\n"
                             "Main mode:\n"
                             "How to handle files that exist only on one side?\n"
                             "  MIRROR (default)\n"
                             "    [source-only -> destination, delete destination-only]\n"
                             "  BACKUP\n"
                             "    [source-only -> destination, keep destination-only]\n"
                             "  SYNC\n"
                             "    [source-only -> destination, destination-only -> source]"))
    parser.add_argument("-s", type=str.lower, dest="select_mode", default="source", metavar="mode", choices=["source", "dest", "new", "no"],
                        help=getString("F!\n"
                             "Selection mode:\n"
                             "How to handle files that exist on both sides but differ?\n"
                             "  SOURCE (default)\n"
                             "    [copy source to destination]\n"
                             "  DEST\n"
                             "    [copy destination to source]\n"
                             "  NEW\n"
                             "    [copy newer to opposite side]\n"
                             "  NO\n"
                             "    [do nothing]"))
    parser.add_argument("-c", type=str.lower, dest="compare_mode", default="attr", metavar="mode", choices=["attr", "both", "crc"],
                        help=getString("F!\n"
                             "Compare mode:\n"
                             "How to detect files that exist on both sides but differ?\n"
                             "  ATTR (default)\n"
                             "    [compare file attributes: mod-time and size]\n"
                             "  BOTH\n"
                             "    [compare file attributes first, then check CRC]\n"
                             "  CRC\n"
                             "    [compare CRC only, ignoring file attributes]"))
    parser.add_argument("--nomoves", action="store_true",
                        help=getString("Do not detect moved or renamed files"))
    parser.add_argument("--noarchive", action="store_true",
                        help=getString("F!\n"
                             "Disable archiving files before overwriting/deleting to:\n"
                             "  <source|dest>/.backupy/Archives/yymmdd-HHMM/\n"
                             "  <source|dest>/.backupy/Trash/yymmdd-HHMM/"))
    parser.add_argument("--nolog", action="store_true",
                        help=getString("F!\n"
                             "Disable writing to:\n"
                             "  <source>/.backupy/Logs/log-yymmdd-HHMM.csv\n"
                             "  <source|dest>/.backupy/database.json"))
    parser.add_argument("--noprompt", action="store_true",
                        help=getString("Complete run without prompting for confirmation"))
    parser.add_argument("--norun", action="store_true",
                        help=getString("Perform a dry run according to your configuration"))
    parser.add_argument("--save", action="store_true",
                        help=getString("Save configuration to <source>/.backupy/config.json"))
    parser.add_argument("--load", action="store_true",
                        help=getString("Load configuration from <source>/.backupy/config.json"))
    parser.add_argument("-f", action="store", type=str, nargs="*", default=False, dest="filter", metavar="regex",
                        help=argparse.SUPPRESS)
    parser.add_argument("-ff", action="store", type=str, nargs="*", default=False, dest="filter_false", metavar="regex",
                        help=argparse.SUPPRESS)
    args = parser.parse_args()
    backup_manager = BackupManager(args)
    backup_manager.backup()


if __name__ == "__main__":
    sys.exit(main())
