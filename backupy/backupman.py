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

import argparse
import datetime
import os
import sys
import time
import typing

from .config import ConfigObject
from .dirinfo import DirInfo
from .fileman import FileManager
from .logman import LogManager
from .utils import (
    getString,
    getVersion,
    readJson,
    writeJson,
)


class BackupManager():
    def __init__(self, args: typing.Union[argparse.Namespace, dict], gui: bool = False):
        """Main class, configure with an argparse namespace or dictionary to create a job then execute with .run()"""
        # init time
        self.backup_time = datetime.datetime.now().strftime("%y%m%d-%H%M")
        # debugging/testing
        if "backup_time_override" in args and args["backup_time_override"]:
            self.backup_time = args["backup_time_override"]
            time.ctime = lambda t: time.asctime(time.gmtime(t))
        # init config
        if type(args) != dict:
            args = vars(args)
        self.config = ConfigObject(args)
        # load config (be careful if using a non-default config_dir!)
        if "load" in args and args["load"] is True:
            self.loadConfig()
        # set args that can overwrite loaded config
        if "dry_run" in args and args["dry_run"] is True:
            self.config.dry_run = True
        if "scan_only" in args and args["scan_only"] is True:
            self.config.scan_only = True
        if "compare_mode" in args and args["compare_mode"] is not None:
            self.config.compare_mode = args["compare_mode"]
        # init log and file manager (don't create a new ConfigObject after this point)
        self.log = LogManager(self.config, self.backup_time, gui)
        self.fileman = FileManager(self.log, self.config, self.backup_time, gui)
        # scan only mode
        if self.config.scan_only and (self.config.dest is None or not os.path.isdir(self.config.dest)):
            self.config.dest = self.config.source
        # check source & dest
        if not os.path.isdir(self.config.source):
            print(self.log.colourString(getString("Invalid source directory: ") + self.config.source, "FAIL"))
            sys.exit()
        if self.config.dest is None:
            print(self.log.colourString(getString("Destination directory not provided or config failed to load"), "FAIL"))
            sys.exit()
        self.config.source = os.path.abspath(self.config.source)
        self.config.dest = os.path.abspath(self.config.dest)
        # save config
        if "save" in args and args["save"] is True:
            self.saveConfig()
        # init gui flag
        self.gui = gui
        # gui modifications
        if self.gui:
            from .gui import simplePrompt
            self.gui_simplePrompt = simplePrompt
            self.config.stdout_status_bar = False
        # log settings
        self.log.append([getString("### SETTINGS ###")])
        self.log.append([getString("Time:"), self.backup_time,
                         getString("Version:"), getVersion(),
                         getString("Source DB CRC:"), "0",
                         getString("Dest DB CRC:"), "0",
                         getString("Config:"), str(vars(self.config))])

    def saveConfig(self) -> None:
        writeJson(os.path.join(self.config.source, self.config.config_dir, "config.json"), vars(self.config))
        print(self.log.colourString(getString("Config saved"), "OKGREEN"))
        sys.exit()

    def loadConfig(self) -> None:
        current_source = self.config.source
        config_dir = os.path.abspath(os.path.join(self.config.source, self.config.config_dir, "config.json"))
        config = readJson(config_dir)
        print(self.log.colourString(getString("Loaded config from:") + "\n" + config_dir, "OKGREEN"))
        self.config = ConfigObject(config)
        if self.config.source is None or os.path.abspath(current_source) != os.path.abspath(self.config.source):
            print(self.log.colourString(getString("A config file matching the specified source was not found (case sensitive)"), "FAIL"))
            sys.exit()

    def abortRun(self) -> int:
        self.log.append([getString("### ABORTED ###")])
        self.log.writeLog("database.aborted.json")
        print(self.log.colourString(getString("Run aborted"), "WARNING"))
        return 1

    def _skipFileTransfers(self, source_only: list, dest_only: list, changed: list) -> bool:
        self.log.append([getString("### SKIPPED ###")])
        while True:
            print(self.log.colourString(getString("Enter file paths to remove from transfer queue, then 'continue' when ready or 'cancel' to abort"), "OKGREEN"))
            p = input("> ")
            if len(p) == 0 or p == "?":
                print(self.log.colourString(getString("Enter file paths to remove from transfer queue, then 'continue' when ready or 'cancel' to abort"), "OKGREEN"))
            elif p == "continue":
                return True
            elif p == "cancel":
                return False
            if p in source_only:
                source_only.remove(p)
                self.log.append(["File:", "Source", p])
            elif p in dest_only:
                dest_only.remove(p)
                self.log.append(["File:", "Dest", p])
            elif p in changed:
                changed.remove(p)
                self.log.append(["File:", "Changed", p])
            else:
                print(self.log.colourString(getString("Could not find file in queues: %s") % (p), "WARNING"))

    def _checkConsistency(self, dest_database_load_success: bool,
                          source_only: list, dest_only: list, changed: list, moved: list) -> None:
        d1, d2, d3, d4, d5, d6, d7 = self.source.getDicts()
        source_dict, source_prev, source_new, source_modified, source_missing, source_crc_errors, source_dirs = set(d1), set(d2), set(d3), set(d4), set(d5), set(d6), set(d7)
        d1, d2, d3, d4, d5, d6, d7 = self.dest.getDicts()
        dest_dict, dest_prev, dest_new, dest_modified, dest_missing, dest_crc_errors, dest_dirs = set(d1), set(d2), set(d3), set(d4), set(d5), set(d6), set(d7)
        source_only, dest_only, changed = set(source_only), set(dest_only), set(changed)
        source_moved = set([f["source"] for f in moved])
        dest_moved = set([f["dest"] for f in moved])
        assert not (source_moved & dest_moved)
        assert changed <= (source_modified | dest_modified) | (source_new & dest_new) | (source_crc_errors | dest_crc_errors)
        assert source_only <= source_dict
        assert dest_only <= dest_dict
        # prev dirs and prev files under .backupy cause the next two asserts to be <=
        assert source_dict <= (source_prev - (source_missing | dest_moved)) | source_new | source_dirs
        assert dest_dict <= (dest_prev - (dest_missing | source_moved)) | dest_new | dest_dirs

    def _databaseAndCorruptionCheck(self, dest_database_load_success: bool) -> bool:
        # get databases
        source_dict, source_prev, source_new, source_modified, source_missing, source_crc_errors, _ = self.source.getDicts()
        dest_dict, dest_prev, dest_new, dest_modified, dest_missing, dest_crc_errors, _ = self.dest.getDicts()
        # print database conflicts, including both collisions from files being modified independently on both sides and unexpected missing files
        # note: this only notifies the user so they can intervene, it does not handle them in any special way, treating them as regular file changes
        # it can also be triggered by time zone or dst changes, lower file system mod time precision, and corruption if using CRCs (handled next)
        abort_run = False
        if dest_database_load_success and self.config.source != self.config.dest:
            self.log.append([getString("### DATABASE CONFLICTS ###")])
            if self.config.main_mode == "sync":
                sync_conflicts = sorted(list(set(source_modified) & set(dest_modified)))  # modified on both sides
                sync_conflicts += sorted(list(set(source_missing) | set(dest_missing)))  # deleted from either or both sides
                sync_conflicts += sorted(list(set(source_new) & set(dest_new)))  # new on both sides
                # new and different on both sides
                # sorted(list(filter(lambda f: source_new[f] != dest_new[f], set(source_new) & set(dest_new))))
                if len(sync_conflicts) >= 1:
                    print(self.log.colourString(getString("WARNING: found files modified in both source and destination since last scan"), "WARNING"))
                    abort_run = True
                print(self.log.colourString(getString("Sync Database Conflicts: %s") % (len(sync_conflicts)), "HEADER"))
                self.log.printSyncDbConflicts(sync_conflicts, source_dict, dest_dict, source_prev, dest_prev)
            else:
                dest_conflicts = sorted(list(set(dest_modified)))
                dest_conflicts += sorted(list(set(dest_missing)))
                dest_conflicts += sorted(list(set(dest_new)))
                if len(dest_conflicts) >= 1:
                    print(self.log.colourString(getString("WARNING: found files modified in the destination since last scan"), "WARNING"))
                    abort_run = True
                print(self.log.colourString(getString("Destination Database Conflicts: %s") % (len(dest_conflicts)), "HEADER"))
                self.log.printChangedFiles(dest_conflicts, dest_dict, dest_prev, "   Dest", "     DB")
        # print database conflicts concerning CRCs if available, as well as CRC conflicts between source and dest if attributes otherwise match
        if len(source_crc_errors) > 0 or len(dest_crc_errors) > 0:
            self.log.append([getString("### CRC ERRORS DETECTED ###")])
            print(self.log.colourString(getString("WARNING: found non matching CRC values, possible corruption detected"), "WARNING"))
            abort_run = True
            if self.config.compare_mode == "crc":
                crc_errors_detected = sorted(list(set(source_crc_errors) | set(dest_crc_errors)))
                print(self.log.colourString(getString("CRC Errors Detected: %s") % (len(crc_errors_detected)), "HEADER"))
                self.log.printSyncDbConflicts(crc_errors_detected, source_dict, dest_dict, source_prev, dest_prev)
            elif self.config.compare_mode == "attr+":
                if set(source_crc_errors) != set(dest_crc_errors):
                    raise Exception("Inconsistent CRC error detection between source and dest")
                print(self.log.colourString(getString("CRC Errors Detected: %s") % (len(source_crc_errors)), "HEADER"))
                self.log.printChangedFiles(sorted(list(source_crc_errors)), source_crc_errors, dest_crc_errors)
        return abort_run

    def _printAndLogScanOnlyDiffSummary(self, side_str: str, side_info: "DirInfo") -> None:
        # get databases
        side_dict, side_prev, side_new, side_modified, side_missing, _, _ = side_info.getDicts()
        compare_func = lambda f1, f2: side_new[f1] == side_missing[f2]
        list_new, list_missing = sorted(list(side_new)), sorted(list(side_missing))
        moved = side_info.getMovedAndUpdateLists(list_new, list_missing, side_new, side_missing, compare_func)
        # print differences
        print(self.log.colourString(getString("%s New Files: %s") % (side_str, len(list_new)), "HEADER"))
        self.log.append([getString("### %s NEW FILES ###") % (side_str.upper())])
        self.log.printFiles(list_new, side_dict)
        print(self.log.colourString(getString("%s Missing Files: %s") % (side_str, len(list_missing)), "HEADER"))
        self.log.append([getString("### %s MISSING FILES ###") % (side_str.upper())])
        self.log.printFiles(list_missing, side_prev)
        print(self.log.colourString(getString("%s Changed Files: %s") % (side_str, len(side_modified)), "HEADER"))
        self.log.append([getString("### %s CHANGED FILES ###") % (side_str.upper())])
        self.log.printChangedFiles(sorted(list(side_modified)), side_dict, side_prev, "    New", "    Old")
        print(self.log.colourString(getString("%s Moved Files: %s") % (side_str, len(moved)), "HEADER"))
        self.log.append([getString("### %s MOVED FILES ###") % (side_str.upper())])
        self.log.printMovedFiles(moved, side_new, side_missing, "   New: ", "   Old: ")

    def _printAndLogCompareDiffSummary(self, source_only: list, dest_only: list, changed: list, moved: list) -> None:
        # get databases
        source_dict, _, _, _, _, _, _ = self.source.getDicts()
        dest_dict, _, _, _, _, _, _ = self.dest.getDicts()
        # prepare diff messages
        if self.config.noarchive:
            archive_msg = getString("delete")
        else:
            archive_msg = getString("archive")
        if self.config.main_mode == "sync":
            dest_msg = getString("(will be copied to source)")
        elif self.config.main_mode == "backup":
            dest_msg = getString("(will be left as is)")
        elif self.config.main_mode == "mirror":
            dest_msg = getString("(will be %sd)" % (archive_msg))
        if self.config.select_mode == "source":
            change_msg = getString("(%s dest and copy source -> dest)" % (archive_msg))
        elif self.config.select_mode == "dest":
            change_msg = getString("(%s source and copy dest -> source)" % (archive_msg))
        elif self.config.select_mode == "new":
            change_msg = getString("(%s older and copy newer)" % (archive_msg))
        elif self.config.select_mode == "no":
            change_msg = getString("(will be left as is)")
        # print differences
        print(self.log.colourString(getString("Source Only (will be copied to dest): %s") % (len(source_only)), "HEADER"))
        self.log.append([getString("### SOURCE ONLY ###")])
        self.log.printFiles(source_only, source_dict)
        print(self.log.colourString(getString("Destination Only %s: %s") % (dest_msg, len(dest_only)), "HEADER"))
        self.log.append([getString("### DESTINATION ONLY ###")])
        self.log.printFiles(dest_only, dest_dict)
        print(self.log.colourString(getString("Changed Files %s: %s") % (change_msg, len(changed)), "HEADER"))
        self.log.append([getString("### CHANGED FILES ###")])
        self.log.printChangedFiles(changed, source_dict, dest_dict)
        if not self.config.nomoves:
            print(self.log.colourString(getString("Moved Files (will move files on dest to match source): %s") % (len(moved)), "HEADER"))
            self.log.append([getString("### MOVED FILES ###")])
            self.log.printMovedFiles(moved, source_dict, dest_dict)

    def _performBackup(self, source_only: list, dest_only: list, changed: list, moved: list, simulation_msg: str) -> None:
        # get databases
        source_dict, _, _, _, _, _, _ = self.source.getDicts()
        dest_dict, _, _, _, _, _, _ = self.dest.getDicts()
        # perform the backup/mirror/sync
        self.log.append([getString("### START ") + self.config.main_mode.upper() + simulation_msg.upper() + " ###"])
        print(self.log.colourString(getString("Starting ") + self.config.main_mode, "HEADER"))
        if self.config.main_mode == "mirror":
            self.fileman.handleDeletedFiles(self.config.dest, dest_only)
            self.fileman.copyFiles(self.config.source, self.config.dest, source_only, source_only)
            self.fileman.handleMovedFiles(moved)
            self.fileman.handleChangedFiles(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        elif self.config.main_mode == "backup":
            self.fileman.copyFiles(self.config.source, self.config.dest, source_only, source_only)
            self.fileman.handleMovedFiles(moved)
            self.fileman.handleChangedFiles(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        elif self.config.main_mode == "sync":
            self.fileman.copyFiles(self.config.source, self.config.dest, source_only, source_only)
            self.fileman.copyFiles(self.config.dest, self.config.source, dest_only, dest_only)
            self.fileman.handleMovedFiles(moved)
            self.fileman.handleChangedFiles(self.config.source, self.config.dest, source_dict, dest_dict, changed)

    def run(self):
        """Main method, use this to run your job"""
        # dry run confirmation message
        if self.config.dry_run:
            simulation_msg = getString(" dry run")
            print(self.log.colourString(getString("Dry Run"), "HEADER"))
        else:
            simulation_msg = ""
        # init DirInfo and load previous scan data if available
        self.source = DirInfo(self.config.source, self.config.compare_mode, self.config.config_dir,
                              [self.config.archive_dir, self.config.log_dir, self.config.trash_dir],
                              self.gui, self.config.force_posix_path_sep,
                              self.config.filter_include_list, self.config.filter_exclude_list)
        self.dest = DirInfo(self.config.dest, self.config.compare_mode, self.config.config_dir,
                            [self.config.archive_dir, self.config.log_dir, self.config.trash_dir],
                            self.gui, self.config.force_posix_path_sep,
                            self.config.filter_include_list, self.config.filter_exclude_list)
        dest_database_load_success = False
        self.source.loadJson()
        self.dest.loadJson()
        if self.dest.dict_prev != {}:
            dest_database_load_success = True
        # scan directories (also calculates CRC if enabled) (didn't parallelize scans to prevent excess vibration of adjacent consumer grade disks and keep status bars simple)
        self.log.colourPrint(getString("Scanning files on source:\n%s") % (self.config.source), "OKBLUE")
        self.source.scanDir(self.config.stdout_status_bar)
        if self.config.source != self.config.dest:
            self.log.colourPrint(getString("Scanning files on destination:\n%s") % (self.config.dest), "OKBLUE")
            self.dest.scanDir(self.config.stdout_status_bar)
        else:
            self.dest = self.source
        # update logman and fileman to reference the same source and dest
        self.log.source, self.log.dest = self.source, self.dest
        self.fileman.source, self.fileman.dest = self.source, self.dest
        # compare directories (should be relatively fast, all the read operations are done during scan)
        if not self.config.scan_only:
            self.log.colourPrint(getString("Comparing directories..."), "OKBLUE")
            source_only, dest_only, changed, moved = self.source.dirCompare(self.dest, self.config.nomoves)
        # check for database conflicts or corruption
        detected_database_conflicts_or_corruption = self._databaseAndCorruptionCheck(dest_database_load_success)
        if self.config.quit_on_db_conflict and detected_database_conflicts_or_corruption:
            return self.abortRun()
        # print differences between current and previous scans then exit if only scanning
        if self.config.scan_only:
            self._printAndLogScanOnlyDiffSummary("Source", self.source)
            if self.config.source != self.config.dest:
                self._printAndLogScanOnlyDiffSummary("Destination", self.dest)
            self.log.append([getString("### SCAN COMPLETED ###")])
            self.log.writeLog("database.json")
            print(self.log.colourString(getString("Completed!"), "OKGREEN"))
            return 0
        # print differences between source and dest
        self._printAndLogCompareDiffSummary(source_only, dest_only, changed, moved)
        # check for consistency between comparison and database dicts
        try:
            self._checkConsistency(dest_database_load_success, source_only, dest_only, changed, moved)
        except Exception as e:
            self.log.append(["BACKUPY ERROR", str(e)])
            print(e)
            print(self.log.colourString(getString("Error: Inconsistent directory comparison and database checks"), "FAIL"))
            return self.abortRun()
        # exit if directories already match
        if len(source_only) == 0 and len(dest_only) == 0 and len(changed) == 0 and len(moved) == 0:
            print(self.log.colourString(getString("Directories already match, completed!"), "OKGREEN"))
            self.log.append([getString("### NO CHANGES FOUND ###")])
            self.log.writeLog("database.json")
            return 0
        # wait for go ahead
        self.log.writeLog("database.tmp.json")
        if not self.config.noprompt:
            if self.gui:
                go = self.gui_simplePrompt(getString("Scan complete, continue with %s%s?") % (self.config.main_mode, simulation_msg))
            else:
                print(self.log.colourString(getString("Scan complete, continue with %s%s (y/N)?") % (self.config.main_mode, simulation_msg), "OKGREEN"))
                go = input("> ")
            if len(go) == 4 and go.lower() == "skip":
                if not self._skipFileTransfers(source_only, dest_only, changed):
                    return self.abortRun()
            elif len(go) == 0 or go[0].lower() != "y":
                return self.abortRun()
        # backup operations
        self._performBackup(source_only, dest_only, changed, moved, simulation_msg)
        self.log.append([getString("### COMPLETED ###")])
        self.log.writeLog("database.json")
        print(self.log.colourString(getString("Completed!"), "OKGREEN"))
        return 0
