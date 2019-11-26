import sys
import backupy
from gooey import Gooey, GooeyParser

@Gooey(richtext_controls=False)
def main_gui():
    parser = GooeyParser(description="BackuPy: A small python program for backing up directories with an emphasis on clear rules, simple usage and logging changes")
    parser.add_argument("--source", action="store", type=str, widget='DirChooser', required=True,
                        help="Path of source")
    parser.add_argument("--dest", action="store", type=str, default=None, widget='DirChooser',
                        help="Path of destination")
    parser.add_argument("-m", type=str.lower, dest="main_mode", default="mirror", metavar="Main mode", choices=["mirror", "backup", "sync"],
                        help="How to handle files that exist only on one side?\n"
                             "  MIRROR (default)\n"
                             "    [source-only -> destination, delete destination-only]\n"
                             "  BACKUP\n"
                             "    [source-only -> destination, keep destination-only]\n"
                             "  SYNC\n"
                             "    [source-only -> destination, destination-only -> source]")
    parser.add_argument("-s", type=str.lower, dest="select_mode", default="source", metavar="Selection mode (which files to keep)", choices=["source", "dest", "new", "no"],
                        help="How to handle files that exist on both sides but differ?\n"
                             "  SOURCE (default)\n"
                             "    [copy source to destination]\n"
                             "  DEST\n"
                             "    [copy destination to source]\n"
                             "  NEW\n"
                             "    [copy newer to opposite side]\n"
                             "  NO\n"
                             "    [do nothing]")
    parser.add_argument("-c", type=str.lower, dest="compare_mode", default="attr", metavar="Compare mode", choices=["attr", "both", "crc"],
                        help="How to detect files that exist on both sides but differ?\n"
                             "  ATTR (default)\n"
                             "    [compare file attributes: mod-time and size]\n"
                             "  BOTH\n"
                             "    [compare file attributes first, then check CRC]\n"
                             "  CRC\n"
                             "    [compare CRC only, ignoring file attributes]")
    parser.add_argument("--nomoves", action="store_true",
                        help="Don't detect moved or renamed files")
    parser.add_argument("--noarchive", action="store_true",
                        help="Disable archiving, by default files are moved to /.backupy/yymmdd-HHMM/ on their respective side before being removed or overwritten")
    parser.add_argument("--suppress", action="store_true",
                        help="Suppress logging; by default logs are written to source/.backupy/log-yymmdd-HHMM.csv and /.backupy/dirinfo.json")
    parser.add_argument("--goahead", action="store_true",
                        help="Go ahead without prompting for confirmation (MUST BE ENABLED)") # https://github.com/chriskiehl/Gooey/issues/222
    parser.add_argument("--norun", action="store_true",
                        help="Simulate the run according to your configuration")
    parser.add_argument("--save", action="store_true",
                        help="Save configuration in source")
    parser.add_argument("--load", action="store_true",
                        help="Load configuration from source")
    args = parser.parse_args()
    backup_manager = backupy.BackupManager(args, gui=True)
    backup_manager.backup()


if __name__ == "__main__":
    sys.exit(main_gui())
