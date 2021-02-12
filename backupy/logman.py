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
import shutil
import time

from .config import ConfigObject
from .filescanner import FileScanner
from .utils import (
    getString,
    writeCsv,
)


class LogManager:
    def __init__(self, backup_time: int, gui: bool):
        """Provides methods for log formatting and pretty printing (used by BackupManager)"""
        # init variables
        self._log = []
        self._log_columns = []
        self._log_row_split = False
        self.backup_time = backup_time
        self.gui = gui
        self.terminal_width = shutil.get_terminal_size()[0]
        # gui modifications
        if self.gui:
            from .gui import colourize
            self.gui_colourize = colourize
            self.terminal_width = 80
        # init attributes for linting (replaced by BackupManager to reference the same object)
        self.config = ConfigObject
        self.source = FileScanner
        self.dest = FileScanner

    def append(self, entry: list, columns: list = [], row_split: bool = True) -> None:
        # entry to appear in log, label columns for summary, row_split for a new file
        # columns corresponds to the column names of each item in entry or an empty string to omit from summary
        # columns should be an empty list if this entry should be omitted entirely from summary
        # len(columns) should be >= len(entry) or an empty list
        self._log.append(entry)
        if columns:
            self._log_columns.append(columns + [row_split or self._log_row_split])
            self._log_row_split = False
        else:
            self._log_columns.append([])

    def appendNewRowFlag(self) -> None:
        self._log_row_split = True

    def convertLog(self) -> list:
        # convert existing log into log summary
        # combines multiple log entries into a single row
        # each row contains all relevant info of a single file across source, destination and databases on both sides
        columns = ["Section",
                   "Header", "Subheader", "Path", "Size", "Modified", "Hash",
                   "Header", "Subheader", "Path", "Size", "Modified", "Hash",
                   "Header", "Subheader", "Path", "Size", "Modified", "Hash",
                   "Header", "Subheader", "Path", "Size", "Modified", "Hash"]
        log_csv = [columns]
        new_section = False
        for i in range(len(self._log)):
            if self._log_columns[i]:
                if self._log_columns[i][-1] and not new_section:
                    # create new row based on last value of log_columns (unless a new section was just started)
                    log_csv.append([""]*len(columns))
                    entry_number = -1
                if self._log_columns[i][0] == "Section":
                    # fill in the label for the new section
                    log_csv[-1][0] = self._log[i][0].strip("# ")
                    new_section = True
                    entry_number = -1
                else:
                    new_entry = True
                    for j in range(len(self._log[i])):
                        # fill in row with items from entries under the correct column
                        if self._log_columns[i][j]:
                            if new_entry:
                                entry_number += 1
                                new_entry = False
                                new_section = False
                            entry_offset = columns.index(self._log_columns[i][j])
                            log_csv[-1][entry_offset + entry_number*6] = self._log[i][j]
                    if not log_csv[-1][0]:
                        # copy the section from the above row if missing
                        log_csv[-1][0] = log_csv[-2][0]
        if all(entry == "" for entry in log_csv[-1][1:]):
            _ = log_csv.pop(-1)
        return log_csv

    def writeLog(self, db_name: str) -> None:
        if not self.config.nolog:
            # <source|dest>/.backupy/database.json
            if self.config.dry_run:
                db_name = db_name[:-4] + "dryrun.json"
            self.source.saveDatabase(db_name)
            self.dest.saveDatabase(db_name)
            self._log[1][5] = self.source.calcCrc(os.path.join(self.source.dir, self.source.config_dir, db_name))
            self._log[1][7] = self.dest.calcCrc(os.path.join(self.dest.dir, self.dest.config_dir, db_name))
            # <source>/.backupy/Logs/log-yymmdd-HHMM.csv
            if self.config.root_alias_log or self.config.force_posix_path_sep:
                for i in range(2, len(self._log)):
                    for j in range(len(self._log[i])):
                        if type(self._log[i][j]) == str:
                            if self.config.root_alias_log:
                                self._log[i][j] = self._log[i][j].replace(self.config.source, getString("<source>"))
                                self._log[i][j] = self._log[i][j].replace(self.config.dest, getString("<dest>"))
                            if self.config.force_posix_path_sep:
                                self._log[i][j] = self._log[i][j].replace(os.path.sep, "/")
            writeCsv(os.path.join(self.config.source, self.config.log_dir, "log-" + self.backup_time + ".csv"), self._log)
            if self.config.write_log_dest:
                writeCsv(os.path.join(self.config.dest, self.config.log_dir, "log-" + self.backup_time + "-dest.csv"), self._log)
            if self.config.write_log_summary:
                writeCsv(os.path.join(self.config.source, self.config.log_dir, "log-" + self.backup_time + "-plus.csv"), self.convertLog())

    def replaceSurrogates(self, string: str) -> str:
        return string.encode("utf-8", "surrogateescape").decode("utf-8", "replace")

    def colourString(self, string: str, colour: str) -> str:
        string = self.replaceSurrogates(string)
        if self.gui:
            return self.gui_colourize(string, colour)
        elif self.config.nocolour:
            return string
        colours = {
            "R": "\033[91m",
            "G": "\033[92m",
            "Y": "\033[93m",
            "B": "\033[94m",
            "V": "\033[95m"
        }
        return colours[colour] + string + "\033[0m"

    def prettySize(self, size: float) -> str:
        if size > 10**9:
            return "{:<10}".format("%s GB" % (round(size/10**9, 2)))
        elif size > 10**6:
            return "{:<10}".format("%s MB" % (round(size/10**6, 2)))
        elif size > 10**3:
            return "{:<10}".format("%s kB" % (round(size/10**3, 2)))
        else:
            return "{:<10}".format("%s B" % (size))

    def prettyAttr(self, attr: dict) -> list:
        attr_list = []
        attr_list.append(self.prettySize(attr["size"]).strip())
        attr_list.append(time.ctime(attr["mtime"]))
        if "crc" in attr:
            attr_list.append(attr["crc"])
        if "dir" in attr:
            attr_list.append("dir: %s" % (attr["dir"]))
        return attr_list

    def colourPrint(self, msg: str, colour: str) -> None:
        if self.config.verbose:
            if colour == "NONE":
                print(self.replaceSurrogates(msg))
            else:
                print(self.colourString(msg, colour))

    def printFileInfo(self, header: str, f: str, d: dict, sub_header: str = "", skip_info: bool = False) -> None:
        header, sub_header = getString(header), getString(sub_header)
        if f in d and d[f] is not None:
            self.append([header.strip(), sub_header.strip(), f] + self.prettyAttr(d[f]), ["Header", "Subheader", "Path", "Size", "Modified", "Hash", ""], False)
            missing = False
        else:
            self.append([header.strip(), sub_header.strip(), f] + [getString("Missing")], ["Header", "Subheader", "Path", "Size"], False)
            missing = True
        if header == "":
            s = ""
        else:
            s = self.colourString(header, "B") + self.replaceSurrogates(f)
            if not skip_info:
                s = s + "\n"
        if not skip_info:
            extra_space = " "*min(4, self.terminal_width//5-16)
            s = s + extra_space + self.colourString(sub_header, "B") + " "*(12-len(sub_header))
            if not missing:
                s = s + extra_space + self.colourString(getString(" Size: "), "B") + self.prettySize(d[f]["size"])
                s = s + extra_space + self.colourString(getString(" Modified: "), "B") + time.ctime(d[f]["mtime"])
                if "crc" in d[f]:
                    s = s + extra_space + self.colourString(getString(" Hash: "), "B") + d[f]["crc"]
            else:
                s = s + extra_space + self.colourString(getString(" Missing"), "B")
        print(s)

    def printFiles(self, files: list, d: dict) -> None:
        for f in files:
            self.appendNewRowFlag()
            self.printFileInfo("File: ", f, d)

    def printChangedFiles(self, files: list, d1: dict, d2: dict, s1: str = " Source", s2: str = "   Dest") -> None:
        for f in files:
            self.appendNewRowFlag()
            self.printFileInfo("File: ", f, d1, " "*4 + s1)
            self.printFileInfo("", f, d2, " "*4 + s2)

    def printMovedFiles(self, files: list, d1: dict, d2: dict, h1: str = "Source: ", h2: str = "  Dest: ") -> None:
        for f in files:
            self.appendNewRowFlag()
            if self.config.main_mode != "sync":
                self.printFileInfo(h1, f["source"], d1, skip_info=True)
                self.printFileInfo(h2, f["dest"], d2)
            elif f["match"] == "source":
                self.printFileInfo(h1, f["source"], d1, skip_info=True)
                self.printFileInfo(h2, f["dest"], d2, "Move Dest  ")
            elif f["match"] == "dest":
                self.printFileInfo(h1, f["source"], d1, skip_info=True)
                self.printFileInfo(h2, f["dest"], d2, "Move Source")

    def printSyncDbConflicts(self, files: list, d1: dict, d2: dict, d1db: dict, d2db: dict) -> None:
        for f in files:
            self.appendNewRowFlag()
            self.printFileInfo("File: ", f, d1, "     Source")
            self.printFileInfo("", f, d1db, "         DB")
            self.printFileInfo("", f, d2, "       Dest")
            self.printFileInfo("", f, d2db, "         DB")
