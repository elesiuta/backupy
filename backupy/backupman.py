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
from .fileman import FileManager
from .filescanner import FileScanner
from .logman import LogManager
from .transferlists import TransferLists
from .utils import (
    getString,
    getVersion,
    simplePrompt,
    readJson,
    writeJson,
    testConsistency
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
        # init log manager
        self.log = LogManager(self.backup_time, gui)
        # init config
        if type(args) != dict:
            args = vars(args)
        self.config = ConfigObject(args)
        # load config (be careful if using a non-default config_dir!)
        if "load" in args and args["load"] is True:
            self.loadConfig()
        # update log manager to ensure it references the same config (don't create a new ConfigObject after this point)
        self.log.config = self.config
        # set args that can overwrite loaded config (note: all other args are silently replaced with loaded configuration)
        if "dry_run" in args and args["dry_run"] is True:
            self.config.dry_run = True
        if "scan_only" in args and args["scan_only"] is True:
            self.config.scan_only = True
        if "compare_mode" in args and args["compare_mode"] is not None and not gui:
            self.config.compare_mode = args["compare_mode"]
        # scan only mode
        if self.config.scan_only and (self.config.dest is None or not os.path.isdir(self.config.dest)):
            self.config.dest = self.config.source
        # cold storage mode
        if self.config.use_cold_storage:
            self.config.write_database_x2 = True
        # check source & dest
        if not os.path.isdir(self.config.source):
            print(self.log.colourString(getString("Unable to access source directory: ") + self.config.source, "R"))
            print(self.log.colourString(getString("Check folder permissions and if the directory exists."), "R"))
            sys.exit(1)
        if self.config.dest is None:
            print(self.log.colourString(getString("Destination directory not provided or config failed to load"), "R"))
            sys.exit(1)
        try:
            for access_test in [self.config.source, self.config.dest]:
                if os.path.isdir(access_test):
                    _ = os.listdir(access_test)
                else:
                    os.makedirs(access_test)
        except Exception as e:
            self.log.colourPrint("%s: %s for %s" % (type(e).__name__, str(e.args), access_test), "R")
            self.log.colourPrint(getString("BackuPy will now exit without taking any action."), "R")
            sys.exit(1)
        self.config.source = os.path.abspath(self.config.source)
        self.config.dest = os.path.abspath(self.config.dest)
        # save config (still works with --load, so you can cleanup a messy json file from an old version this way)
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
        # lock config from future changes (makes code safer and easier to verify)
        self.config.locked = True

    def saveConfig(self) -> None:
        writeJson(os.path.join(self.config.source, self.config.config_dir, "config.json"), vars(self.config))
        print(self.log.colourString(getString("Config saved"), "G"))
        sys.exit(0)

    def loadConfig(self) -> None:
        # will probably raise an exception and crash (safely) if the configuration is not valid json
        current_source = self.config.source
        config_dir = os.path.abspath(os.path.join(self.config.source, self.config.config_dir, "config.json"))
        config = readJson(config_dir)
        self.config = ConfigObject(config)
        self.log.config = self.config
        print(self.log.colourString(getString("Loaded config from:") + "\n" + config_dir, "G"))
        if self.config.source is None or os.path.abspath(current_source) != os.path.abspath(self.config.source):
            print(self.log.colourString(getString("A config file matching the specified source was not found (case sensitive)"), "R"))
            sys.exit(1)

    def abortRun(self) -> int:
        self.log.append([getString("### ABORTED ###")])
        self.log.writeLog("database.aborted.json")
        print(self.log.colourString(getString("Run aborted"), "Y"))
        return 1

    def _databaseAndCorruptionCheck(self, dest_database_load_success: bool) -> bool:
        # get databases
        source_dict, source_prev = self.source.getDicts()
        source_new, source_modified, source_missing, source_crc_errors, _, _ = self.source.getSets()
        dest_dict, dest_prev = self.dest.getDicts()
        dest_new, dest_modified, dest_missing, dest_crc_errors, _, _ = self.dest.getSets()
        # print database conflicts, including both collisions from files being modified independently on both sides and unexpected missing files
        # note: this only notifies the user so they can intervene, it does not handle them in any special way, treating them as regular file changes
        # it can also be triggered by time zone or dst changes, lower file system mod time precision, and corruption if using CRCs (handled next)
        detection_flag = False
        if dest_database_load_success and self.config.source != self.config.dest:
            self.log.append([getString("### DATABASE CONFLICTS ###")], ["Section"])
            if self.config.main_mode == "sync":
                sync_conflicts = sorted(list(source_modified & dest_modified))  # modified on both sides
                sync_conflicts += sorted(list(source_new & dest_new))  # new on both sides
                sync_conflicts = sorted(list(filter(lambda f: not self.source.fileMatch(f, f, dest_dict, set(), True), sync_conflicts)))  # don't already match
                if len(sync_conflicts) >= 1:
                    print(self.log.colourString(getString("WARNING: found files modified in both source and destination since last scan"), "Y"))
                    detection_flag = True
                print(self.log.colourString(getString("Sync Database Conflicts: %s") % (len(sync_conflicts)), "V"))
                self.log.printSyncDbConflicts(sync_conflicts, source_dict, dest_dict, source_prev, dest_prev)
            else:
                dest_conflicts = sorted(list(dest_modified))
                dest_conflicts += sorted(list(dest_missing))
                dest_conflicts += sorted(list(dest_new))
                if len(dest_conflicts) >= 1:
                    print(self.log.colourString(getString("WARNING: found files modified in the destination since last scan"), "Y"))
                    detection_flag = True
                print(self.log.colourString(getString("Destination Database Conflicts: %s") % (len(dest_conflicts)), "V"))
                self.log.printChangedFiles(dest_conflicts, dest_dict, dest_prev, "   Dest", "     DB")
        # print database conflicts concerning CRCs if available, as well as CRC conflicts between source and dest if attributes otherwise match
        crc_errors_detected = []
        if len(source_crc_errors) > 0 or len(dest_crc_errors) > 0:
            self.log.append([getString("### CRC ERRORS DETECTED ###")], ["Section"])
            print(self.log.colourString(getString("WARNING: found non matching CRC values, possible corruption detected"), "Y"))
            detection_flag = True
            crc_errors_detected = sorted(list(source_crc_errors | dest_crc_errors))
            print(self.log.colourString(getString("CRC Errors Detected: %s") % (len(crc_errors_detected)), "V"))
            if self.config.source != self.config.dest:
                self.log.printSyncDbConflicts(crc_errors_detected, source_dict, dest_dict, source_prev, dest_prev)
            else:
                self.log.printChangedFiles(crc_errors_detected, source_dict, source_prev, " Source", "     DB")
        # show curses tree
        if detection_flag:
            while not self.config.noprompt:
                print(self.log.colourString(getString("Show files as tree with curses (y/n)?"), "G"))
                response = simplePrompt(["y", "n"])
                if response == "n":
                    break
                try:
                    from .treedisplay import dest_conflicts_tree, sync_conflicts_tree
                    if dest_database_load_success and self.config.source != self.config.dest:
                        if self.config.main_mode == "sync":
                            sync_conflicts_tree(sync_conflicts, crc_errors_detected)
                        else:
                            dest_conflicts_tree(dest_new, dest_modified, dest_missing, crc_errors_detected)
                    else:
                        sync_conflicts_tree([], crc_errors_detected)
                except Exception:
                    print(self.log.colourString(getString("Curses Error"), "R"))
        return detection_flag

    def _printAndLogScanOnlyDiffSummary(self, side_str: str, side_info: FileScanner) -> None:
        # get databases
        side_dict, side_prev = side_info.getDicts()
        side_new, side_modified, side_missing, side_crc_errors, side_dirs, side_unmodified = side_info.getSets()
        self_compare = side_info.compareDb(side_prev, set(), detect_moves=True, exact_time=False, ignore_empty_dirs=True)
        list_new, list_missing, list_modified, moved = self_compare["self_only"], self_compare["other_only"], self_compare["changed"], self_compare["moved"]
        # print differences
        sum_size = self.log.prettySize(sum(side_dict[f]["size"] for f in list_new)).strip()
        print(self.log.colourString(getString("%s New Files: %s (%s)") % (side_str, len(list_new), sum_size), "V"))
        self.log.append([getString("### %s NEW FILES ###") % (side_str.upper())], ["Section"])
        self.log.printFiles(list_new, side_dict)
        sum_size = self.log.prettySize(sum(side_prev[f]["size"] for f in list_missing)).strip()
        print(self.log.colourString(getString("%s Missing Files: %s (%s)") % (side_str, len(list_missing), sum_size), "V"))
        self.log.append([getString("### %s MISSING FILES ###") % (side_str.upper())], ["Section"])
        self.log.printFiles(list_missing, side_prev)
        sum_size = self.log.prettySize(sum(abs(side_dict[f]["size"] - side_prev[f]["size"]) for f in list_modified)).strip()
        print(self.log.colourString(getString("%s Changed Files: %s (%s)") % (side_str, len(list_modified), sum_size), "V"))
        self.log.append([getString("### %s CHANGED FILES ###") % (side_str.upper())], ["Section"])
        self.log.printChangedFiles(list_modified, side_dict, side_prev, "    New", "    Old")
        sum_size = self.log.prettySize(sum(side_dict[f["source"]]["size"] for f in moved)).strip()
        print(self.log.colourString(getString("%s Moved Files: %s (%s)") % (side_str, len(moved), sum_size), "V"))
        self.log.append([getString("### %s MOVED FILES ###") % (side_str.upper())], ["Section"])
        self.log.printMovedFiles(moved, side_dict, side_prev, "   New: ", "   Old: ")
        # show curses tree
        if list_new or list_missing or list_modified or moved:
            while not self.config.noprompt:
                print(self.log.colourString(getString("Show files as tree with curses (y/n)?"), "G"))
                response = simplePrompt(["y", "n"])
                if response == "n":
                    break
                try:
                    from .treedisplay import scan_only_tree
                    scan_only_tree(side_str, list_new, list_missing, list_modified, moved)
                except Exception:
                    print(self.log.colourString(getString("Curses Error"), "R"))

    def _printAndLogCompareDiffSummary(self, transfer_lists: TransferLists) -> None:
        # get lists and databases
        source_only, dest_only, changed, moved, source_deleted, dest_deleted = transfer_lists.getLists()
        source_dict, _ = self.source.getDicts()
        dest_dict, _ = self.dest.getDicts()
        # prepare diff messages
        if self.config.noarchive:
            archive_msg = getString("delete")
        else:
            archive_msg = getString("archive")
        if self.config.main_mode == "sync":
            dest_msg = getString("(will be copied to source)")
            move_msg = getString("(will move other file to match)")
        elif self.config.main_mode == "backup":
            dest_msg = getString("(will be left as is)")
            move_msg = getString("(will move files on dest to match source)")
        elif self.config.main_mode == "mirror":
            dest_msg = getString("(will be %sd)" % (archive_msg))
            move_msg = getString("(will move files on dest to match source)")
        if self.config.select_mode == "source":
            change_msg = getString("(%s dest and copy source -> dest)" % (archive_msg))
        elif self.config.select_mode == "dest":
            change_msg = getString("(%s source and copy dest -> source)" % (archive_msg))
        elif self.config.select_mode == "new":
            change_msg = getString("(%s older and copy newer)" % (archive_msg))
        elif self.config.select_mode == "no":
            change_msg = getString("(will be left as is)")
        # print differences
        sum_size = self.log.prettySize(sum(source_dict[f]["size"] for f in source_only)).strip()
        print(self.log.colourString(getString("Source Only (will be copied to dest): %s (%s)") % (len(source_only), sum_size), "V"))
        self.log.append([getString("### SOURCE ONLY ###")], ["Section"])
        self.log.printFiles(source_only, source_dict)
        sum_size = self.log.prettySize(sum(dest_dict[f]["size"] for f in dest_only)).strip()
        print(self.log.colourString(getString("Destination Only %s: %s (%s)") % (dest_msg, len(dest_only), sum_size), "V"))
        self.log.append([getString("### DESTINATION ONLY ###")], ["Section"])
        self.log.printFiles(dest_only, dest_dict)
        sum_size = self.log.prettySize(sum(abs(source_dict[f]["size"] - dest_dict[f]["size"]) for f in changed)).strip()
        print(self.log.colourString(getString("Changed Files %s: %s (%s)") % (change_msg, len(changed), sum_size), "V"))
        self.log.append([getString("### CHANGED FILES ###")], ["Section"])
        self.log.printChangedFiles(changed, source_dict, dest_dict)
        if not self.config.nomoves:
            sum_size = self.log.prettySize(sum(source_dict[f["source"]]["size"] for f in moved)).strip()
            print(self.log.colourString(getString("Moved Files %s: %s (%s)") % (move_msg, len(moved), sum_size), "V"))
            self.log.append([getString("### MOVED FILES ###")], ["Section"])
            self.log.printMovedFiles(moved, source_dict, dest_dict)
        if self.config.main_mode == "sync" and self.config.sync_propagate_deletions:
            sum_size = self.log.prettySize(sum(dest_dict[f]["size"] for f in source_deleted)).strip()
            print(self.log.colourString(getString("Deleted from source (will %s on dest): %s (%s)") % (archive_msg, len(source_deleted), sum_size), "V"))
            self.log.append([getString("### DELETED FROM SOURCE ###")], ["Section"])
            self.log.printFiles(source_deleted, dest_dict)
            sum_size = self.log.prettySize(sum(source_dict[f]["size"] for f in dest_deleted)).strip()
            print(self.log.colourString(getString("Deleted from dest (will %s on source): %s (%s)") % (archive_msg, len(dest_deleted), sum_size), "V"))
            self.log.append([getString("### DELETED FROM DESTINATION ###")], ["Section"])
            self.log.printFiles(dest_deleted, source_dict)

    def _performBackup(self, transfer_lists: TransferLists, simulation_msg: str) -> None:
        # get lists and databases
        source_only, dest_only, changed, moved, source_deleted, dest_deleted = transfer_lists.getLists()
        source_dict, _ = self.source.getDicts()
        dest_dict, _ = self.dest.getDicts()
        # init file manager
        fileman = FileManager(self.config, self.source, self.dest, self.log, self.backup_time, self.gui)
        # perform the backup/mirror/sync
        self.log.append([getString("### START ") + self.config.main_mode.upper() + simulation_msg.upper() + " ###"])
        print(self.log.colourString(getString("Starting ") + self.config.main_mode, "V"))
        if self.config.main_mode == "mirror":
            fileman.handleDeletedFiles(self.config.dest, dest_only)
            fileman.copyFiles(self.config.source, self.config.dest, source_only, source_only)
            fileman.handleMovedFiles(moved)
            fileman.handleChangedFiles(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        elif self.config.main_mode == "backup":
            fileman.copyFiles(self.config.source, self.config.dest, source_only, source_only)
            fileman.handleMovedFiles(moved)
            fileman.handleChangedFiles(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        elif self.config.main_mode == "sync":
            fileman.handleDeletedFiles(self.config.source, dest_deleted)
            fileman.handleDeletedFiles(self.config.dest, source_deleted)
            fileman.copyFiles(self.config.source, self.config.dest, source_only, source_only)
            fileman.copyFiles(self.config.dest, self.config.source, dest_only, dest_only)
            fileman.handleMovedFiles(moved)
            fileman.handleChangedFiles(self.config.source, self.config.dest, source_dict, dest_dict, changed)

    def run(self) -> int:
        """Main method, use this to run your job"""
        # dry run confirmation message
        if self.config.dry_run:
            simulation_msg = getString(" dry run")
            print(self.log.colourString(getString("Dry Run"), "V"))
        else:
            simulation_msg = ""
        # init FileScanner and load previous scan data if available
        self.source = FileScanner(self.config.source, self.config.source_unique_id,
                              self.config.dest, self.config, self.gui)
        self.dest = FileScanner(self.config.dest, self.config.dest_unique_id,
                            self.config.source, self.config, self.gui)
        dest_database_load_success = False
        self.source.loadDatabase()
        self.dest.loadDatabase(self.config.use_cold_storage)
        if self.dest.dict_prev != {}:
            dest_database_load_success = True
        # scan directories (also calculates CRC if enabled) (didn't parallelize scans to prevent excess vibration of adjacent consumer grade disks and keep status bars simple)
        try:
            self.log.colourPrint(getString("Scanning files on source:\n%s") % (self.config.source), "B")
            self.source.scanDir(self.config.stdout_status_bar)
            if not self.config.use_cold_storage:
                if self.config.source != self.config.dest:
                    self.log.colourPrint(getString("Scanning files on destination:\n%s") % (self.config.dest), "B")
                    self.dest.scanDir(self.config.stdout_status_bar)
                else:
                    self.dest = self.source
        except Exception as e:
            self.log.colourPrint(getString("Error encountered during scan: ") + str(e.args[0]), "R")
            self.log.colourPrint(getString("BackuPy will now exit without taking any action."), "R")
            return 1
        # update log manager to reference the same source and dest
        self.log.source, self.log.dest = self.source, self.dest
        # compare directories (should be relatively fast, all the read operations are done during scan)
        if not self.config.scan_only:
            self.log.colourPrint(getString("Comparing directories..."), "B")
            transfer_lists = TransferLists(self.source.compareOtherScanner(self.dest, self.config.nomoves))
            if self.config.main_mode == "sync":
                transfer_lists.updateSyncMovedDirection(self.dest)
                if self.config.sync_propagate_deletions:
                    transfer_lists.propagateSyncDeletions(self.source, self.dest)
            transfer_lists.freeze()
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
            print(self.log.colourString(getString("Completed!"), "G"))
            return 0
        # print differences between source and dest
        self._printAndLogCompareDiffSummary(transfer_lists)
        # consistency checks used for testing and debugging
        if self.backup_time == "000000-0000":
            testConsistency(self.source.getDicts(), self.source.getSets(),
                            self.dest.getDicts(), self.dest.getSets(),
                            transfer_lists.getSets(),
                            self.source.compareDb(self.source.dict_prev, set(), False, False, True),
                            self.dest.compareDb(self.dest.dict_prev, set(), False, False, True),
                            self.source.compareDb(self.source.dict_prev, set(), True, False, True),
                            self.dest.compareDb(self.dest.dict_prev, set(), True, False, True))
        # exit if directories already match
        if transfer_lists.isEmpty():
            print(self.log.colourString(getString("Directories already match, completed!"), "G"))
            self.log.append([getString("### NO CHANGES FOUND ###")])
            self.log.writeLog("database.json")
            return 0
        # wait for go ahead
        self.log.writeLog("database.tmp.json")
        while not self.config.noprompt:
            if self.gui:
                go = self.gui_simplePrompt(getString("Scan complete, continue with %s%s?") % (self.config.main_mode, simulation_msg))
            else:
                print(self.log.colourString(getString("Scan complete, continue with %s%s (y/n/skip/curses)?") % (self.config.main_mode, simulation_msg), "G"))
                go = simplePrompt(["y", "n", "skip", "curses"])
            if go == "skip":
                if not transfer_lists.skipFileTransfers(self.log):
                    return self.abortRun()
            elif go == "curses":
                try:
                    from .treedisplay import transfer_lists_tree
                    transfer_lists_tree(transfer_lists.getLists())
                except Exception:
                    print(self.log.colourString(getString("Curses Error"), "R"))
            elif go == "n":
                return self.abortRun()
            elif go == "y":
                break
        # backup operations
        self._performBackup(transfer_lists, simulation_msg)
        self.log.append([getString("### COMPLETED ###")])
        self.log.writeLog("database.json")
        print(self.log.colourString(getString("Completed!"), "G"))
        return 0
