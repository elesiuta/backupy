import sys
import typing
import PySimpleGUI as sg
from colored import stylize, attr, fg
from gooey import Gooey, GooeyParser
import backupy

def colourize(string: str, colour: str) -> str:
    return string
    
def simplePrompt(msg: str) -> str:
    sg.change_look_and_feel('System Default For Real')
    layout = [ [sg.Text(msg)],
               [sg.Button('Ok'), sg.Button('Cancel')] ]
    window = sg.Window('BackuPy', layout)
    event, _ = window.Read()
    window.close()
    if event == "Ok":
        return "y"
    else:
        return "n"

@Gooey(program_name="BackuPy", richtext_controls=False, tabbed_groups=True)
def main_gui():
    dict_profiles = backupy.readJson("profiles.json")
    if "profiles" in dict_profiles:
        list_profiles = dict_profiles["profiles"]
    else:
        list_profiles = []
    parser = GooeyParser(description="A simple python program for backing up directories")
    group1 = parser.add_argument_group("Profiles", "")
    group2 = parser.add_argument_group("Directories", "")
    group3 = parser.add_argument_group("Configuration", "")
    group1.add_argument("--loadprofile", metavar="Load Saved Profile", nargs="*", widget='Listbox', choices=list_profiles,
                        help='Load a previously saved profile')
    group2.add_argument("--source", action="store", type=str, default=None, widget='DirChooser',
                        help="Path of source")
    group2.add_argument("--dest", action="store", type=str, default=None, widget='DirChooser',
                        help="Path of destination")
    group3.add_argument("-m", type=str.lower, dest="main_mode", default="mirror", metavar="Main mode", choices=["mirror", "backup", "sync"],
                        help="How to handle files that exist only on one side?\n"
                             "  MIRROR (default)\n"
                             "    [source-only -> destination, delete destination-only]\n"
                             "  BACKUP\n"
                             "    [source-only -> destination, keep destination-only]\n"
                             "  SYNC\n"
                             "    [source-only -> destination, destination-only -> source]")
    group3.add_argument("-s", type=str.lower, dest="select_mode", default="source", metavar="Selection mode", choices=["source", "dest", "new", "no"],
                        help="How to handle files that exist on both sides but differ?\n"
                             "  SOURCE (default)\n"
                             "    [copy source to destination]\n"
                             "  DEST\n"
                             "    [copy destination to source]\n"
                             "  NEW\n"
                             "    [copy newer to opposite side]\n"
                             "  NO\n"
                             "    [do nothing]")
    group3.add_argument("-c", type=str.lower, dest="compare_mode", default="attr", metavar="Compare mode", choices=["attr", "both", "crc"],
                        help="How to detect files that exist on both sides but differ?\n"
                             "  ATTR (default)\n"
                             "    [compare file attributes: mod-time and size]\n"
                             "  BOTH\n"
                             "    [compare file attributes first, then check CRC]\n"
                             "  CRC\n"
                             "    [compare CRC only, ignoring file attributes]")
    group3.add_argument("--nomoves", action="store_true",
                        help="Do not detect moved or renamed files")
    group3.add_argument("--noarchive", action="store_true",
                        help="Disable archiving files before deleting/overwriting to:\n"
                             "  <source|dest>/.backupy/yymmdd-HHMM/\n")
    group3.add_argument("--nolog", action="store_true",
                        help="Disable writing to:\n"
                             "  <source>/.backupy/log-yymmdd-HHMM.csv\n"
                             "  <source|dest>/.backupy/database.json")
    group3.add_argument("--noprompt", action="store_true",
                        help="Complete run without prompting for confirmation")
    group3.add_argument("--norun", action="store_true",
                        help="Perform a dry run according to your configuration")
    group2.add_argument("--save", action="store_true",
                        help="Save configuration in source")
    group2.add_argument("--load", action="store_true",
                        help="Load configuration from source")
    args = vars(parser.parse_args())
    args["stdout_status_bar"] = False # https://github.com/chriskiehl/Gooey/issues/213 , use a simpler expression and hide_progress_msg
    if args["save"] and args["source"] not in list_profiles:
        list_profiles.append(args["source"])
        backupy.writeJson("profiles.json", {"profiles": list_profiles}, False)
    if args["loadprofile"] != []:
        for i in range(len(args["loadprofile"])):
            args["source"] = args["loadprofile"][i]
            args["load"] = True
            backup_manager = backupy.BackupManager(args, gui=True)
            backup_manager.backup()
    else:
        backup_manager = backupy.BackupManager(args, gui=True)
        backup_manager.backup()


if __name__ == "__main__":
    sys.exit(main_gui())


# TODO
# About dialog - https://github.com/chriskiehl/Gooey#menus
# Richtext - https://github.com/chriskiehl/GooeyExamples/blob/master/examples/richtext_demo.py
# add gui imports (functions from here) to BackupManager init if gui
# use radio group for mode (only if there is a way to add a title and description without putting it on a new tab) https://github.com/chriskiehl/Gooey/blob/master/docs/Gooey-Options.md
# build with onedir and create installer with inno setup - https://github.com/jrsoftware/issrc
# replace gooey with pysimplegui if output windows improves (better richtext and refresh) for smaller build size
