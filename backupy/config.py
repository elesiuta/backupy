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

class ConfigObject:
    def __init__(self, config: dict):
        """Used for storing user configuration, meant only for internal use by BackupManager"""
        # default config (from argparse)
        self.source = None
        self.dest = None
        self.main_mode = "mirror"
        self.select_mode = "source"
        self.compare_mode = "attr"
        self.filter_include_list = None
        self.filter_exclude_list = None
        self.noarchive = False
        self.nolog = False
        self.nomoves = False
        self.noprompt = False
        self.dry_run = False
        self.force_posix_path_sep = False
        self.quit_on_db_conflict = False
        self.scan_only = False
        self.verify_copy = False
        # default config (additional)
        self.archive_dir = ".backupy/Archive"
        self.config_dir = ".backupy"
        self.log_dir = ".backupy/Logs"
        self.trash_dir = ".backupy/Trash"
        self.cleanup_empty_dirs = True
        self.root_alias_log = True
        self.stdout_status_bar = True
        self.verbose = True
        # load config
        for key in config:
            if config[key] is not None and hasattr(self, key):
                self.__setattr__(key, config[key])
        # normalize paths (these should be relative, not absolute!)
        self.archive_dir = os.path.normpath(self.archive_dir)
        self.config_dir = os.path.normpath(self.config_dir)
        self.log_dir = os.path.normpath(self.log_dir)
        self.trash_dir = os.path.normpath(self.trash_dir)
