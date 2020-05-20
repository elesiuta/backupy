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

import csv
import json
import os


def getVersion() -> str:
    return "1.7.2"


def getString(text: str) -> str:
    # import locale
    # logic for localisation goes here, set language with either a global or singleton
    # store strings in a dictionary or use this as an alias for gettext
    return text


def writeCsv(file_path: str, data: list) -> None:
    if not os.path.isdir(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    if os.path.isfile(file_path) and not os.access(file_path, os.W_OK):
        file_path = file_path[:-4] + "-1.csv"
    try:
        with open(file_path, "w", newline="", encoding="utf-8", errors="backslashreplace") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerows(data)
    except Exception:
        file_path = file_path[:-4] + "-1.csv"
        with open(file_path, "w", newline="", encoding="utf-8", errors="backslashreplace") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerows(data)


def readJson(file_path: str) -> dict:
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8", errors="surrogateescape") as json_file:
            data = json.load(json_file)
        return data
    return {}


def writeJson(file_path: str, data: dict, subdir: bool = True, sort_keys: bool = False) -> None:
    if subdir and not os.path.isdir(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    try:
        with open(file_path, "w", encoding="utf-8", errors="surrogateescape") as json_file:
            json.dump(data, json_file, indent=1, separators=(',', ': '), sort_keys=sort_keys, ensure_ascii=False)
    except Exception:
        print(getString("Error, could not write: ") + file_path)
