import os
import sys
import tempfile
sys.stdout = tempfile.TemporaryFile()

import PySimpleGUI as sg
from colored import stylize, attr, fg
from gooey import Gooey, GooeyParser, local_resource_path

from .backupman import BackupManager
from .utils import (
    getVersion,
    readJson,
    writeJson,
)


class Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


sys.stdout = Unbuffered(sys.__stdout__)

GPLv3 = """This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>."""


def colourize(string: str, colour: str) -> str:
    colours = {
            "R": fg("red"),
            "G": fg("green"),
            "B": fg("blue"),
            "Y": fg("yellow"),
            "V": fg("magenta")
        }
    return stylize(string, colours[colour])


def simplePrompt(msg: str) -> str:
    sg.change_look_and_feel("System Default For Real")
    layout = [[sg.Text(msg)],
              [sg.Button("Ok"), sg.Button("Cancel")]]
    window = sg.Window("BackuPy", layout)
    event, _ = window.Read()
    window.close()
    if event == "Ok":
        return "y"
    else:
        return "n"


@Gooey(program_name="BackuPy",
       image_dir=local_resource_path("images/"),
       richtext_controls=True,
       tabbed_groups=True,
       monospace_display=True,
       progress_regex=r"^progress: (?P<current>\d+)/(?P<total>\d+)$",
       progress_expr="current / total * 100",
       hide_progress_msg=True,
       default_size=(620, 530),
       menu=[{
            'name': 'File',
            'items': [{
                    'type': 'AboutDialog',
                    'menuTitle': 'About',
                    'name': 'BackuPy',
                    'description': 'A simple backup program in python',
                    'version': getVersion(),
                    'website': 'https://github.com/elesiuta/backupy',
                    'license': GPLv3
            }]
        }])
def main_gui():
    # load profiles
    dict_profiles = readJson("profiles.json")
    if "profiles" in dict_profiles:
        list_profiles = dict_profiles["profiles"]
    else:
        list_profiles = []
    # argparse setup
    parser = GooeyParser(description="A simple backup program in python")
    group1 = parser.add_argument_group("Profiles", "")
    group2 = parser.add_argument_group("Directories", "")
    group3 = parser.add_argument_group("Usage Mode", "")
    group4 = parser.add_argument_group("Configuration", "")
    for source_dir in list_profiles:
        group1.add_argument("--load_profile_"+source_dir, action="store_true", metavar="Load: "+os.path.basename(source_dir),
                            gooey_options={"full_width": True, "show_label": True},
                            help=" " + source_dir)
    group2.add_argument("--source", metavar="Source", action="store", type=str, default=None,
                        widget="DirChooser", gooey_options={"full_width": True},
                        help="Path of source")
    group2.add_argument("--dest", metavar="Destination", action="store", type=str, default=None,
                        widget="DirChooser", gooey_options={"full_width": True},
                        help="Path of destination")
    group3_main = group3.add_mutually_exclusive_group(required=True,
                                                      gooey_options={"title": "Main mode: How to handle files that exist only on one side?",
                                                                     "full_width": True,
                                                                     'initial_selection': 0})
    group3_main.add_argument("--main_mode_radio_mirror", metavar="Mirror", action="store_true",
                             help="[source-only -> destination, delete destination-only]")
    group3_main.add_argument("--main_mode_radio_backup", metavar="Backup", action="store_true",
                             help="[source-only -> destination, keep destination-only]")
    group3_main.add_argument("--main_mode_radio_sync", metavar="Sync", action="store_true",
                             help="[source-only -> destination, destination-only -> source]")
    group3_select = group3.add_mutually_exclusive_group(required=True,
                                                        gooey_options={"title": "Selection mode: How to handle files that exist on both sides but differ?",
                                                                       "full_width": True,
                                                                       'initial_selection': 0})
    group3_select.add_argument("--select_mode_radio_source", metavar="Source", action="store_true",
                               help="[copy source to destination]")
    group3_select.add_argument("--select_mode_radio_dest", metavar="Destination", action="store_true",
                               help="[copy destination to source]")
    group3_select.add_argument("--select_mode_radio_new", metavar="New", action="store_true",
                               help="[copy newer to opposite side]")
    group3_select.add_argument("--select_mode_radio_no", metavar="None", action="store_true",
                               help="[do nothing]")
    group3_compare = group3.add_mutually_exclusive_group(required=True,
                                                         gooey_options={"title": "Compare mode: How to detect files that exist on both sides but differ?",
                                                                        "full_width": True,
                                                                        'initial_selection': 0})
    group3_compare.add_argument("--compare_mode_radio_attr", metavar="Attribute", action="store_true",
                                help="[compare file attributes: mod-time and size]")
    group3_compare.add_argument("--compare_mode_radio_attr+", metavar="Attribute+", action="store_true",
                                help="[compare file attributes and record CRC for changed files]")
    group3_compare.add_argument("--compare_mode_radio_crc", metavar="CRC", action="store_true",
                                help="[compare file attributes and CRC for every file]")
    group4.add_argument("--dry-run", dest="dry_run", action="store_true", metavar="Dry run", gooey_options={"full_width": True},
                        help=" Perform a dry run with no changes made to your files")
    group4.add_argument("-p", "--posix", dest="--force_posix_path_sep", action="store_true", metavar="Force posix paths", gooey_options={"full_width": True},
                        help=" Force posix style paths on non-posix operating systems")
    group4.add_argument("--sync-delete", dest="sync_propagate_deletions", action="store_true", metavar="Propagate deletions during sync", gooey_options={"full_width": True},
                        help=" Use the database to propagate deletions since the last sync")
    group4.add_argument("--noarchive", action="store_true", metavar="No archiving", gooey_options={"full_width": True},
                        help=" Disable archiving files before overwriting/deleting to:\n"
                             "  <source|dest>/.backupy/Archives/yymmdd-HHMM/\n"
                             "  <source|dest>/.backupy/Trash/yymmdd-HHMM/")
    group4.add_argument("--nolog", action="store_true", metavar="No logs", gooey_options={"full_width": True},
                        help=" Disable writing log and file databases to:\n"
                             "  <source>/.backupy/Logs/log-yymmdd-HHMM.csv\n"
                             "  <source|dest>/.backupy/database.json")
    group4.add_argument("--nomoves", action="store_true", metavar="No moves", gooey_options={"full_width": True},
                        help=" Do not detect when files are moved or renamed")
    group4.add_argument("--noprompt", action="store_true", metavar="No prompt", gooey_options={"full_width": True},
                        help=" Complete run without prompting for confirmation")
    group4.add_argument("-q", "--qconflicts", dest="--quit_on_db_conflict", action="store_true", metavar="Quit on database conflicts", gooey_options={"full_width": True},
                        help=" Quit if database conflicts are detected (always notified)\n"
                             "  -> unexpected changes on destination (backup and mirror)\n"
                             "  -> sync conflict (file modified on both sides since last sync)\n"
                             "  -> file corruption (ATTR+ or CRC compare modes)")
    group4.add_argument("-d", "--dbscan", dest="scan_only", action="store_true", metavar="Scan only", gooey_options={"full_width": True},
                        help=" Only scan files to check and update their database entries")
    group4.add_argument("-v", "--verify", dest="verify_copy", action="store_true", metavar="Verify copies", gooey_options={"full_width": True},
                        help=" Verify CRC of copied files")
    group2.add_argument("--save", action="store_true", metavar="Save",
                        help=" Save configuration to <source>/.backupy/config.json")
    group2.add_argument("--load", action="store_true", metavar="Load",
                        help=" Load configuration from <source>/.backupy/config.json")
    # parse args and store dictionary
    args = vars(parser.parse_args())
    # convert radio groups back to choice of string
    for key in list(args.keys()):
        if "_radio_" in key:
            if args[key] is True:
                key_split = key.split("_radio_")
                args[key_split[0]] = key_split[1]
    # check for loaded profiles
    loaded_profiles = []
    for key in list(args.keys()):
        if "load_profile_" in key:
            if args[key] is True:
                loaded_profiles.append(key.lstrip("load_profile_"))
    # execute selected profiles or execute config
    if len(loaded_profiles) >= 1:
        for source_dir in loaded_profiles:
            args["source"] = source_dir
            args["load"] = True
            backup_manager = BackupManager(args, gui=True)
            backup_manager.run()
            print("")
    else:
        # store profile if new
        if (args["save"] or args["load"]) and args["source"] not in list_profiles:
            list_profiles.append(args["source"])
            writeJson("profiles.json", {"profiles": list_profiles}, False)
        # check config and execute
        if args["source"] is not None and (args["dest"] is not None or args["load"]):
            backup_manager = BackupManager(args, gui=True)
            backup_manager.run()
            print("")
        else:
            print(colourize("At least one of the following conditions must be satisfied:\n"
                            "\t1) Select at least one profile\n"
                            "\t2) Specify source and destination directories\n"
                            "\t3) Specify source directory and load configuration\n", "R"))


if __name__ == "__main__":
    # execute with python -m backupy.gui
    sys.exit(main_gui())
