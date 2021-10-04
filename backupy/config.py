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
import random
import typing


class ConfigObject:
    def __init__(self, config: dict):
        """Used for storing user configuration, these attribute names are also the key names in config.json or the config dictionary"""
        # default config (from argparse cli)
        self.source: typing.Union[str, None] = None
        self.dest: typing.Union[str, None] = None
        self.main_mode: str = "mirror"
        self.select_mode: str = "source"
        self.compare_mode: str = "attr"
        self.sync_propagate_deletions: bool = False
        self.filter_include_list: typing.Union[list[str], None] = None
        self.filter_exclude_list: typing.Union[list[str], None] = None
        self.noarchive: bool = False
        self.nocolour: bool = False
        self.nofollow: bool = False
        self.nolog: bool = False
        self.nomoves: bool = False
        self.noprompt: bool = False
        self.dry_run: bool = False
        self.force_posix_path_sep: bool = False
        self.quit_on_db_conflict: bool = False
        self.scan_only: bool = False
        self.use_cold_storage: bool = False
        self.use_rsync: bool = False
        self.verify_copy: bool = False
        # default config (additional, cannot set via cli)
        self.source_unique_id: str = "%05x" % random.randrange(16**5)
        self.dest_unique_id: str = "%05x" % random.randrange(16**5)
        self.archive_dir: str = ".backupy/Archive"
        self.config_dir: str = ".backupy"
        self.log_dir: str = ".backupy/Logs"
        self.trash_dir: str = ".backupy/Trash"
        self.cleanup_empty_dirs: bool = True
        self.root_alias_log: bool = True
        self.stdout_status_bar: bool = True
        self.verbose: bool = True
        self.write_database_x2: bool = False
        self.write_log_dest: bool = False
        self.write_log_summary: bool = False
        # load config
        for key in config:
            if config[key] is not None and hasattr(self, key):
                if getattr(self, key) is not None and type(getattr(self, key)) != type(config[key]):
                    raise Exception("Error: Invalid type for %s in config, should be %s" % (key, type(getattr(self, key))))
                self.__setattr__(key, config[key])
        # normalize paths (these should be relative, not absolute!)
        self.archive_dir = os.path.normpath(self.archive_dir)
        self.config_dir = os.path.normpath(self.config_dir)
        self.log_dir = os.path.normpath(self.log_dir)
        self.trash_dir = os.path.normpath(self.trash_dir)
        # check modes are valid
        self.main_mode, self.select_mode, self.compare_mode = self.main_mode.lower(), self.select_mode.lower(), self.compare_mode.lower()
        assert self.main_mode in ["mirror", "backup", "sync"]
        assert self.select_mode in ["source", "dest", "new", "no"]
        assert self.compare_mode in ["attr", "attr+", "crc"]

    def __setattr__(self, name, value):
        if not hasattr(self, "locked") or not self.locked:
            super().__setattr__(name, value)
        else:
            raise Exception("Error: Config modified during run (should be locked)")
