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
import csv
import datetime
import json
import os
import re
import shutil
import sys
import time
import typing
import unicodedata
import zlib


##################
### Main class ###
##################


class BackupManager:
    def __init__(self, args: typing.Union[argparse.Namespace, dict], gui: bool = False):
        """Main class, configure with an argparse namespace or dictionary to create a job then run with .backup()"""
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
        # load config (be careful if using a non-default config_dir!)
        if "load" in args and args["load"] == True:
            self.loadJson()
        # set args that can overwrite loaded config
        if "dry_run" in args and args["dry_run"] == True:
            self.config.dry_run = True
        if "scan_only" in args and args["scan_only"] == True:
            self.config.scan_only = True
        if "compare_mode" in args and args["compare_mode"] is not None:
            self.config.compare_mode = args["compare_mode"]
        # scan only mode
        if self.config.scan_only and (self.config.dest is None or not os.path.isdir(self.config.dest)):
            self.config.dest = self.config.source
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
        if "save" in args and args["save"] == True:
            self.saveJson()
        # gui modifications
        self.terminal_width = shutil.get_terminal_size()[0]
        if self.gui:
            self.config.stdout_status_bar = False
            self.terminal_width = 80
        # debugging/testing
        if "backup_time_override" in args and args["backup_time_override"]:
            self.backup_time = args["backup_time_override"]
        # log settings
        self.log.append([getString("### SETTINGS ###")])
        self.log.append([getString("Time:"), self.backup_time,
                         getString("Version:"), getVersion(),
                         getString("Source DB CRC:"), "0",
                         getString("Dest DB CRC:"), "0",
                         getString("Config:"), str(vars(self.config))])

    ######################################
    ### Saving/loading/logging methods ###
    ######################################

    def saveJson(self) -> None:
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
            print(self.colourString(getString("A config file matching the specified source was not found (case sensitive)"), "FAIL"))
            sys.exit()

    def writeLog(self, db_name: str) -> None:
        if not self.config.nolog:
            # <source|dest>/.backupy/database.json
            if self.config.dry_run:
                db_name = db_name[:-4] + "dryrun.json"
            self.source.saveJson(db_name)
            self.dest.saveJson(db_name)
            self.log[1][5] = self.source.calcCrc(os.path.join(self.source.dir, self.source.config_dir, db_name))
            self.log[1][7] = self.dest.calcCrc(os.path.join(self.dest.dir, self.dest.config_dir, db_name))
            # <source>/.backupy/Logs/log-yymmdd-HHMM.csv
            if self.config.root_alias_log or self.config.force_posix_path_sep:
                for i in range(2, len(self.log)):
                    for j in range(len(self.log[i])):
                        if type(self.log[i][j]) == str:
                            if self.config.root_alias_log:
                                self.log[i][j] = self.log[i][j].replace(self.config.source, getString("<source>"))
                                self.log[i][j] = self.log[i][j].replace(self.config.dest, getString("<dest>"))
                            if self.config.force_posix_path_sep:
                                self.log[i][j] = self.log[i][j].replace(os.path.sep, "/")
            writeCsv(os.path.join(self.config.source, self.config.log_dir, "log-" + self.backup_time + ".csv"), self.log)

    def abortRun(self) -> int:
        self.log.append([getString("### ABORTED ###")])
        self.writeLog("database.aborted.json")
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

    def prettySize(self, size: float) -> str:
        if size > 10**9:
            return "{:<10}".format("%s GB" %(round(size/10**9, 2)))
        elif size > 10**6:
            return "{:<10}".format("%s MB" %(round(size/10**6, 2)))
        elif size > 10**3:
            return "{:<10}".format("%s KB" %(round(size/10**3, 2)))
        else:
            return "{:<10}".format("%s B" %(size))

    def prettyAttr(self, attr: dict) -> str:
        string = "{'size': %s, 'mtime': %s" %(attr["size"], attr["mtime"])
        if "crc" in attr: string += ", 'crc': '%s'" %(attr["crc"])
        if "dir" in attr: string += ", 'dir': %s" %(attr["dir"])
        string += "}"
        return string

    ########################
    ### Printing methods ###
    ########################

    def colourPrint(self, msg: str, colour: str) -> None:
        if self.config.verbose:
            if colour == "NONE":
                print(self.replaceSurrogates(msg))
            else:
                print(self.colourString(msg, colour))

    def printFileInfo(self, header: str, f: str, d: dict, sub_header: str = "", skip_info: bool = False) -> None:
        header, sub_header = getString(header), getString(sub_header)
        if f in d and d[f] is not None:
            self.log.append([header.strip(), sub_header.strip(), f] + [self.prettyAttr(d[f])])
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
            extra_space = " "*min(4, self.terminal_width//5-16)
            s = s + extra_space*2 + self.colourString(sub_header, "OKBLUE") + " "*(8-len(sub_header))
            if not missing:
                s = s + extra_space + self.colourString(getString(" Size: "), "OKBLUE") + self.prettySize(d[f]["size"])
                s = s + extra_space + self.colourString(getString(" Modified: "), "OKBLUE") + time.ctime(d[f]["mtime"])
                if "crc" in d[f]:
                    s = s + extra_space + self.colourString(getString(" Hash: "), "OKBLUE") + d[f]["crc"]
            else:
                s = s + extra_space + self.colourString(getString(" Missing"), "OKBLUE")
        print(s)

    def printFiles(self, l: list, d: dict) -> None:
        for f in l:
            self.printFileInfo("File: ", f, d)

    def printChangedFiles(self, l: list, d1: dict, d2: dict, s1: str = " Source", s2: str = "   Dest") -> None:
        for f in l:
            self.printFileInfo("File: ", f, d1, s1)
            self.printFileInfo("", f, d2, s2)

    def printMovedFiles(self, l: list, d1: dict, d2: dict, h1: str = "Source: ", h2: str = "  Dest: ") -> None:
        for f in l:
            self.printFileInfo(h1, f["source"], d1, skip_info=True)
            self.printFileInfo(h2, f["dest"], d2)

    def printSyncDbConflicts(self, l: list, d1: dict, d2: dict, d1db: dict, d2db: dict) -> None:
        for f in l:
            self.printFileInfo("File: ", f, d1, " Source")
            self.printFileInfo("", f, d1db, "     DB")
            self.printFileInfo("", f, d2, "   Dest")
            self.printFileInfo("", f, d2db, "     DB")

    #############################################################################
    ### File operation methods (only use these methods to perform operations) ###
    #############################################################################

    def removeFile(self, root_path: str, file_relative_path: str) -> None:
        try:
            self.log.append(["Remove:", root_path, file_relative_path])
            self.source.updateDictOnRemove(root_path, file_relative_path, self.dest)
            if not self.config.dry_run:
                path = os.path.join(root_path, file_relative_path)
                if os.path.isdir(path):
                    os.rmdir(path)
                else:
                    os.remove(path)
                if self.config.cleanup_empty_dirs:
                    head = os.path.dirname(path)
                    if len(os.listdir(head)) == 0:
                        os.removedirs(head)
        except Exception as e:
            self.log.append(["REMOVE ERROR", root_path, file_relative_path, str(e)])
            print(e)

    def copyFile(self, source_root: str, dest_root: str, source_file: str, dest_file: str) -> None:
        try:
            self.log.append(["Copy:", source_root, source_file, dest_root, dest_file])
            self.source.updateDictOnCopy(source_root, dest_root, source_file, dest_file, self.dest)
            if not self.config.dry_run:
                source = os.path.join(source_root, source_file)
                dest = os.path.join(dest_root, dest_file)
                if os.path.isdir(source):
                    os.makedirs(dest)
                else:
                    if not os.path.isdir(os.path.dirname(dest)):
                        os.makedirs(os.path.dirname(dest))
                    shutil.copy2(source, dest)
                    if self.config.verify_copy:
                        self.source.verifyCrcOnCopy(source_root, dest_root, source_file, dest_file, self.dest)
        except Exception as e:
            self.log.append(["COPY ERROR", source_root, source_file, dest_root, dest_file, str(e)])
            print(e)

    def moveFile(self, source_root: str, dest_root: str, source_file: str, dest_file: str) -> None:
        try:
            self.log.append(["Move:", source_root, source_file, dest_root, dest_file])
            self.source.updateDictOnMove(source_root, dest_root, source_file, dest_file, self.dest)
            if not self.config.dry_run:
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
            self.log.append(["MOVE ERROR", source_root, source_file, dest_root, dest_file, str(e)])
            print(e)

    ##############################################################################
    ### Batch file operation methods (do not perform file operations directly) ###
    ##############################################################################

    def removeFiles(self, root_path: str, file_relative_paths: list) -> None:
        self.colourPrint(getString("Removing %s unique files from:\n%s") %(len(file_relative_paths), root_path), "OKBLUE")
        for f in file_relative_paths:
            self.removeFile(root_path, f)
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

    def handleDeletedFiles(self, root_path: str, file_relative_paths: list) -> None:
        if self.config.noarchive:
            self.removeFiles(root_path, file_relative_paths)
        else:
            recycle_bin = os.path.join(root_path, self.config.trash_dir, self.backup_time)
            self.moveFiles(root_path, recycle_bin, file_relative_paths, file_relative_paths)

    def handleMovedFiles(self, moved_pairs: list, reverse: bool = False) -> None:
        if not self.config.nomoves:
            # conflicts shouldn't happen since moved is a subset of files from source_only and dest_only
            # depends on source_info.dirCompare(dest_info) otherwise source and dest keys will be reversed
            self.colourPrint(getString("Moving %s files on destination to match source") %(len(moved_pairs)), "OKBLUE")
            for f in moved_pairs:
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

    def archiveFile(self, root_path: str, file_relative_path: str) -> None:
        if not self.config.noarchive:
            archive_path = os.path.join(root_path, self.config.archive_dir, self.backup_time)
            self.moveFile(root_path, archive_path, file_relative_path, file_relative_path)

    def handleChangedFiles(self, source_root: str, dest_root: str, source_dict: dict, dest_dict: dict, changed: list) -> None:
        self.colourPrint(getString("Handling %s file changes per selection mode") %(len(changed)), "OKBLUE")
        copy_status = StatusBar("Copying", len(changed), self.config.stdout_status_bar, gui=self.gui)
        for frp in changed:
            copy_status.update(frp)
            if self.config.select_mode == "source":
                self.archiveFile(dest_root, frp)
                self.copyFile(source_root, dest_root, frp, frp)
            elif self.config.select_mode == "dest":
                self.archiveFile(source_root, frp)
                self.copyFile(dest_root, source_root, frp, frp)
            elif self.config.select_mode == "new":
                if source_dict[frp]["mtime"] > dest_dict[frp]["mtime"]:
                    self.archiveFile(dest_root, frp)
                    self.copyFile(source_root, dest_root, frp, frp)
                else:
                    self.archiveFile(source_root, frp)
                    self.copyFile(dest_root, source_root, frp, frp)
            else:
                break
        copy_status.endProgress()

    #########################################
    ### Helper functions used by backup() ###
    #########################################

    def _databaseAndCorruptionCheck(self, dest_database_load_success: bool) -> bool:
        # get databases
        source_dict, source_prev, source_new, source_modified, source_missing, source_crc_errors = self.source.getDicts()
        dest_dict, dest_prev, dest_new, dest_modified, dest_missing, dest_crc_errors = self.dest.getDicts()
        # print database conflicts, including both collisions from files being modified independently on both sides and unexpected missing files
        # note: this only notifies the user so they can intervene, it does not handle them in any special way, treating them as regular file changes
        # it can also be triggered by time zone or dst changes, lower file system mod time precision, and corruption if using CRCs (handled next)
        abort_run = False
        if dest_database_load_success and self.config.source != self.config.dest:
            self.log.append([getString("### DATABASE CONFLICTS ###")])
            if self.config.main_mode == "sync":
                sync_conflicts = sorted(list(set(source_modified) & set(dest_modified))) # modified on both sides
                sync_conflicts += sorted(list(set(source_missing) | set(dest_missing))) # deleted from either or both sides
                sync_conflicts += sorted(list(set(source_new) & set(dest_new))) # new on both sides
                # sync_conflicts += sorted(list(filter(lambda f: source_new[f] != dest_new[f], set(source_new) & set(dest_new)))) # new and different on both sides
                if len(sync_conflicts) >= 1:
                    print(self.colourString(getString("WARNING: found files modified in both source and destination since last scan"), "WARNING"))
                    abort_run = True
                print(self.colourString(getString("Sync Database Conflicts: %s") %(len(sync_conflicts)), "HEADER"))
                self.printSyncDbConflicts(sync_conflicts, source_dict, dest_dict, source_prev, dest_prev)
            else:
                dest_conflicts = sorted(list(set(dest_modified)))
                dest_conflicts += sorted(list(set(dest_missing)))
                dest_conflicts += sorted(list(set(dest_new)))
                if len(dest_conflicts) >= 1:
                    print(self.colourString(getString("WARNING: found files modified in the destination since last scan"), "WARNING"))
                    abort_run = True
                print(self.colourString(getString("Destination Database Conflicts: %s") %(len(dest_conflicts)), "HEADER"))
                self.printChangedFiles(dest_conflicts, dest_dict, dest_prev, "   Dest", "     DB")
        # print database conflicts concerning CRCs if available, as well as CRC conflicts between source and dest if attributes otherwise match
        if len(source_crc_errors) > 0 or len(dest_crc_errors) > 0:
            self.log.append([getString("### CRC ERRORS DETECTED ###")])
            print(self.colourString(getString("WARNING: found non matching CRC values, possible corruption detected"), "WARNING"))
            abort_run = True
            if self.config.compare_mode == "crc":
                crc_errors_detected = sorted(list(set(source_crc_errors) | set(dest_crc_errors)))
                print(self.colourString(getString("CRC Errors Detected: %s") %(len(crc_errors_detected)), "HEADER"))
                self.printSyncDbConflicts(crc_errors_detected, source_dict, dest_dict, source_prev, dest_prev)
            elif self.config.compare_mode == "attr+":
                if set(source_crc_errors) != set(dest_crc_errors):
                    raise Exception("Inconsistent CRC error detection between source and dest")
                print(self.colourString(getString("CRC Errors Detected: %s") %(len(source_crc_errors)), "HEADER"))
                self.printChangedFiles(sorted(list(source_crc_errors)), source_crc_errors, dest_crc_errors)
        return abort_run

    def _printAndLogScanOnlyDiffSummary(self, side_str: str, side_info: "DirInfo") -> None:
        # get databases
        side_dict, side_prev, side_new, side_modified, side_missing, _ = side_info.getDicts()
        compare_func = lambda f1, f2: side_new[f1] == side_missing[f2]
        list_new, list_missing = sorted(list(side_new)), sorted(list(side_missing))
        moved = side_info.getMovedAndUpdateLists(list_new, list_missing, side_new, side_missing, compare_func)
        # print differences
        print(self.colourString(getString("%s New Files: %s") %(side_str, len(list_new)), "HEADER"))
        self.log.append([getString("### %s NEW FILES ###") %(side_str.upper())])
        self.printFiles(list_new, side_dict)
        print(self.colourString(getString("%s Missing Files: %s") %(side_str, len(list_missing)), "HEADER"))
        self.log.append([getString("### %s MISSING FILES ###") %(side_str.upper())])
        self.printFiles(list_missing, side_prev)
        print(self.colourString(getString("%s Changed Files: %s") %(side_str, len(side_modified)), "HEADER"))
        self.log.append([getString("### %s CHANGED FILES ###") %(side_str.upper())])
        self.printChangedFiles(sorted(list(side_modified)), side_dict, side_prev, "    New", "    Old")
        print(self.colourString(getString("%s Moved Files: %s") %(side_str, len(moved)), "HEADER"))
        self.log.append([getString("### %s MOVED FILES ###") %(side_str.upper())])
        self.printMovedFiles(moved, side_new, side_missing, "   New: ", "   Old: ")

    def _printAndLogCompareDiffSummary(self, source_only: list, dest_only: list, changed: list, moved: list) -> None:
        # get databases
        source_dict, _, _, _, _, _ = self.source.getDicts()
        dest_dict, _, _, _, _, _ = self.dest.getDicts()
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
            dest_msg = getString("(will be %sd)" %(archive_msg))
        if self.config.select_mode == "source":
            change_msg = getString("(%s dest and copy source -> dest)" %(archive_msg))
        elif self.config.select_mode == "dest":
            change_msg = getString("(%s source and copy dest -> source)" %(archive_msg))
        elif self.config.select_mode == "new":
            change_msg = getString("(%s older and copy newer)" %(archive_msg))
        elif self.config.select_mode == "no":
            change_msg = getString("(will be left as is)")
        # print differences
        print(self.colourString(getString("Source Only (will be copied to dest): %s") %(len(source_only)), "HEADER"))
        self.log.append([getString("### SOURCE ONLY ###")])
        self.printFiles(source_only, source_dict)
        print(self.colourString(getString("Destination Only %s: %s") %(dest_msg, len(dest_only)), "HEADER"))
        self.log.append([getString("### DESTINATION ONLY ###")])
        self.printFiles(dest_only, dest_dict)
        print(self.colourString(getString("Changed Files %s: %s") %(change_msg, len(changed)), "HEADER"))
        self.log.append([getString("### CHANGED FILES ###")])
        self.printChangedFiles(changed, source_dict, dest_dict)
        if not self.config.nomoves:
            print(self.colourString(getString("Moved Files (will move files on dest to match source): %s") %(len(moved)), "HEADER"))
            self.log.append([getString("### MOVED FILES ###")])
            self.printMovedFiles(moved, source_dict, dest_dict)

    def _performBackup(self, source_only: list, dest_only: list, changed: list, moved: list, simulation_msg: str) -> None:
        # get databases
        source_dict, _, _, _, _, _ = self.source.getDicts()
        dest_dict, _, _, _, _, _ = self.dest.getDicts()
        # perform the backup/mirror/sync
        self.log.append([getString("### START ") + self.config.main_mode.upper() + simulation_msg.upper() + " ###"])
        print(self.colourString(getString("Starting ") + self.config.main_mode, "HEADER"))
        if self.config.main_mode == "mirror":
            self.handleDeletedFiles(self.config.dest, dest_only)
            self.copyFiles(self.config.source, self.config.dest, source_only, source_only)
            self.handleMovedFiles(moved)
            self.handleChangedFiles(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        elif self.config.main_mode == "backup":
            self.copyFiles(self.config.source, self.config.dest, source_only, source_only)
            self.handleMovedFiles(moved)
            self.handleChangedFiles(self.config.source, self.config.dest, source_dict, dest_dict, changed)
        elif self.config.main_mode == "sync":
            self.copyFiles(self.config.source, self.config.dest, source_only, source_only)
            self.copyFiles(self.config.dest, self.config.source, dest_only, dest_only)
            self.handleMovedFiles(moved)
            self.handleChangedFiles(self.config.source, self.config.dest, source_dict, dest_dict, changed)

    ######################################
    ### Main backup/mirror/sync method ###
    ######################################

    def backup(self):
        """Main method, use this to run your job"""
        # dry run confirmation message
        if self.config.dry_run:
            simulation_msg = getString(" dry run")
            print(self.colourString(getString("Dry Run"), "HEADER"))
        else:
            simulation_msg = ""
        # init dir scanning and load previous scan data if available
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
        self.colourPrint(getString("Scanning files on source:\n%s") %(self.config.source), "OKBLUE")
        self.source.scanDir(self.config.stdout_status_bar)
        if self.config.source != self.config.dest:
            self.colourPrint(getString("Scanning files on destination:\n%s") %(self.config.dest), "OKBLUE")
            self.dest.scanDir(self.config.stdout_status_bar)
        else:
            self.dest = self.source
        # compare directories (should be relatively fast, all the read operations are done during scan)
        if not self.config.scan_only:
            self.colourPrint(getString("Comparing directories..."), "OKBLUE")
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
            self.writeLog("database.json")
            print(self.colourString(getString("Completed!"), "OKGREEN"))
            return 0
        # print differences between source and dest
        self._printAndLogCompareDiffSummary(source_only, dest_only, changed, moved)
        # exit if directories already match
        if len(source_only) == 0 and len(dest_only) == 0 and len(changed) == 0 and len(moved) == 0:
            print(self.colourString(getString("Directories already match, completed!"), "OKGREEN"))
            self.log.append([getString("### NO CHANGES FOUND ###")])
            self.writeLog("database.json")
            return 0
        # wait for go ahead
        self.writeLog("database.tmp.json")
        if not self.config.noprompt:
            if self.gui:
                go = self.gui_simplePrompt(getString("Scan complete, continue with %s%s?") %(self.config.main_mode, simulation_msg))
            else:
                print(self.colourString(getString("Scan complete, continue with %s%s (y/N)?") %(self.config.main_mode, simulation_msg), "OKGREEN"))
                go = input("> ")
            if len(go) == 0 or go[0].lower() != "y":
                return self.abortRun()
        # backup operations
        self._performBackup(source_only, dest_only, changed, moved, simulation_msg)
        self.log.append([getString("### COMPLETED ###")])
        self.writeLog("database.json")
        print(self.colourString(getString("Completed!"), "OKGREEN"))
        return 0
