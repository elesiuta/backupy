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

from .filescanner import FileScanner
from .logman import LogManager
from .utils import getString


class TransferLists:
    def __init__(self, dir_compare: dict):
        """Holds lists of files that are queued for copying/moving/deleting"""
        self.source_only = dir_compare["self_only"]
        self.dest_only = dir_compare["other_only"]
        self.changed = dir_compare["changed"]
        self.moved = dir_compare["moved"]
        self.source_deleted = []
        self.dest_deleted = []

    def __setattr__(self, name, value):
        if not hasattr(self, "locked") or not self.locked[0]:
            super().__setattr__(name, value)
        else:
            raise Exception("Error: Attempted modification to TransferLists after freezing")

    def getLists(self) -> tuple:
        """Returns tuple of lists (or tuples): source_only, dest_only, changed, moved"""
        return (self.source_only,
                self.dest_only,
                self.changed,
                self.moved,
                self.source_deleted,
                self.dest_deleted)

    def getSets(self) -> tuple:
        """Returns tuple of set(lists): source_only, dest_only, changed, moved (files on source), moved (files on dest)"""
        return (set(self.source_only),
                set(self.dest_only),
                set(self.changed),
                set([f["source"] for f in self.moved]),
                set([f["dest"] for f in self.moved]),
                set(self.source_deleted),
                set(self.dest_deleted))

    def isEmpty(self) -> bool:
        return (len(self.source_only) == 0 and
                len(self.dest_only) == 0 and
                len(self.changed) == 0 and
                len(self.moved) == 0 and
                len(self.source_deleted) == 0 and
                len(self.dest_deleted) == 0)

    def freeze(self) -> None:
        """Make this object mostly immutable for code safety"""
        self.source_only = tuple(self.source_only)
        self.dest_only = tuple(self.dest_only)
        self.changed = tuple(self.changed)
        self.moved = tuple(self.moved)
        self.locked = [True]

    def _unfreeze(self) -> None:
        """Allow unfreezing for internal methods (obviously not actually private, but should be treated as such)"""
        self.locked[0] = False
        self.source_only = list(self.source_only)
        self.dest_only = list(self.dest_only)
        self.changed = list(self.changed)
        self.moved = list(self.moved)

    def skipFileTransfers(self, log: LogManager) -> bool:
        self._unfreeze()
        log.append([getString("### SKIPPED ###")], ["Section"])
        print(log.colourString(getString("Enter file paths to remove them from the transfer queues, then 'continue' when ready or 'cancel' to abort"), "G"))
        while True:
            p = input("> ")
            if len(p) == 0 or p == "?":
                print(log.colourString(getString("Enter file paths to remove them from the transfer queues, then 'continue' when ready or 'cancel' to abort"), "G"))
            elif p == "continue":
                self.freeze()
                return True
            elif p == "cancel":
                self.freeze()
                return False
            elif p in self.source_only:
                self.source_only.remove(p)
                log.append(["File:", "Source", p], ["Header", "Subheader", "Path"])
            elif p in self.dest_only:
                self.dest_only.remove(p)
                log.append(["File:", "Dest", p], ["Header", "Subheader", "Path"])
            elif p in self.changed:
                self.changed.remove(p)
                log.append(["File:", "Changed", p], ["Header", "Subheader", "Path"])
            elif p in self.source_deleted:
                self.source_deleted.remove(p)
                log.append(["File:", "Deleted", p], ["Header", "Subheader", "Path"])
            elif p in self.dest_deleted:
                self.dest_deleted.remove(p)
                log.append(["File:", "Deleted", p], ["Header", "Subheader", "Path"])
            else:
                print(log.colourString(getString("Could not find file in queues: %s") % (p), "Y"))

    def propagateSyncDeletions(self, source: FileScanner, dest: FileScanner) -> None:
        source_only, dest_only, _, source_moved, dest_moved, _, _ = self.getSets()
        source_diff = source.compareDb(source.getDatabaseX2(), set(), False, True, False)
        source_new, source_modified, source_missing = set(source_diff["self_only"]), set(source_diff["changed"]), set(source_diff["other_only"])
        dest_diff = dest.compareDb(dest.getDatabaseX2(), set(), False, True, False)
        dest_new, dest_modified, dest_missing = set(dest_diff["self_only"]), set(dest_diff["changed"]), set(dest_diff["other_only"])
        # file was deleted on one side, and should be deleted from the other iff it exists and is not new or modified since the last scan
        # if it was moved on one side, it would have been removed from other_only, this is verified under checkConsistency
        source_deleted = (source_missing & dest_only) - (dest_new | dest_modified | dest_moved)
        dest_deleted = (dest_missing & source_only) - (source_new | source_modified | source_moved)
        self.source_only = sorted(list(source_only - dest_deleted))
        self.source_deleted = sorted(list(source_deleted))
        self.dest_only = sorted(list(dest_only - source_deleted))
        self.dest_deleted = sorted(list(dest_deleted))

    def updateSyncMovedDirection(self, dest: FileScanner) -> None:
        # default action is to leave as (move on dest to) match source if unsure
        dest_diff = dest.compareDb(dest.getDatabaseX2(), set(), False, True, False)
        dest_new, dest_missing = set(dest_diff["self_only"]), set(dest_diff["other_only"])
        for pair in self.moved:
            if pair["dest"] in dest_new and pair["source"] in dest_missing:
                # renamed on dest, should move on source to match dest
                pair["match"] = "dest"
