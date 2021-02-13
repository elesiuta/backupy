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
import unicodedata


def getVersion() -> str:
    return "1.9.0"


def getString(text: str) -> str:
    # import locale
    # logic for localisation goes here, set language with either a global or singleton
    # store strings in a dictionary or use this as an alias for gettext
    return text


def getStringMaxWidth(string: str) -> int:
    width = 0
    for char in string:
        if unicodedata.east_asian_width(char) in ["W", "F", "A"]:
            width += 2
        else:
            width += 1
    return width


def simplePrompt(options: list) -> str:
    while True:
        response = input("> ")
        for option in options:
            if response.strip().lower().startswith(option):
                return option


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


def testConsistency(source_dicts: tuple, source_sets: tuple,
                    dest_dicts: tuple, dest_sets: tuple,
                    transfer_lists: tuple,
                    redundant_source: dict, redundant_dest: dict,
                    redundant_source_moves: dict, redundant_dest_moves: dict) -> None:
    # get sets
    source_only, dest_only, changed, source_moved, dest_moved, source_deleted, dest_deleted = transfer_lists
    source_dict, source_prev = source_dicts
    source_dict, source_prev = set(source_dict), set(source_prev)
    source_new, source_modified, source_missing, source_crc_errors, source_dirs, source_unmodified = source_sets
    dest_dict, dest_prev = dest_dicts
    dest_dict, dest_prev = set(dest_dict), set(dest_prev)
    dest_new, dest_modified, dest_missing, dest_crc_errors, dest_dirs, dest_unmodified = dest_sets
    # make sure each item only appears in one set
    union_len = len(source_only | dest_only | changed | source_moved | dest_moved | source_deleted | dest_deleted)
    total_len = len(source_only) + len(dest_only) + len(changed) + len(source_moved) + len(dest_moved) + len(source_deleted) + len(dest_deleted)
    assert union_len == total_len
    # these versions fail because side comparasion can find crc errors and won't remove them from side_x
    # union_len = len(source_new | source_modified | source_missing | source_crc_errors | source_dirs | source_unmodified)
    # total_len = len(source_new) + len(source_modified) + len(source_missing) + len(source_crc_errors) + len(source_dirs) + len(source_unmodified)
    # union_len = len(dest_new | dest_modified | dest_missing | dest_crc_errors | dest_dirs | dest_unmodified)
    # total_len = len(dest_new) + len(dest_modified) + len(dest_missing) + len(dest_crc_errors) + len(dest_dirs) + len(dest_unmodified)
    # contradictions
    assert not (source_moved & dest_moved)
    assert not (source_only & source_moved)
    assert not (dest_only & dest_moved)
    # changed - ... below would be any skipped files
    # assert changed <= (source_modified | dest_modified) | (source_new & dest_new) | (source_crc_errors | dest_crc_errors)
    assert source_only <= source_dict
    assert dest_only <= dest_dict
    assert not source_only & dest_only
    assert not source_only & changed
    assert not dest_only & changed
    # prev dirs and prev files under .backupy cause the next two asserts to be <=
    assert source_dict <= (source_prev - (source_missing | dest_moved)) | source_new | source_dirs
    assert dest_dict <= (dest_prev - (dest_missing | source_moved)) | dest_new | dest_dirs
    assert source_prev >= (source_unmodified | source_missing) - source_new  # same, basically old stuff that should have been ignored in the old dictionary
    assert dest_prev >= (dest_unmodified | dest_missing) - dest_new
    # basically redo all the logic done during dir and file scan using compareDb to see if they match
    assert set(redundant_source["changed"]) == source_modified
    assert set(redundant_source["other_only"]) >= source_missing
    assert set(redundant_source["other_only"]) <= source_missing | dest_moved
    assert set(redundant_source["self_only"]) == source_new
    assert set(redundant_dest["changed"]) == dest_modified
    assert set(redundant_dest["other_only"]) >= dest_missing
    assert set(redundant_dest["other_only"]) <= dest_missing | source_moved
    assert set(redundant_dest["self_only"]) == dest_new
    # no need to check compareDirInfo anymore since it's just a wrapper for compareDb now
    # redundant_dict_compare = self.source.selfCompare(self.dest.dict_current, False, True, False)
    # redundant_dict_compare_reverse = self.dest.selfCompare(self.source.dict_current, False, True, False)
    # assert set(redundant_dict_compare["modified"]) == (changed | (source_crc_errors & source_dict & dest_dict) | (dest_crc_errors & dest_dict & source_dict))
    # assert set(redundant_dict_compare["modified"]) == (changed | (source_crc_errors - (source_dict - dest_dict)) | (dest_crc_errors - (dest_dict - source_dict)))
    # assert set(redundant_dict_compare["new"]) == source_only | source_moved | dest_deleted
    # assert set(redundant_dict_compare["missing"]) == dest_only | dest_moved | source_deleted
    # assert set(redundant_dict_compare_reverse["modified"]) == (changed | (source_crc_errors - (source_dict - dest_dict)) | (dest_crc_errors - (dest_dict - source_dict)))
    # assert set(redundant_dict_compare_reverse["new"]) == dest_only | dest_moved | source_deleted
    # assert set(redundant_dict_compare_reverse["missing"]) == source_only | source_moved | dest_deleted
    # might be able to make a check for moved along the lines of source_only is approx source_new | dest_missing - dest_new - source_missing
