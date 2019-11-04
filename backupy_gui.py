import backupy
from gooey import Gooey, GooeyParser

@Gooey(richtext_controls=True)
def main_gui():
    parser = GooeyParser(description="BackuPy: A small python program for backing up directories with an emphasis on clear rules, simple usage and logging changes")
    parser.add_argument("--source", action="store", type=str, widget='DirChooser', required=True,
                        help="Path of source")
    parser.add_argument("--dest", action="store", type=str, default=None, widget='DirChooser',
                        help="Path of destination")
    parser.add_argument("-m", type=str.lower, default="mirror", metavar="mode", choices=["mirror", "backup", "sync"],
                        help="Backup mode:\n"
                             "How to handle files that exist only on one side?\n"
                             "  MIRROR (default)\n"
                             "    [source-only -> destination, delete destination-only]\n"
                             "  BACKUP\n"
                             "    [source-only -> destination, keep destination-only]\n"
                             "  SYNC\n"
                             "    [source-only -> destination, destination-only -> source]")
    parser.add_argument("-c", type=str.lower, default="source", metavar="mode", choices=["source", "dest", "new", "no"],
                        help="Conflict resolution mode:\n"
                             "How to handle files that exist on both sides but differ?\n"
                             "  SOURCE (default)\n"
                             "    [copy source to destination]\n"
                             "  DEST\n"
                             "    [copy destination to source]\n"
                             "  NEW\n"
                             "    [copy newer to opposite side]\n"
                             "  NO\n"
                             "    [do nothing]")
    parser.add_argument("-r", type=str.lower, default="none", metavar="mode", choices=["none", "match", "all"],
                        help="CRC mode:\n"
                             "How to compare files that exist on both sides?\n"
                             "  NONE (default)\n"
                             "    [only compare file size and time, fastest]\n"
                             "  MATCH\n"
                             "    [only compare CRC for files with matching size and time]\n"
                             "  ALL\n"
                             "    [compare CRC first for all files, slowest]")
    parser.add_argument("-d", action="store_true",
                        help="Try and detect moved files")
    parser.add_argument("--noarchive", action="store_true",
                        help="Disable archiving, by default files are moved to /.backupy/yymmdd-HHMM/ on their respective side before being removed or overwritten")
    parser.add_argument("--suppress", action="store_true",
                        help="Suppress logging; by default logs are written to source/.backupy/log-yymmdd-HHMM.csv and /.backupy/dirinfo.json")
    parser.add_argument("--goahead", action="store_true",
                        help="Go ahead without prompting for confirmation (MUST BE ENABLED)")
    parser.add_argument("-n", "--norun", action="store_true",
                        help="Simulate the run according to your configuration")
    parser.add_argument("-s", "--save", action="store_true",
                        help="Save configuration in source")
    parser.add_argument("-l", "--load", action="store_true",
                        help="Load configuration from source")
    args = parser.parse_args()
    backup_manager = backupy.BackupManager(args)
    backup_manager.backup()


if __name__ == "__main__":
    main_gui()
