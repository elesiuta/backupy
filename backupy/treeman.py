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

import curses
import os

from .utils import getStringMaxWidth


def dest_conflicts_tree(dest_new: list, dest_modified: list, dest_missing: list, crc_errors_detected: list) -> None:
    pages = ["return"]
    if dest_new:
        pages.append("Dest Conflicts (new)")
    if dest_modified:
        pages.append("Dest Conflicts (changed)")
    if dest_missing:
        pages.append("Dest Conflicts (missing)")
    if crc_errors_detected:
        pages.append("CRC Errors Detected")
    pages.append("return")
    transfer_trees = []
    if dest_new:
        i = pages.index("Dest Conflicts (new)")
        transfer_trees.append(TreeMan(dest_new, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if dest_modified:
        i = pages.index("Dest Conflicts (changed)")
        transfer_trees.append(TreeMan(dest_modified, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if dest_missing:
        i = pages.index("Dest Conflicts (missing)")
        transfer_trees.append(TreeMan(dest_missing, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if crc_errors_detected:
        i = pages.index("CRC Errors Detected")
        transfer_trees.append(TreeMan(crc_errors_detected, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    i = 0
    while transfer_trees:
        transfer_trees[i].show()
        if transfer_trees[i].next_screen == "left":
            i -= 1
        elif transfer_trees[i].next_screen == "right":
            i += 1
        elif transfer_trees[i].next_screen == "esc":
            break
        if i < 0 or i >= len(transfer_trees):
            break


def scan_only_tree(side_str: str, side_new: list, side_missing: list, side_modified: list, moved) -> None:
    source_moved = [f["source"] for f in moved]
    dest_moved = [f["dest"] for f in moved]
    pages = ["return"]
    if side_new:
        pages.append(side_str + " New")
    if side_modified:
        pages.append(side_str + " Changed")
    if side_missing:
        pages.append(side_str + " Missing")
    if source_moved:
        pages.append("Source Moved")
    if dest_moved:
        pages.append("Dest Moved")
    pages.append("return")
    transfer_trees = []
    if side_new:
        i = pages.index(side_str + " New")
        transfer_trees.append(TreeMan(side_new, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if side_modified:
        i = pages.index(side_str + " Changed")
        transfer_trees.append(TreeMan(side_modified, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if side_missing:
        i = pages.index(side_str + " Missing")
        transfer_trees.append(TreeMan(side_missing, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if source_moved:
        i = pages.index("Source Moved")
        transfer_trees.append(TreeMan(source_moved, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if dest_moved:
        i = pages.index("Dest Moved")
        transfer_trees.append(TreeMan(dest_moved, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    i = 0
    while transfer_trees:
        transfer_trees[i].show()
        if transfer_trees[i].next_screen == "left":
            i -= 1
        elif transfer_trees[i].next_screen == "right":
            i += 1
        elif transfer_trees[i].next_screen == "esc":
            break
        if i < 0 or i >= len(transfer_trees):
            break


def sync_conflicts_tree(sync_conflicts: list, crc_errors_detected: list) -> None:
    pages = ["return"]
    if sync_conflicts:
        pages.append("Sync Database Conflicts")
    if crc_errors_detected:
        pages.append("CRC Errors Detected")
    pages.append("return")
    transfer_trees = []
    if sync_conflicts:
        i = pages.index("Sync Database Conflicts")
        transfer_trees.append(TreeMan(sync_conflicts, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if crc_errors_detected:
        i = pages.index("CRC Errors Detected")
        transfer_trees.append(TreeMan(crc_errors_detected, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    i = 0
    while transfer_trees:
        transfer_trees[i].show()
        if transfer_trees[i].next_screen == "left":
            i -= 1
        elif transfer_trees[i].next_screen == "right":
            i += 1
        elif transfer_trees[i].next_screen == "esc":
            break
        if i < 0 or i >= len(transfer_trees):
            break


def transfer_lists_tree(transfer_lists_list: tuple) -> None:
    source_only, dest_only, changed, moved, source_deleted, dest_deleted = transfer_lists_lis
    source_moved = [f["source"] for f in moved]
    dest_moved = [f["dest"] for f in moved]
    pages = ["prompt"]
    if source_only:
        pages.append("Source Only")
    if dest_only:
        pages.append("Dest Only")
    if changed:
        pages.append("Changed")
    if source_moved:
        pages.append("Source Moved")
    if dest_moved:
        pages.append("Dest Moved")
    if source_deleted:
        pages.append("Deleted from source")
    if dest_deleted:
        pages.append("Deleted from dest")
    pages.append("prompt")
    transfer_trees = []
    if source_only:
        i = pages.index("Source Only")
        transfer_trees.append(TreeMan(source_only, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if dest_only:
        i = pages.index("Dest Only")
        transfer_trees.append(TreeMan(dest_only, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if changed:
        i = pages.index("Changed")
        transfer_trees.append(TreeMan(changed, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if source_moved:
        i = pages.index("Source Moved")
        transfer_trees.append(TreeMan(source_moved, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if dest_moved:
        i = pages.index("Dest Moved")
        transfer_trees.append(TreeMan(dest_moved, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if source_deleted:
        i = pages.index("Deleted from source")
        transfer_trees.append(TreeMan(source_deleted, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    if dest_deleted:
        i = pages.index("Deleted from dest")
        transfer_trees.append(TreeMan(dest_deleted, "<-"+pages[i-1], pages[i], pages[i+1]+"->"))
    i = 0
    while True:
        transfer_trees[i].show()
        if transfer_trees[i].next_screen == "left":
            i -= 1
        elif transfer_trees[i].next_screen == "right":
            i += 1
        elif transfer_trees[i].next_screen == "esc":
            break
        if i < 0 or i >= len(transfer_trees):
            break


class TreeMan:
    def __init__(self, files: list, prev: str, curr: str, next: str):
        self.tree = {"children": {}, "depth": -1, "expanded": True}
        for file_path in files:
            file_split = []
            while True:
                file_path, tail = os.path.split(file_path)
                file_split.append(tail)
                if not file_path:
                    break
            parent = self.tree
            for node in reversed(file_split):
                if node not in parent["children"]:
                    parent["children"][node] = {"children": {}, "depth": parent["depth"] + 1, "expanded": False}
                parent = parent["children"][node]
        self.next_screen = None
        self.prev = prev
        self.curr = curr
        self.next = next

    def traverse(self, tree):
        for child in tree["children"]:
            yield child, tree["children"][child]
            if tree["children"][child]["expanded"]:
                for grandchild, branch in self.traverse(tree["children"][child]):
                    yield grandchild, branch

    def print(self, name, tree, width):
        icon = "|-- "
        if tree["children"]:
            if tree["expanded"]:
                icon = "[-]"
            else:
                icon = "[+]"
        data = "%s%s %s" % (" " * 2 * tree["depth"], icon, name)
        return data + " " * (width - getStringMaxWidth(data))

    def show(self):
        self.next_screen = None
        def cursed_tree(stdscr, self):
            cursor = 1
            toggle_expand = False
            while True:
                stdscr.clear()
                curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
                stdscr.attrset(curses.color_pair(0) | curses.A_BOLD)
                stdscr.addstr("{prev: <{width}}{curr: ^{width}}{next: >{width}}".format(width=curses.COLS//3, prev=self.prev, curr=self.curr, next=self.next))
                line = 1
                offset = max(0, cursor - curses.LINES + 3)
                for name, tree in self.traverse(self.tree):
                    if line == cursor:
                        stdscr.attrset(curses.color_pair(1) | curses.A_BOLD)
                        if toggle_expand:
                            tree["expanded"] = not tree["expanded"]
                            toggle_expand = False
                    else:
                        stdscr.attrset(curses.color_pair(0))
                    if 0 <= line - offset < curses.LINES - 1:
                        stdscr.addstr(line - offset, 0, self.print(name, tree, curses.COLS))
                    line += 1
                stdscr.refresh()
                ch = stdscr.getch()
                if ch == ord("\n") or ch == ord(" "):
                    toggle_expand = True
                elif ch == curses.KEY_UP:
                    cursor -= 1
                elif ch == curses.KEY_DOWN:
                    cursor += 1
                elif ch == curses.KEY_PPAGE:
                    cursor -= curses.LINES
                    if cursor < 1:
                        cursor = 1
                elif ch == curses.KEY_NPAGE:
                    cursor += curses.LINES
                    if cursor >= line:
                        cursor = line - 1
                elif ch == curses.KEY_LEFT:
                    self.next_screen = "left"
                    return
                elif ch == curses.KEY_RIGHT:
                    self.next_screen = "right"
                    return
                elif ch == 27:
                    self.next_screen = "esc"
                    return
                cursor %= line
        curses.wrapper(cursed_tree, self)
