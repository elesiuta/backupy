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

class TransferLists:
    def __init__(self, dir_compare: dict):
        """Holds lists of files that are queued for copying/moving/deleting"""
        self.source_only = dir_compare["source_only"]
        self.dest_only = dir_compare["dest_only"]
        self.changed = dir_compare["changed"]
        self.moved = dir_compare["moved"]

    def __setattr__(self, name, value):
        if not hasattr(self, "locked") or not self.locked:
            super().__setattr__(name, value)
        else:
            raise Exception("Error: Attempted modification to TransferLists after freezing")

    def getLists(self) -> tuple:
        """Returns tuple of lists (or tuples): source_only, dest_only, changed, moved"""
        return (self.source_only,
                self.dest_only,
                self.changed,
                self.moved,)

    def getSets(self) -> tuple:
        """Returns tuple of set(lists): source_only, dest_only, changed, moved (files on source), moved (files on dest)"""
        return (set(self.source_only),
                set(self.dest_only),
                set(self.changed),
                set([f["source"] for f in self.moved]),
                set([f["dest"] for f in self.moved]),)

    def isEmpty(self) -> bool:
        return (len(self.source_only) == 0 and
                len(self.dest_only) == 0 and
                len(self.changed) == 0 and
                len(self.moved) == 0)

    def freeze(self) -> None:
        """Make this object mostly immutable for code safety"""
        self.source_only = tuple(self.source_only)
        self.dest_only = tuple(self.dest_only)
        self.changed = tuple(self.changed)
        self.moved = tuple(self.moved)
        self.locked = True