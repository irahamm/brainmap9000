import bisect

import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout
"""
THIS FILE CONTAINS SMALL HELPER FUNCTION
"""

'''
'brainmap9000' is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.
If not, see <https://www.gnu.org/licenses/>.
'''

# define this word binder function according to our file's syntax
def word_bind(words: list, nt):
    s = ""
    for word in words:
        s += word + r"\\"
    s = s[:-2]
    if nt:
        s += "@"+nt
    return s


# this function check if the row the tract adder is trying to add is valid
def valid_line_check(line):
    # first two stops
    if not isinstance(line[0], list) or not isinstance(line[1], list):
        return False
    # a case where we have an unfilled mid-stop
    for i in range(2, len(line)-1):
        if not isinstance(line[i], list) and isinstance(line[i+1], list):
            return False
    return True


# another function which checks if the row that  the tract adder is trying to add is valid
def valid_node_check(line, valid_words):
    line = [x for x in line if not isinstance(x, type(np.nan))]
    for lst in line:
        for line_edit in lst:
            if line_edit not in valid_words:
                return False

    return True


def insortWidget(layout: QVBoxLayout, widget: QWidget):
    """this function inserts a widget into a layout of labels while maintaining alphabetical order"""
    lst = [layout.itemAt(i).widget().text() for i in range(layout.count()) if hasattr(layout.itemAt(i).widget(), 'text')]
    ind = bisect.bisect(lst, widget.text())
    layout.insertWidget(ind, widget)
