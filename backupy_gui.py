import os
import sys
import typing
import PySimpleGUI as sg
from colored import stylize, attr, fg
from gooey import Gooey, GooeyParser
import backupy

def colourize(string: str, colour: str) -> str:
    colours = {
            "HEADER" : fg("magenta"),
            "OKBLUE" : fg("blue"),
            "OKGREEN" : fg("green"),
            "WARNING" : fg("yellow"),
            "FAIL" : fg("red"),
            "BOLD" : attr("bold"),
            "UNDERLINE" : attr("underlined")
        }
    return stylize(string, colours[colour])

def simplePrompt(msg: str) -> str:
    sg.change_look_and_feel("System Default For Real")
    layout = [ [sg.Text(msg)],
               [sg.Button("Ok"), sg.Button("Cancel")] ]
    window = sg.Window("BackuPy", layout)
    event, _ = window.Read()
    window.close()
    if event == "Ok":
        return "y"
    else:
        return "n"

@Gooey(program_name="BackuPy",
       richtext_controls=True,
       tabbed_groups=True,
       menu=[{
            'name': 'File',
            'items': [{
                    'type': 'AboutDialog',
                    'menuTitle': 'About',
                    'name': 'BackuPy',
                    'description': 'A simple python program for backing up directories',
                    'version': '0.5.5',
                    'website': 'https://github.com/elesiuta/backupy',
                    'license': 'GPLv3'
                }]
            }])
def main_gui():
    # load profiles
    dict_profiles = backupy.readJson("profiles.json")
    if "profiles" in dict_profiles:
        list_profiles = dict_profiles["profiles"]
    else:
        list_profiles = []
    # argparse setup
    parser = GooeyParser(description="A simple python program for backing up directories")
    group1 = parser.add_argument_group("Profiles", "")
    group2 = parser.add_argument_group("Directories", "")
    group3 = parser.add_argument_group("Configuration", "")
    for source_dir in list_profiles:
        group1.add_argument("--load_profile_"+source_dir, action="store_true", metavar="Load: "+os.path.basename(source_dir),
                            gooey_options={"full_width":True, "show_label":True},
                            help=" " + source_dir)
    group2.add_argument("--source", metavar="Source", action="store", type=str, default=None,
                        widget="DirChooser", gooey_options={"full_width":True},
                        help="Path of source")
    group2.add_argument("--dest", metavar="Destination", action="store", type=str, default=None,
                        widget="DirChooser", gooey_options={"full_width":True},
                        help="Path of destination")
    group3_main = group3.add_mutually_exclusive_group(required=True,
                                                      gooey_options={"title":"Main mode: How to handle files that exist only on one side?",
                                                                     "full_width":True,
                                                                     'initial_selection':0})
    group3_main.add_argument("--main_mode_radio_mirror", metavar="Mirror", action="store_true",
                             help="[source-only -> destination, delete destination-only]")
    group3_main.add_argument("--main_mode_radio_backup", metavar="Backup", action="store_true",
                             help="[source-only -> destination, keep destination-only]")
    group3_main.add_argument("--main_mode_radio_sync", metavar="Sync", action="store_true",
                             help="[source-only -> destination, destination-only -> source]")
    group3_select = group3.add_mutually_exclusive_group(required=True,
                                                        gooey_options={"title":"Selection mode: How to handle files that exist on both sides but differ?",
                                                                       "full_width":True,
                                                                       'initial_selection':0})
    group3_select.add_argument("--select_mode_radio_source", metavar="Source", action="store_true",
                               help="[copy source to destination]")
    group3_select.add_argument("--select_mode_radio_dest", metavar="Destination", action="store_true",
                               help="[copy destination to source]")
    group3_select.add_argument("--select_mode_radio_new", metavar="New", action="store_true",
                               help="[copy newer to opposite side]")
    group3_select.add_argument("--select_mode_radio_no", metavar="None", action="store_true",
                               help="[do nothing]")
    group3_compare = group3.add_mutually_exclusive_group(required=True,
                                                         gooey_options={"title":"Compare mode: How to detect files that exist on both sides but differ?",
                                                                        "full_width":True,
                                                                        'initial_selection':0})
    group3_compare.add_argument("--compare_mode_radio_attr", metavar="Attributes", action= "store_true",
                                help="[compare file attributes: mod-time and size]")
    group3_compare.add_argument("--compare_mode_radio_both", metavar="Both", action= "store_true",
                                help="[compare file attributes first, then check CRC]")
    group3_compare.add_argument("--compare_mode_radio_crc", metavar="CRC", action= "store_true",
                                help="[compare CRC only, ignoring file attributes]")
    group3.add_argument("--nomoves", action="store_true", metavar="No moves", gooey_options={"full_width":True},
                        help="Do not detect moved or renamed files")
    group3.add_argument("--noarchive", action="store_true", metavar="No archiving", gooey_options={"full_width":True},
                        help="Disable archiving files before deleting/overwriting to:\n"
                             "  <source|dest>/.backupy/yymmdd-HHMM/\n")
    group3.add_argument("--nolog", action="store_true", metavar="No logs", gooey_options={"full_width":True},
                        help="Disable writing to:\n"
                             "  <source>/.backupy/log-yymmdd-HHMM.csv\n"
                             "  <source|dest>/.backupy/database.json")
    group3.add_argument("--noprompt", action="store_true", metavar="No prompt", gooey_options={"full_width":True},
                        help="Complete run without prompting for confirmation")
    group3.add_argument("--norun", action="store_true", metavar="No run", gooey_options={"full_width":True},
                        help="Perform a dry run according to your configuration")
    group2.add_argument("--save", action="store_true", metavar="Save",
                        help="Save configuration in source")
    group2.add_argument("--load", action="store_true", metavar="Load",
                        help="Load configuration from source")
    # parse args and store dictionary
    args = vars(parser.parse_args())
    args["stdout_status_bar"] = False # https://github.com/chriskiehl/Gooey/issues/213 , use a simpler expression and hide_progress_msg
    # convert radio groups back to choice of string
    for key in list(args.keys()):
        if "_radio_" in key:
            if args[key] == True:
                key_split = key.split("_radio_")
                args[key_split[0]] = key_split[1]
    # check for loaded profiles
    loaded_profiles = []
    for key in list(args.keys()):
        if "load_profile_" in key:
            if args[key] == True:
                loaded_profiles.append(key.lstrip("load_profile_"))
    # execute selected profiles or execute config
    if len(loaded_profiles) >= 1:
        for source_dir in loaded_profiles:
            args["source"] = source_dir
            args["load"] = True
            backup_manager = backupy.BackupManager(args, gui=True)
            backup_manager.backup()
            print("")
    else:
        # check config and execute
        if args["source"] != None and (args["dest"] != None or args["load"]):
            backup_manager = backupy.BackupManager(args, gui=True)
            backup_manager.backup()
            print("")
        else:
            print(colourize("At least one of the following conditions must be satisfied:\n"
                            "\t1) Select at least one profile\n"
                            "\t2) Specify source and destination directories\n"
                            "\t3) Specify source directory and load configuration\n", "FAIL"))
        # store profile if new
        if args["save"] and args["source"] not in list_profiles:
            list_profiles.append(args["source"])
            backupy.writeJson("profiles.json", {"profiles": list_profiles}, False)


if __name__ == "__main__":
    sys.exit(main_gui())


# TODO
# build with onedir and create installer with inno setup - https://github.com/jrsoftware/issrc
