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

import shutil

from .utils import getString, getStringMaxWidth


class StatusBar:
    def __init__(self, title: str, total: int, display: bool, gui: bool = False):
        self.title = title
        self.total = total
        self.display = display
        self.gui = gui
        terminal_width = shutil.get_terminal_size()[0]
        if terminal_width < 16:
            self.display = False
        if self.display:
            self.char_display = terminal_width - 2
            self.progress = 0
            if self.total == -1:
                progress_str = str(self.progress) + ": "
            else:
                self.digits = str(len(str(self.total)))
                progress_str = str("{:>" + self.digits + "}").format(self.progress) + "/" + str(self.total) + ": "
            self.title_str = getString(self.title) + " "
            self.msg_len = self.char_display - len(progress_str) - len(self.title_str)
            msg = " " * self.msg_len
            print(self.title_str + progress_str + msg, end="\r")
        elif self.gui and self.total > 0:
            self.progress = 0
            print("progress: %s/%s" % (self.progress, self.total))

    def update(self, msg: str) -> None:
        if self.display:
            self.progress += 1
            msg = msg.encode("utf-8", "surrogateescape").decode("utf-8", "replace")
            if self.total == -1:
                progress_str = str(self.progress) + ": "
            else:
                progress_str = str("{:>" + self.digits + "}").format(self.progress) + "/" + str(self.total) + ": "
            self.msg_len = self.char_display - len(progress_str) - len(self.title_str)
            while getStringMaxWidth(msg) > self.msg_len:
                splice = (len(msg) - 4) // 2
                msg = msg[:splice] + "..." + msg[-splice:]
            msg = msg + " " * int(self.msg_len - getStringMaxWidth(msg))
            print(self.title_str + progress_str + msg, end="\r")
        elif self.gui and self.total > 0:
            self.progress += 1
            print("progress: %s/%s" % (self.progress, self.total))

    def endProgress(self) -> None:
        if self.display:
            if self.title == "Copying":
                title_str = getString("File operations completed!")
            else:
                title_str = getString(self.title + " completed!")
            # if self.total == 0:
            #     title_str = "No action necessary"
            print(title_str + " " * (self.char_display - len(title_str)))
        elif self.gui and self.total > 0:
            self.progress = self.total
            print("progress: %s/%s" % (self.progress, self.total))
        self.display, self.gui = False, False
