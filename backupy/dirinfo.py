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
import re
import typing
import zlib

from .statusbar import StatusBar
from .utils import (
    readJson,
    writeJson,
)


class DirInfo:
    def __init__(self, directory_root_path: str, compare_mode: str,  config_dir: str,
                 ignored_toplevel_folders: list = [], gui: bool = False, force_posix_path_sep: bool = False,
                 filter_include_list: typing.Union[list, None] = None, filter_exclude_list: typing.Union[list, None] = None):
        """For scanning directories, tracking files and changes, meant only for internal use by BackupManager"""
        # File dictionaries, keys are paths relative to directory_root_path, values are dictionaries of file attributes
        self.dict_current = {}
        self.dict_prev = {}
        self.dict_modified = {}
        self.dict_missing = {}
        self.dict_new = {}
        self.dict_crc_errors = {}
        self.dict_dirs = {}
        # Init filters
        self.filter_include_list = None
        self.filter_exclude_list = None
        try:
            if filter_include_list is not None:
                self.filter_include_list = [re.compile(f) for f in filter_include_list]
            if filter_exclude_list is not None:
                self.filter_exclude_list = [re.compile(f) for f in filter_exclude_list]
        except Exception:
            raise Exception("Filter Processing Error")
        # Init other variables
        self.dir = directory_root_path
        self.compare_mode = compare_mode
        self.config_dir = config_dir
        self.ignored_toplevel_folders = list(set(ignored_toplevel_folders[:] + [config_dir]))
        self.gui = gui
        self.force_posix_path_sep = force_posix_path_sep

    def getDicts(self) -> tuple:
        """Returns tuple of dictionaries: current, prev, new, modified, missing, crc_errors, dirs"""
        return (self.dict_current,
                self.dict_prev,
                self.dict_new,
                self.dict_modified,
                self.dict_missing,
                self.dict_crc_errors,
                self.dict_dirs)

    def getSets(self) -> tuple:
        """Returns tuple of set(dictionaries): current, prev, new, modified, missing, crc_errors, dirs"""
        return (set(self.dict_current),
                set(self.dict_prev),
                set(self.dict_new),
                set(self.dict_modified),
                set(self.dict_missing),
                set(self.dict_crc_errors),
                set(self.dict_dirs))

    def saveJson(self, db_name: str = "database.json") -> None:
        writeJson(os.path.join(self.dir, self.config_dir, db_name), self.dict_current, sort_keys=True)

    def loadJson(self) -> None:
        self.dict_prev = readJson(os.path.join(self.dir, self.config_dir, "database.json"))

    def verifyCrcOnCopy(self, source_root: str, dest_root: str, source_file: str, dest_file: str, secondInfo: 'DirInfo') -> None:
        if self.dir == source_root and secondInfo.dir == dest_root:
            if secondInfo.getCrc(dest_file, recalc=True) != self.getCrc(source_file):
                raise Exception("CRC Verification Failed")
        elif self.dir == dest_root and secondInfo.dir == source_root:
            if self.getCrc(dest_file, recalc=True) != secondInfo.getCrc(source_file):
                raise Exception("CRC Verification Failed")

    def updateDictOnCopy(self, source_root: str, dest_root: str, source_file: str, dest_file: str, secondInfo: 'DirInfo') -> None:
        if self.dir == source_root and secondInfo.dir == dest_root:
            secondInfo.dict_current[dest_file] = self.dict_current[source_file].copy()
        elif self.dir == dest_root and secondInfo.dir == source_root:
            self.dict_current[dest_file] = secondInfo.dict_current[source_file].copy()
        else:
            raise Exception("Update Database Error")

    def updateDictOnMove(self, source_root: str, dest_root: str, source_file: str, dest_file: str, secondInfo: 'DirInfo') -> None:
        if source_root == dest_root == self.dir:
            self.dict_current[dest_file] = self.dict_current.pop(source_file)
        elif source_root == dest_root == secondInfo.dir:
            secondInfo.dict_current[dest_file] = secondInfo.dict_current.pop(source_file)
        elif source_root == self.dir and dest_root != secondInfo.dir:
            _ = self.dict_current.pop(source_file)
        elif source_root == secondInfo.dir and dest_root != self.dir:
            _ = secondInfo.dict_current.pop(source_file)
        else:
            raise Exception("Update Database Error")

    def updateDictOnRemove(self, root_path: str, file_relative_path: str, secondInfo: 'DirInfo') -> None:
        if root_path == self.dir:
            _ = self.dict_current.pop(file_relative_path)
        elif root_path == secondInfo.dir:
            _ = secondInfo.dict_current.pop(file_relative_path)
        else:
            raise Exception("Update Database Error")

    def getCrc(self, relative_path: str, recalc: bool = False) -> str:
        if recalc or "crc" not in self.dict_current[relative_path]:
            full_path = os.path.join(self.dir, relative_path)
            self.dict_current[relative_path]["crc"] = self.calcCrc(full_path)
        return self.dict_current[relative_path]["crc"]

    def calcCrc(self, file_path: str, prev: int = 0) -> str:
        with open(file_path, "rb") as f:
            for line in f:
                prev = zlib.crc32(line, prev)
        return "%X" % (prev & 0xFFFFFFFF)

    def timeMatch(self, t1: float, t2: float, exact_only: bool = False, tz_diffs: list = [3600, 3601, 3602], fs_tol: int = 2) -> bool:
        if t1 == t2:
            return True
        elif exact_only:
            return False
        diff = abs(int(t1) - int(t2))
        if diff <= fs_tol or diff in tz_diffs:
            return True
        else:
            return False

    def pathMatch(self, path: str, path_list: list) -> bool:
        # is path in path_list (or a subdir of one in it)
        if os.path.isabs(path):
            relpath, _abspath = os.path.relpath(path, self.dir), path
        else:
            relpath, _abspath = path, os.path.join(self.dir, path)
        for p in path_list:
            p = os.path.normcase(p)
            if os.path.isabs(p):
                raise Exception("Default .backupy dirs have been changed to absolute paths in the config, they should be relative paths.")
                # if os.path.normcase(os.path.commonpath([p, abspath])) == p:
                #     return True
            else:
                if os.path.normcase(os.path.commonpath([p, relpath])) == p:
                    return True
        return False

    def fileMatch(self, f1: str, f2: str, secondInfo: 'DirInfo', compare_mode: str, move_check: bool = False) -> bool:
        if self.dict_current[f1]["size"] == secondInfo.dict_current[f2]["size"]:
            if self.timeMatch(self.dict_current[f1]["mtime"], secondInfo.dict_current[f2]["mtime"], False):
                # these are the 'unchanged files (probably)' from both sides, crc should be up to date from the scan if using CRC mode
                if compare_mode == "crc" and self.dict_current[f1]["crc"] != secondInfo.dict_current[f2]["crc"]:
                    # size and date match, but crc does not, probably corrupted
                    if f1 not in self.dict_crc_errors and f2 not in secondInfo.dict_crc_errors:
                        # log error since it wasn't already detected during scan, that implies neither file has a past record
                        self.dict_crc_errors[f1] = None
                        secondInfo.dict_crc_errors[f2] = None
                    return False
                # detect mismatched crc values across both sides (usually if corruption happened before crc database was created)
                if compare_mode == "attr+" and self.dict_current[f1]["crc"] != secondInfo.dict_current[f2]["crc"]:
                    if move_check:
                        # it may be corrupted or coincidence, just won't flag these files as matching
                        return False
                    self.dict_crc_errors[f1] = self.dict_current[f1]
                    secondInfo.dict_crc_errors[f2] = secondInfo.dict_current[f2]
                return True
        return False

    def scanDir(self, stdout_status_bar: bool) -> None:
        # init
        if os.path.isdir(self.dir) and self.dict_current == {}:
            total = sum(len(f) for r, d, f in os.walk(self.dir))
            scan_status = StatusBar("Scanning", total, stdout_status_bar, gui=self.gui)
            # will never enable followlinks, adds too many possible issues and complexity in handling them
            for dir_path, subdir_list, file_list in os.walk(self.dir, followlinks=False):
                # ignore folders
                if self.pathMatch(dir_path, self.ignored_toplevel_folders):
                    subdir_list.clear()
                    continue
                # apply filters
                if self.filter_include_list is not None:
                    subdir_list = filter(lambda x: any([True if r.search(x) else False for r in self.filter_include_list]), subdir_list)
                    file_list = filter(lambda x: any([True if r.search(x) else False for r in self.filter_include_list]), file_list)
                if self.filter_exclude_list is not None:
                    subdir_list = filter(lambda x: all([False if r.search(x) else True for r in self.filter_exclude_list]), subdir_list)
                    file_list = filter(lambda x: all([False if r.search(x) else True for r in self.filter_exclude_list]), file_list)
                # scan folders
                for subdir in subdir_list:
                    full_path = os.path.join(dir_path, subdir)
                    if len(os.listdir(full_path)) == 0:
                        # track empty directories with a dummy entry, non-empty directories should not have entries, they are handled automatically by having files inside them
                        relative_path = os.path.relpath(full_path, self.dir)
                        if self.force_posix_path_sep:
                            relative_path = relative_path.replace(os.path.sep, "/")
                        self.dict_current[relative_path] = {"size": 0, "mtime": 0, "crc": "0", "dir": True}
                        self.dict_dirs[relative_path] = {"size": 0, "mtime": 0, "crc": "0", "dir": True}
                # scan files
                for file_name in file_list:
                    full_path = os.path.join(dir_path, file_name)
                    relative_path = os.path.relpath(full_path, self.dir)
                    if self.force_posix_path_sep:
                        relative_path = relative_path.replace(os.path.sep, "/")
                    scan_status.update(relative_path)
                    self.scanFile(full_path, relative_path)
            scan_status.endProgress()
            # check for missing (or moved) files
            for relative_path in (set(self.dict_prev) - set(self.dict_current)):
                if "dir" not in self.dict_prev[relative_path]:
                    if not self.pathMatch(relative_path, self.ignored_toplevel_folders):
                        self.dict_missing[relative_path] = self.dict_prev[relative_path]
                # else:
                #     self.dict_dirs[relative_path] = {"size": 0, "mtime": 0, "crc": "0", "dir": False}

    def scanFile(self, full_path: str, relative_path: str) -> None:
        # get file attributes
        size = os.path.getsize(full_path)
        mtime = os.path.getmtime(full_path)
        # check and set database dictionaries
        if relative_path in self.dict_prev:
            if (
              self.dict_prev[relative_path]["size"] == size and
              self.timeMatch(self.dict_prev[relative_path]["mtime"], mtime, True)):
                # unchanged file (probably)
                self.dict_current[relative_path] = self.dict_prev[relative_path].copy()
            else:
                # changed file
                self.dict_current[relative_path] = {"size": size, "mtime": mtime}
                self.dict_modified[relative_path] = self.dict_prev[relative_path]
        else:
            # new file
            self.dict_current[relative_path] = {"size": size, "mtime": mtime}
            self.dict_new[relative_path] = self.dict_current[relative_path]
        if self.compare_mode == "crc":
            # calculate CRC for all files (simpler code and potential warning sign for disk issues)
            self.dict_current[relative_path]["crc"] = self.calcCrc(full_path)
            if (
              relative_path in self.dict_prev and
              "crc" in self.dict_prev[relative_path] and
              self.dict_prev[relative_path]["crc"] != self.dict_current[relative_path]["crc"] and
              self.dict_prev[relative_path]["size"] == size and
              self.timeMatch(self.dict_prev[relative_path]["mtime"], mtime, False)):
                # corrupted file (probably, changed crc, unchanged size and mtime)
                self.dict_crc_errors[relative_path] = self.dict_prev[relative_path]
        elif self.compare_mode == "attr+" and "crc" not in self.dict_current[relative_path]:
            # save time by only calculating crc for new and changed files (by attributes) so we can check for corruption later (and possibly preexisting)
            if (
              relative_path in self.dict_prev and
              "crc" in self.dict_prev[relative_path] and
              self.dict_prev[relative_path]["size"] == size and
              self.timeMatch(self.dict_prev[relative_path]["mtime"], mtime, False)):
                # attributes match, preserve old crc
                self.dict_current[relative_path]["crc"] = self.dict_prev[relative_path]["crc"]
            else:
                self.dict_current[relative_path]["crc"] = self.calcCrc(full_path)

    def getMovedAndUpdateLists(self, a_only: list, b_only: list, a_dict: dict, b_dict: dict, compare_func: typing.Callable) -> tuple:
        moved = []
        for f1 in reversed(a_only):
            if "dir" not in a_dict[f1]:
                for f2 in reversed(b_only):
                    if "dir" not in b_dict[f2]:
                        if compare_func(f1, f2):
                            moved.append({"source": f1, "dest": f2})
                            a_only.remove(f1)
                            b_only.remove(f2)
                            break
        moved.reverse()
        return moved

    def selfCompare(self, second_db: dict, exact_time: bool = True, compare_crc: bool = False, ignore_empty_dirs: bool = True) -> dict:
        # compare functions
        compare_crc = compare_crc and self.compare_mode == "crc"
        crc_match = lambda a, b: "crc" in a and "crc" in b and a["crc"] == b["crc"]
        file_match = lambda a, b, f: (a[f]["size"] == b[f]["size"] and
                                      self.timeMatch(a[f]["mtime"], b[f]["mtime"], exact_time) and
                                      (not compare_crc or crc_match(a[f], b[f])))
        # init and filter file sets
        ignored_path_match = lambda f: self.pathMatch(f, self.ignored_toplevel_folders)
        is_dir = lambda d, f: ignore_empty_dirs and "dir" in d[f] and d[f]["dir"] is True
        file_set_a = set(filter(lambda f: not ignored_path_match(f) and not is_dir(self.dict_current, f), self.dict_current))
        file_set_b = set(filter(lambda f: not ignored_path_match(f) and not is_dir(second_db, f), second_db))
        # compare
        modified = sorted(list(filter(lambda f: not file_match(self.dict_current, second_db, f), file_set_a & file_set_b)))
        new = sorted(list(file_set_a - file_set_b))
        missing = sorted(list(file_set_b - file_set_a))
        return {"modified": modified, "missing": missing, "new": new}

    def dirCompare(self, secondInfo: 'DirInfo', no_moves: bool = False) -> dict:
        "Use source.dirCompare(dest) to return diff of source and dest as dict of file lists"
        # init variables
        file_list = set(self.dict_current)
        second_list = set(secondInfo.dict_current)
        if self.compare_mode == secondInfo.compare_mode:
            compare_mode = self.compare_mode
        else:
            raise Exception("Inconsistent compare mode between directories")
        # compare
        changed = sorted(list(filter(lambda f: not self.fileMatch(f, f, secondInfo, compare_mode), file_list & second_list)))
        self_only = sorted(list(file_list - second_list))
        second_only = sorted(list(second_list - file_list))
        moved = []
        if not no_moves:
            compare_func = lambda f1, f2: self.fileMatch(f1, f2, secondInfo, compare_mode, True)
            moved = self.getMovedAndUpdateLists(self_only, second_only, self.dict_current, secondInfo.dict_current, compare_func)
            for pair in moved:
                if pair["source"] not in self.dict_modified and pair["dest"] not in secondInfo.dict_modified:
                    _ = secondInfo.dict_missing.pop(pair["source"], 1)
                    _ = self.dict_missing.pop(pair["dest"], 1)
        return {"source_only": self_only, "dest_only": second_only, "changed": changed, "moved": moved}
