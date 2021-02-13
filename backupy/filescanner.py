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

from .config import ConfigObject
from .statusbar import StatusBar
from .utils import (
    readJson,
    writeJson,
)


class FileScanner:
    def __init__(self, directory_root_path: str, unique_id: str,
                 other_root_path: str, config: ConfigObject, gui: bool = False):
        """For scanning directories, tracking files and changes, meant only for internal use by BackupManager"""
        # File dictionaries, keys are paths relative to directory_root_path, values are dictionaries of file attributes
        self.dict_current = {}
        self.dict_prev = {}
        # File sets of relative paths
        self.set_unmodified = set()
        self.set_modified = set()
        self.set_missing = set()
        self.set_new = set()
        self.set_crc_errors = set()
        self.set_dirs = set()
        # Init filters
        self.filter_include_list = None
        self.filter_exclude_list = None
        try:
            if config.filter_include_list is not None:
                self.filter_include_list = [re.compile(f) for f in config.filter_include_list]
            if config.filter_exclude_list is not None:
                self.filter_exclude_list = [re.compile(f) for f in config.filter_exclude_list]
        except Exception:
            raise Exception("Filter Processing Error")
        # Init variables from config
        self.compare_mode = config.compare_mode
        self.config_dir = config.config_dir
        self.ignored_toplevel_folders = list(set([config.archive_dir, config.log_dir, config.trash_dir, config.config_dir]))
        self.force_posix_path_sep = config.force_posix_path_sep
        self.write_database_x2 = config.write_database_x2 and not config.scan_only
        # Init other variables
        self.dir = directory_root_path
        self.other_dir = other_root_path
        self.unique_id = unique_id
        self.gui = gui

    def getDicts(self) -> tuple:
        """Returns tuple of dictionaries: current, prev"""
        return (self.dict_current,
                self.dict_prev)

    def getSets(self) -> tuple:
        """Returns tuple of sets: new, modified, missing, crc_errors, dirs, unmodified"""
        return (self.set_new,
                self.set_modified,
                self.set_missing,
                self.set_crc_errors,
                self.set_dirs,
                self.set_unmodified)

    def saveDatabase(self, db_name: str = "database.json") -> None:
        """Write database to config_dir on self and other if enabled"""
        writeJson(os.path.join(self.dir, self.config_dir, db_name), self.dict_current, sort_keys=True)
        if self.write_database_x2:
            other_db_path = os.path.join(self.other_dir, self.config_dir, "database-%s%s" % (self.unique_id, db_name[8:]))
            writeJson(other_db_path, self.dict_current, sort_keys=True)

    def loadDatabase(self, use_cold_storage: bool = False) -> None:
        """Load database from config_dir"""
        if use_cold_storage:
            self.dict_current = self.getDatabaseX2(False)
            self.dict_prev = self.dict_current
            self.set_unmodified = set(self.dict_current.keys())
        else:
            self.dict_prev = readJson(os.path.join(self.dir, self.config_dir, "database.json"))

    def getDatabaseX2(self, fallback: bool = True) -> dict:
        """Get the 'last seen' database of this directory from the perspective of the other directory"""
        other_db_path = os.path.join(self.other_dir, self.config_dir, "database-%s.json" % self.unique_id)
        database_x2 = readJson(other_db_path)
        if database_x2 or not fallback:
            return database_x2
        else:
            return self.dict_prev

    def verifyCrcOnCopy(self, source_root: str, dest_root: str, source_file: str, dest_file: str, other_scanner: 'FileScanner') -> None:
        if self.dir == source_root and other_scanner.dir == dest_root:
            if other_scanner.getCrc(dest_file, recalc=True) != self.getCrc(source_file):
                raise Exception("CRC Verification Failed")
        elif self.dir == dest_root and other_scanner.dir == source_root:
            if self.getCrc(dest_file, recalc=True) != other_scanner.getCrc(source_file):
                raise Exception("CRC Verification Failed")

    def updateDictOnCopy(self, source_root: str, dest_root: str, source_file: str, dest_file: str, other_scanner: 'FileScanner') -> None:
        if self.dir == source_root and other_scanner.dir == dest_root:
            other_scanner.dict_current[dest_file] = self.dict_current[source_file].copy()
        elif self.dir == dest_root and other_scanner.dir == source_root:
            self.dict_current[dest_file] = other_scanner.dict_current[source_file].copy()
        else:
            raise Exception("Update Database Error")

    def updateDictOnMove(self, source_root: str, dest_root: str, source_file: str, dest_file: str, other_scanner: 'FileScanner') -> None:
        if source_root == dest_root == self.dir:
            self.dict_current[dest_file] = self.dict_current.pop(source_file)
        elif source_root == dest_root == other_scanner.dir:
            other_scanner.dict_current[dest_file] = other_scanner.dict_current.pop(source_file)
        elif source_root == self.dir and dest_root != other_scanner.dir:
            _ = self.dict_current.pop(source_file)
        elif source_root == other_scanner.dir and dest_root != self.dir:
            _ = other_scanner.dict_current.pop(source_file)
        else:
            raise Exception("Update Database Error")

    def updateDictOnRemove(self, root_path: str, file_relative_path: str, other_scanner: 'FileScanner') -> None:
        if root_path == self.dir:
            _ = self.dict_current.pop(file_relative_path)
        elif root_path == other_scanner.dir:
            _ = other_scanner.dict_current.pop(file_relative_path)
        else:
            raise Exception("Update Database Error")

    def getCrc(self, relative_path: str, recalc: bool = False) -> str:
        if relative_path not in self.dict_current:
            self.dict_current[relative_path] = {"size": 0, "mtime": 0}
        if recalc or "crc" not in self.dict_current[relative_path]:
            full_path = os.path.join(self.dir, relative_path)
            self.dict_current[relative_path]["crc"] = self.calcCrc(full_path)
        return self.dict_current[relative_path]["crc"]

    def calcCrc(self, file_path: str, prev: int = 0) -> str:
        try:
            with open(file_path, "rb") as f:
                for line in f:
                    prev = zlib.crc32(line, prev)
            return "%X" % (prev & 0xFFFFFFFF)
        except Exception:
            # file either removed by user, or another program such as antimalware (using realtime monitoring) during scan, or lack permissions
            raise Exception("Exiting, error trying to read file: " + file_path)

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

    def fileMatch(self, f1: str, f2: str, other_db: dict, other_crc_errors: set, exact_time: bool) -> bool:
        if self.dict_current[f1]["size"] == other_db[f2]["size"]:
            if self.timeMatch(self.dict_current[f1]["mtime"], other_db[f2]["mtime"], exact_time):
                # unchanged files (probably)
                if "crc" in self.dict_current[f1] and "crc" in other_db[f2] and self.dict_current[f1]["crc"] != other_db[f2]["crc"]:
                    # size and date match, but crc does not, probably corrupted, log error if scanning or comparing sides (f1 == f2), otherwise this is just checking if moved (f1 != f2) (but if time is exact, still flag it to be safe)
                    if f1 == f2 or exact_time:
                        self.set_crc_errors.add(f1)
                        other_crc_errors.add(f2)
                    return False
                return True
        return False

    def scanDir(self, stdout_status_bar: bool) -> None:
        # init
        if os.path.isdir(self.dir) and self.dict_current == {}:
            total = sum(len(f) for r, d, f in os.walk(self.dir))
            scan_status = StatusBar("Scanning", total, stdout_status_bar, gui=self.gui)
            # will never enable followlinks, adds too many possible issues and complexity in handling them
            # may add notification if backupy encounters a directory it cannot access (likely due to permissions)
            for dir_path, subdir_list, file_list in os.walk(self.dir, onerror=None, followlinks=False):
                # ignore folders
                if self.pathMatch(dir_path, self.ignored_toplevel_folders):
                    subdir_list.clear()
                    continue
                # apply filters
                if self.filter_include_list is not None:
                    subdir_list = filter(lambda x: any([True if r.search(os.path.join(dir_path, x)) else False for r in self.filter_include_list]), subdir_list)
                    file_list = filter(lambda x: any([True if r.search(os.path.join(dir_path, x)) else False for r in self.filter_include_list]), file_list)
                if self.filter_exclude_list is not None:
                    subdir_list = filter(lambda x: all([False if r.search(os.path.join(dir_path, x)) else True for r in self.filter_exclude_list]), subdir_list)
                    file_list = filter(lambda x: all([False if r.search(os.path.join(dir_path, x)) else True for r in self.filter_exclude_list]), file_list)
                # scan folders
                for subdir in subdir_list:
                    full_path = os.path.join(dir_path, subdir)
                    try:
                        if len(os.listdir(full_path)) == 0:
                            # track empty directories with a dummy entry, non-empty directories should not have entries, they are handled automatically by having files inside them
                            relative_path = os.path.relpath(full_path, self.dir)
                            if self.force_posix_path_sep:
                                relative_path = relative_path.replace(os.path.sep, "/")
                            self.dict_current[relative_path] = {"size": 0, "mtime": 0, "crc": "0", "dir": True}
                            self.set_dirs.add(relative_path)
                    except Exception as e:
                        raise Exception("%s %s for directory: %s" % (type(e).__name__, str(e.args), full_path))
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
                        self.set_missing.add(relative_path)

    def scanFile(self, full_path: str, relative_path: str) -> None:
        # get file attributes and create entry
        size = os.path.getsize(full_path)
        mtime = os.path.getmtime(full_path)
        self.dict_current[relative_path] = {"size": size, "mtime": mtime}
        if self.compare_mode == "crc":
            self.dict_current[relative_path]["crc"] = self.calcCrc(full_path)
        # check if file is new, modified, or corrupted
        if relative_path in self.dict_prev:
            # calculate crc for attr+ unless it's an exact time match and there's a previous crc to copy
            if self.compare_mode == "attr+" and not ("crc" in self.dict_prev[relative_path] and self.fileMatch(relative_path, relative_path, self.dict_prev, set(), exact_time=True)):
                self.dict_current[relative_path]["crc"] = self.calcCrc(full_path)
            # checking if the file changed, accounting for time rounding and DST
            if self.fileMatch(relative_path, relative_path, self.dict_prev, set(), exact_time=False):
                # unchanged file (probably) (keep old crc value if exists and not already recalculated)
                self.set_unmodified.add(relative_path)
                if self.compare_mode in ["attr", "attr+"] and "crc" in self.dict_prev[relative_path] and "crc" not in self.dict_current[relative_path]:
                    self.dict_current[relative_path]["crc"] = self.dict_prev[relative_path]["crc"]
            else:
                # changed file (or corrupted and added to self.set_crc_errors by fileMatch)
                if relative_path not in self.set_crc_errors:
                    self.set_modified.add(relative_path)
        else:
            # new file
            self.set_new.add(relative_path)
            if self.compare_mode == "attr+":
                self.dict_current[relative_path]["crc"] = self.calcCrc(full_path)

    def getMovedAndUpdateLists(self, a_only: list, b_only: list, a_dict: dict, b_dict: dict, compare_func: typing.Callable) -> list:
        # f1 is in a is "source" and f2 is in b is "dest"
        moved = []
        for f1 in reversed(a_only):
            if "dir" not in a_dict[f1]:
                for f2 in reversed(b_only):
                    if "dir" not in b_dict[f2]:
                        if compare_func(f1, f2):
                            moved.append({"source": f1, "dest": f2, "match": "source"})
                            a_only.remove(f1)
                            b_only.remove(f2)
                            break
        moved.reverse()
        return moved

    def compareDb(self, other_db: dict, other_crc_errors: set, detect_moves: bool, exact_time: bool, ignore_empty_dirs: bool) -> dict:
        # init and filter file sets (for ignored paths, user filters are done on scan)
        ignored_path_match = lambda f: self.pathMatch(f, self.ignored_toplevel_folders)
        is_dir = lambda d, f: ignore_empty_dirs and "dir" in d[f] and d[f]["dir"] is True
        self_set = set(filter(lambda f: not ignored_path_match(f) and not is_dir(self.dict_current, f), self.dict_current))
        other_set = set(filter(lambda f: not ignored_path_match(f) and not is_dir(other_db, f), other_db))
        # compare file sets
        changed_compare_func = lambda f: not self.fileMatch(f, f, other_db, other_crc_errors, exact_time=exact_time)
        changed = set(filter(changed_compare_func, self_set & other_set))
        changed = sorted(list(changed - (self.set_crc_errors | other_crc_errors)))
        self_only = sorted(list(self_set - other_set))
        other_only = sorted(list(other_set - self_set))
        moved = []
        if detect_moves:
            moved_compare_func = lambda f1, f2: self.fileMatch(f1, f2, other_db, other_crc_errors, exact_time=True)
            moved = self.getMovedAndUpdateLists(self_only, other_only, self.dict_current, other_db, moved_compare_func)
        return {"self_only": self_only, "other_only": other_only, "changed": changed, "moved": moved}

    def compareOtherScanner(self, other_scanner: 'FileScanner', no_moves: bool) -> dict:
        diff = self.compareDb(other_scanner.dict_current, other_scanner.set_crc_errors, not no_moves, False, False)
        for pair in diff["moved"]:
            if pair["source"] not in self.set_modified and pair["dest"] not in other_scanner.set_modified:
                other_scanner.set_missing.discard(pair["source"])
                self.set_missing.discard(pair["dest"])
        return diff
