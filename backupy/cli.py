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
import sys

from .backupman import BackupManager
from .utils import getString


class ArgparseCustomFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text[:2] == 'F!':
            return text.splitlines()[1:]
        return argparse.HelpFormatter._split_lines(self, text, width)


def main() -> int:
    # create CLI and parse arguments with argparse
    parser = argparse.ArgumentParser(description=getString("BackuPy: A simple backup program in python with an emphasis on data integrity and transparent behaviour"),
                                     formatter_class=lambda prog: ArgparseCustomFormatter(prog, max_help_position=15),
                                     usage="%(prog)s [options] -- <source> <dest>\n"
                                           "       %(prog)s <source> <dest> [options]\n"
                                           "       %(prog)s <source> --load [-c mode] [--dbscan] [--dry-run]\n"
                                           "       %(prog)s -h | --help")
    parser.add_argument("source", action="store", type=str,
                        help=getString("Path to source"))
    parser.add_argument("dest", action="store", type=str, nargs="?", default=None,
                        help=getString("Path to destination"))
    group1 = parser.add_argument_group("file mode options", "")
    group2 = parser.add_argument_group("misc file options", "")
    group3 = parser.add_argument_group("execution options", "")
    group4 = parser.add_argument_group("backend options (experimental)", "")
    group5 = parser.add_argument_group("configuration options", "")
    group1.add_argument("-m", type=str.lower, dest="main_mode", default="mirror", metavar="mode", choices=["mirror", "backup", "sync"],
                        help=getString(
                             "F!\n"
                             "Main mode: for files that exist only on one side\n"
                             "  MIRROR (default)\n"
                             "    [source-only -> destination, delete destination-only]\n"
                             "  BACKUP\n"
                             "    [source-only -> destination, keep destination-only]\n"
                             "  SYNC\n"
                             "    [source-only -> destination, destination-only -> source]"))
    group1.add_argument("-s", type=str.lower, dest="select_mode", default="source", metavar="mode", choices=["source", "dest", "new", "no"],
                        help=getString(
                             "F!\n"
                             "Selection mode: for files that exist on both sides but differ\n"
                             "  SOURCE (default)\n"
                             "    [copy source to destination]\n"
                             "  DEST\n"
                             "    [copy destination to source]\n"
                             "  NEW\n"
                             "    [copy newer to opposite side]\n"
                             "  NO\n"
                             "    [do nothing]"))
    group1.add_argument("-c", type=str.lower, dest="compare_mode", default=None, metavar="mode", choices=["attr", "attr+", "crc"],
                        help=getString(
                             "F!\n"
                             "Compare mode: for detecting which files differ\n"
                             "  ATTR (default)\n"
                             "    [compare file attributes: mod-time and size]\n"
                             "  ATTR+\n"
                             "    [compare file attributes and record CRC for changed files]\n"
                             "  CRC\n"
                             "    [compare file attributes and CRC for every file]"))
    group2.add_argument("--sync-delete", dest="sync_propagate_deletions", action="store_true",
                        help=getString("Use the database to propagate deletions since the last sync"))
    group2.add_argument("--fi", dest="filter_include_list", action="store", type=str, nargs="+", default=None, metavar="regex",
                        help=getString("Filter: Only include files matching the regular expression(s) (include all by default, searches file paths)"))
    group2.add_argument("--fe", dest="filter_exclude_list", action="store", type=str, nargs="+", default=None, metavar="regex",
                        help=getString("Filter: Exclude files matching the regular expression(s) (exclude has priority over include, searches file paths)"))
    group2.add_argument("--noarchive", dest="noarchive", action="store_true",
                        help=getString(
                             "F!\n"
                             "Disable archiving files before overwriting/deleting to:\n"
                             "   <source|dest>/.backupy/Archives/yymmdd-HHMM/\n"
                             "   <source|dest>/.backupy/Trash/yymmdd-HHMM/"))
    group2.add_argument("--nomoves", dest="nomoves", action="store_true",
                        help=getString("Do not detect when files are moved or renamed"))
    group3.add_argument("--noprompt", dest="noprompt", action="store_true",
                        help=getString("Complete run without prompting for confirmation"))
    group3.add_argument("-d", "--dbscan", dest="scan_only", action="store_true",
                        help=getString("Only scan files to check and update their database entries"))
    group3.add_argument("-n", "--dry-run", dest="dry_run", action="store_true",
                        help=getString("Perform a dry run with no changes made to your files"))
    group3.add_argument("-q", "--qconflicts", dest="quit_on_db_conflict", action="store_true",
                        help=getString(
                             "F!\n"
                             "Quit if database conflicts are detected (always notified)\n"
                             "  -> unexpected changes on destination (backup and mirror)\n"
                             "  -> sync conflict (file modified on both sides since last sync)\n"
                             "  -> file corruption (ATTR+ or CRC compare modes)"))
    group3.add_argument("-v", "--verify", dest="verify_copy", action="store_true",
                        help=getString("Verify CRC of copied files"))
    group4.add_argument("--cold", dest="use_cold_storage", action="store_true",
                        help="Do not read files from destination and only use local databases")
    group4.add_argument("--rsync", dest="use_rsync", action="store_true",
                        help="Use rsync backend")
    group5.add_argument("--nolog", dest="nolog", action="store_true",
                        help=getString(
                             "F!\n"
                             "Disable writing log and file databases to:\n"
                             "   <source>/.backupy/Logs/log-yymmdd-HHMM.csv\n"
                             "   <source|dest>/.backupy/database.json"))
    group5.add_argument("-p", "--posix", dest="force_posix_path_sep", action="store_true",
                        help=getString("Force posix style paths on non-posix operating systems"))
    group5.add_argument("-k", "--save", dest="save", action="store_true",
                        help=getString("Save configuration to <source>/.backupy/config.json"))
    group5.add_argument("-l", "--load", dest="load", action="store_true",
                        help=getString("Load configuration from <source>/.backupy/config.json"))
    parser.add_argument("--nocolour", dest="nocolour", action="store_true",
                        help=argparse.SUPPRESS)
    args = parser.parse_args()
    # create and run job
    backup_manager = BackupManager(args)
    return backup_manager.run()


if __name__ == "__main__":
    # execute with python -m backupy.cli
    sys.exit(main())
