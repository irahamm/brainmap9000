import os
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QStackedLayout, QPushButton, QDialog\
    , QMenu, QTextEdit, QCompleter, QLineEdit, QComboBox, QColorDialog, QGraphicsItem, QGridLayout, QGraphicsScene\
    , QGraphicsView, QApplication, QTreeWidget, QTreeWidgetItem, QCheckBox
from PyQt5.QtCore import pyqtSignal, QPointF, QRectF, Qt, QStringListModel
from PyQt5.QtGui import QFont, QFontMetrics, QPainter, QColor, QPolygonF, QIcon
from data import topG, n_ts_palette, tracts, nodes_on_map, svg_paths, nt_data, painter_paths,\
    store_path_centers_in_graph
from utils import *
'''
'brainmap9000' is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.
If not, see <https://www.gnu.org/licenses/>.
'''


"""
THIS FILE CONTAINS THE UI's CLASSES
( button classes, separate windows, other stuff that don't happen on the map)
"""


class TractLabelV2(QLabel):  # TRACT BUTTONS
    """this class is for pathway buttons on the left side of the software ('tracts' tab)"""
    off = pyqtSignal()
    on = pyqtSignal()

    class DescEditPopup(QDialog):
        """this window is meant to allow the user to easily edit only the tract's description"""
        textOutput = pyqtSignal(str)

        def __init__(self, parent=None, init_text=""):
            super().__init__(parent)
            self.setWindowTitle("Description Edit")
            self.setWindowIcon(QIcon("icon\\icon.ico"))
            self.text_edit = QTextEdit(init_text)
            self.text_edit.setPlaceholderText("You can enter this tract's description here...")
            apply_btn = QPushButton("Apply")
            apply_btn.pressed.connect(self.send_output)
            bot_layout = QHBoxLayout()
            bot_layout.addStretch()
            bot_layout.addWidget(apply_btn)
            layout = QVBoxLayout()
            layout.addWidget(self.text_edit)
            layout.addLayout(bot_layout)
            self.setLayout(layout)

        def send_output(self):
            self.textOutput.emit(self.text_edit.toPlainText())
            self.close()

    class TagsEditPopup(QDialog):
        """this window allows the user to edit the tract's tags"""

        class SpecialLabel(QLabel):
            """a class for the tags inside the said window, which allows removal using a right click"""
            removeMe = pyqtSignal()

            def __init__(self, text=""):
                super().__init__(text)
                font = QFont()
                font.setPointSize(10)
                self.setFont(font)

            def contextMenuEvent(self, event):
                # create a QMenu
                menu = QMenu(self)

                # add actions to the menu
                action1 = menu.addAction("Remove")

                # connect actions to functions (you can define these functions)
                action1.triggered.connect(lambda: self.removeMe.emit())

                # show the menu at the position of the right-click
                menu.exec_(event.globalPos())

        def __init__(self, parent=None):
            super().__init__(parent)

            self.layout1 = QVBoxLayout()
            for cat in [c for c in self.parent().categories if c in topG.graph.tags]:
                label = self.SpecialLabel(cat)
                label.removeMe.connect(self.remove_tag)
                self.layout1.addWidget(label)

            # plus button
            btn = QPushButton("+")
            btn.pressed.connect(self.add_line_e)
            self.layout1.addWidget(btn)
            ok_btn = QPushButton("OK")
            ok_btn.pressed.connect(self.confirm)
            h_layout = QHBoxLayout()
            h_layout.addStretch()
            h_layout.addWidget(ok_btn)
            self.layout1.addLayout(h_layout)
            self.line_es = []

            self.setLayout(self.layout1)

        def remove_tag(self):
            tag_name = self.sender().text()
            # remove sender tag from the ui
            self.layout1.removeWidget(self.sender())
            self.sender().deleteLater()
            # remove it from the file
            for i in range(tracts.shape[0]):
                if isinstance(tracts.loc[i, 'tags'], str):
                    if f", {tag_name}" in tracts.loc[i, 'tags']:
                        cleaned = tracts.loc[i, 'tags'].replace(f", {tag_name}", "")
                        tracts.loc[i, 'tags'] = cleaned
                    elif f"{tag_name}, " in tracts.loc[i, 'tags']:
                        cleaned = tracts.loc[i, 'tags'].replace(f"{tag_name}, ", "")
                        tracts.loc[i, 'tags'] = cleaned

            tracts.to_csv("paths.csv", index=False)

        def add_line_e(self):
            line_e = RestrictedLineEdit(topG.graph.tags)
            self.layout1.insertWidget(self.layout1.count()-2, line_e)

        def confirm(self):
            if all([self.layout1.itemAt(i).widget().valid_inp for i in range(self.layout1.count()-2) if isinstance(self.layout1.itemAt(i).widget(), RestrictedLineEdit)]):
                tags = [self.layout1.itemAt(i).widget().text() for i in range(self.layout1.count()-2)]
                ind = list(tracts['tract name']).index(self.parent().text())
                # add those tags to the file
                tracts.loc[ind, 'tags'] = ", ".join(tags)
                # update file
                tracts.to_csv("paths.csv", index=False)
                # GET THE ARROWS
                arrows = topG.graph.attribute_dict[self.parent().text() + " (P)"]
                # change the categories variable of each arrow:
                for arr in arrows:
                    arr.categories = [c for c in arr.categories if c not in topG.graph.tags] + tags
                self.close()
            else:
                pass

    def __init__(self, text="", region=[], description=""):
        # congrats, you've reached the init definition of the actual button
        self.region = sorted(region, key=lambda x: x.name)
        super().__init__(text)
        # align left
        self.setAlignment(Qt.AlignLeft)
        # enlarge font
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)
        # set OG style sheet
        self.setStyleSheet("""
                    QLabel {
                        background-color: white;
                    }
                    QLabel:hover {
                        background-color: lightblue;
                    }
                """)
        # read categories from the appropriate attribute in the graph
        self.categories = topG.graph.attribute_dict[f"{self.text()} (P)"][0].categories
        # init description attribute
        if description == "nan":
            description = ""
        self.description = description
        # init file ind attribute
        self.file_ind = list(tracts['tract name']).index(self.text())
        # create toggle attribute
        self.toggle = False
        # create filtered attribute
        self.filtered = False

    def released(self, event=None):
        """this method handles regular (left) mouse clicks in practice
        Args:
            event: the mouseClickEvent"""
        # switch toggle
        self.toggle = not self.toggle
        # get arrows from the graph's attribute_dict attribute
        arrows = topG.graph.attribute_dict[self.text()+" (P)"]
        # handle this attempt according to the state of the toggle attribute
        if self.toggle:
            for arrow in arrows:
                arrow.add_active_pointer()
            self.setStyleSheet("background-color: rgba(173, 216, 255, 1)")
            self.on.emit()
        else:  # (copy code like a maniac)
            for arrow in arrows:
                arrow.decrease_active_pointer()
            self.setStyleSheet("""
                                QLabel {
                                    background-color: white;
                                }
                                QLabel:hover {
                                    background-color: lightblue;
                                }
                            """)
            self.off.emit()

    def contextMenuEvent(self, event):
        """this method handles right-clicking in practice
        Args:
            event: the mouseClickEvent"""
        # create a QMenu
        menu = QMenu(self)
        # add actions to the menu
        action1 = menu.addAction("Show Simplified Figure View")
        action2 = menu.addAction("Show Description")
        action3 = menu.addAction("Edit Description")
        action4 = menu.addAction("Edit Tract")
        action5 = menu.addAction("Edit Tags")

        # connect actions to functions (you can define these functions)
        action1.triggered.connect(self.open_figwind)
        action2.triggered.connect(self.open_descwind)
        action3.triggered.connect(self.edit_desc_pop)
        action4.triggered.connect(self.edit_pathway)
        action5.triggered.connect(self.edit_tags)

        # show the menu at the position of the right-click
        menu.exec_(event.globalPos())

    def open_figwind(self):
        """this method handles opening the figure view window and turning on the button in case it's closed"""
        if not self.toggle:
            self.released()
        # climbing the parent hierarchy, we get the main window and activate it's relevant method
        self.parent().parent().parent().parent().parent().parent().parent().open_figure_window()

    def open_descwind(self):
        """this method handles opening the description view window and turning on the button in case it's closed"""
        if not self.toggle:
            self.released()
        # let's try different way of interacting with the main window:
        # climbing the parent hierarchy (is this heavier than using a signal? intuition says yes. but why?)
        # might be problematic if we change the widget hierarchy somehow sometime
        self.parent().parent().parent().parent().parent().parent().parent().open_descriptions()

    def edit_desc_pop(self):
        """this method opens the small dialog which lets the user edit the description"""
        if isinstance(self.description, type(np.nan)):
            dialog = self.DescEditPopup()
        else:
            dialog = self.DescEditPopup(init_text=self.description)
        dialog.textOutput.connect(self.edit_desc_action)
        dialog.exec()

    def hide_arrows(self):
        """the method hides the tract's arrows"""
        arrows = topG.graph.attribute_dict[self.text() + " (P)"]
        for arrow in arrows:
            arrow.hide()

    def edit_desc_action(self, new_desc: str):
        # change to new description
        self.description = new_desc  # at class
        tracts.loc[self.file_ind, 'description'] = new_desc  # at data frame
        tracts.to_csv("paths.csv", index=False)  # at file
        if self.toggle:  # do a refresh
            self.released()
            self.released()

    def edit_pathway(self):
        """open the pathway in the tract editor mode. this method is triggered by the relevant context menu action"""
        self.parent().parent().parent().parent().parent().parent().parent().open_tract_editor(button=self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.released()

    def filter(self):
        self.hide()
        self.filtered = True

    def unfilter(self):
        self.filtered = False
        self.show()

    def setVisible(self, visible: bool):
        if self.filtered:
            pass
        else:
            super().setVisible(visible)

    def edit_tags(self):
        dialog = self.TagsEditPopup(self)
        dialog.exec()

    def get_categories(self):
        """this function updates and retrieves the current categories of this label using topG's attribute dict"""
        self.categories = topG.graph.attribute_dict[f"{self.text()} (P)"][0].categories
        return self.categories

    def __lt__(self, other):
        return self.text() < other.text()

    def __gt__(self, other):
        return self.text() > other.text()

    def __eq__(self, other):
        if isinstance(other, TractLabelV2):
            return self.text() == other.text()
        elif isinstance(other, str):
            return self.text() == other

# AREA BUTTONS
class LeftAlignedPressableLabel_area(QLabel):
    """this class is for area buttons on the left side of the software ('areas' tab)"""
    # define signals
    off = pyqtSignal()
    on = pyqtSignal()

    def __init__(self, text="", region=[]):
        # init variables
        self.region = region
        super().__init__(text)
        # align left
        self.setAlignment(Qt.AlignLeft)
        # enlarge font
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)
        # set OG style sheet
        self.setStyleSheet("""
                    QLabel {
                        background-color: white;
                    }
                    QLabel:hover {
                        background-color: lightblue;
                    }
                """)
        # init categories attribute (will be useful for filtering purposes)
        self.categories = []
        # (iterates over every category of every arrow that comes out or goes into this area)
        if topG.graph.attribute_dict[self.text() + " (A)"]:
            for arr in topG.graph.attribute_dict[self.text() + " (A)"]:
                for elm in arr.categories:
                    self.categories.append(elm)
        # link mouse release event to our method
        self.mouseReleaseEvent = self.released
        # create a toggle attribute
        self.toggle = False
        # create a filtered attribute
        self.filtered = False

    def released(self, event=None):
        # switch toggle
        self.toggle = not self.toggle
        arrows = topG.graph.attribute_dict[self.text()+" (A)"]
        if arrows == []:
            self.parent().parent().parent().parent().parent().parent().parent().myMenu2.removeWidget(self)
            self.deleteLater()
            return
        if self.toggle:
            for arrow in arrows:
                arrow.add_active_pointer()  # switch this with something else - like '.addActivePointer(pointer)'
                # such a command is defined as an arrowpathItem method.
            self.setStyleSheet("background-color: rgba(173, 216, 255, 1)")
            self.on.emit()
        else:  # (copy code like a maniac)
            for arrow in arrows:
                arrow.decrease_active_pointer()
            self.setStyleSheet("""
                                        QLabel {
                                            background-color: white;
                                        }
                                        QLabel:hover {
                                            background-color: lightblue;
                                        }
                                    """)
            self.off.emit()

    def filter(self):
        self.hide()
        self.filtered = True

    def unfilter(self):
        self.filtered = False
        self.show()

    def setVisible(self, visible: bool):
        if self.filtered:
            pass
        else:
            super().setVisible(visible)

    def get_categories(self):
        """this function updates and retrieves the current categories of this label using topG's attribute dict"""
        self.categories = []
        # "memoisation" could be useful here
        for arr in topG.graph.attribute_dict[self.text() + " (A)"]:
            for elm in arr.categories:
                self.categories.append(elm)
        return self.categories

    def __lt__(self, other):
        return self.text() < other.text()


# A CLASS FOR BUTTONS WHICH ARE A GROUP OF EXISTING BUTTONS
class LeftAlignedPressableLabel_composite(QLabel):
    """this class is for group buttons on the left side of the software (which appear both in the area tab and in the
    tracts tab)"""
    def __init__(self, text="", hashtag="", categories=[]):
        self.hashtag = hashtag
        self.num_of_subt_on = 0
        super().__init__(text)
        # align left
        self.setAlignment(Qt.AlignLeft)
        # enlarge font
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)
        # set OG style sheet
        self.setStyleSheet("""
                    QLabel {
                        background-color: white;
                    }
                    QLabel:hover {
                        background-color: lightblue;
                    }
                """)
        self.mouseReleaseEvent = self.released
        self.sub_tracts = []
        # set toggle attribute
        self.toggle = False
        # set categories attribute
        self.categories = categories
        # filtered attribute
        self.filtered = False
        # connected attribute- this will tell us if the button has been through connection
        self.connected = False

    def activate(self):
        # activates all buttons of the group
        self.setStyleSheet("background-color: rgba(230, 216, 255, 1)")
        for button in topG.graph.hashtag_to_button_dict[self.hashtag]:
            button.released()
        self.num_of_subt_on = len(topG.graph.hashtag_to_button_dict[self.hashtag])

    def deactivate(self):
        # deactivates all the buttons of the group
        self.setStyleSheet("""
                                        QLabel {
                                            background-color: white;
                                        }
                                        QLabel:hover {
                                            background-color: lightblue;
                                        }
                                    """)
        for button in topG.graph.hashtag_to_button_dict[self.hashtag]:
            button.released()
        self.num_of_subt_on = 0

    def group_handler(self):
        # if I got an on, add 1 to num_of_subt and check if I it its equal to group size (ie all buttons are on)
        self.num_of_subt_on += 1
        if self.num_of_subt_on == len(topG.graph.hashtag_to_button_dict[self.hashtag]):
            self.setStyleSheet("background-color: rgba(230, 216, 255, 1)")
            self.toggle = True

    def deactivate_self(self):
        if self.num_of_subt_on == len(topG.graph.hashtag_to_button_dict[self.hashtag]):
            self.setStyleSheet("""
                                                            QLabel {
                                                                background-color: white;
                                                            }
                                                            QLabel:hover {
                                                                background-color: lightblue;
                                                            }
                                                        """)
            self.toggle = False
        # also, decrease number of active buttons by one
        self.num_of_subt_on += -1

    def released(self, event):
        """this method handles clicking"""
        print(self.hashtag)
        if self.num_of_subt_on == len(topG.graph.hashtag_to_button_dict[self.hashtag]) or self.num_of_subt_on == 0:
            # switch toggle
            self.toggle = not self.toggle
            if self.toggle:
                self.activate()
            else:
                self.deactivate()
        else:
            # turn on the buttons which are not currently on
            for button in topG.graph.hashtag_to_button_dict[self.hashtag]:
                if button.toggle is False:
                    button.released()
            self.toggle = True

    def filter(self):
        self.hide()
        self.filtered = True

    def unfilter(self):
        self.filtered = False
        self.show()

    def setVisible(self, visible: bool):
        if self.filtered:
            pass
        else:
            super().setVisible(visible)

    def connect_to_subtract_buttons(self):
        """this method initializes the button's connections with its sub buttons"""
        for button in topG.graph.hashtag_to_button_dict[self.hashtag]:
            button.off.connect(self.deactivate_self)
            button.on.connect(self.group_handler)

    def get_categories(self):
        # for now let's just leave it like this
        return self.categories

    def __lt__(self, other):
        return self.text() < other.text()

    def __eq__(self, other):
        if isinstance(other, str):
            return other == self.hashtag
        else:
            super().__eq__(other)


class RestrictedLineEdit(QLineEdit):
    """this a special line edit subclass which changes colors and a flag (valid_inp) according to word validity"""
    cleared = pyqtSignal()

    def __init__(self, valid_words):
        super().__init__()

        self.valid_words = valid_words
        self.completer = QCompleter(self.valid_words)
        self.completer.setCaseSensitivity(False)  # case-insensitive matching
        self.completer.setFilterMode(Qt.MatchContains)
        self.setCompleter(self.completer)

        self.cleared.connect(self.reset_background)

        # connect the editingFinished signal to validation
        self.editingFinished.connect(self.validate_input)

        # init valid flag
        self.valid_inp = False

    def validate_input(self):
        current_text = self.text()
        if current_text not in self.valid_words:
            self.valid_inp = False
            self.setStyleSheet("background-color: rgba(250, 0, 0, 0.5)")
        else:
            self.valid_inp = True
            self.setStyleSheet("background-color: rgba(0, 250, 0, 0.5)")

    def clear(self):
        super().clear()
        self.valid_inp = False
        self.cleared.emit()

    def reset_background(self):
        self.setStyleSheet("background-color: white")

    def contextMenuEvent(self, event):
        # create a QMenu
        menu = QMenu(self)
        # menu.setStyleSheet("background-color: white;")

        # add actions to the menu
        action1 = menu.addAction("Delete")

        # connect actions to functions (you can define these functions)
        action1.triggered.connect(self.trigger_delete)

        # show the menu at the position of the right-click
        menu.exec_(event.globalPos())

    def trigger_delete(self):
        self.parent().layout().removeWidget(self)
        self.deleteLater()


class TractAdderStop(QWidget):  # a class for a "stop column" within the tract adder
    def __init__(self, stop_num, valid_words, with_nt=False, with_minus=False):
        super().__init__()

        # initialize things
        self.lyt = QVBoxLayout()
        self.stop_num = stop_num
        self.valid_words = valid_words
        self.with_nt = with_nt
        # place to write your stop
        beginning = RestrictedLineEdit(self.valid_words)
        beginning.setPlaceholderText(self.stop_num)
        self.lyt.addWidget(beginning)
        # check for neuro-transmitter and minus flags
        if with_nt:
            nt_options = QComboBox()
            nt_options.addItems(list(n_ts_palette.keys()))
            self.lyt.addWidget(nt_options)
        # button to add another area
        add_area_btn = QPushButton("+")
        add_area_btn.setFixedSize(15, 15)
        add_area_btn.clicked.connect(self.add_area)
        self.lyt.addWidget(add_area_btn)
        self.setLayout(self.lyt)

    def add_area(self):
        beginning = RestrictedLineEdit(self.valid_words)
        beginning.setPlaceholderText(self.stop_num)
        if self.with_nt:
            self.lyt.insertWidget(self.lyt.count() - 2, beginning)
        else:
            self.lyt.insertWidget(self.lyt.count() - 1, beginning)

    def add_nt_box(self):
        nt_options = QComboBox()
        nt_options.addItems(list(n_ts_palette.keys()))
        self.with_nt = True
        self.lyt.insertWidget(self.lyt.count()-1, nt_options)


class SuccessfulPathwayAdditionMsg(QDialog):
    """popup window for a successful addition"""
    def __init__(self, tract_name):
        super().__init__()

        self.setWindowTitle("valid input")
        self.setGeometry(150, 150, 300, 80)

        label = QLabel(f"{tract_name} was added successfully")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: rgba(0, 250, 0, 0.5)")
        cont_layout = QVBoxLayout()
        cont_layout.addWidget(label)
        self.setLayout(cont_layout)


class InvalidPathwayAdditionError(QDialog):
    """popup window for an invalid tract"""
    def __init__(self):
        super().__init__()

        self.setWindowTitle("invalid input")
        self.setGeometry(150, 150, 300, 80)

        self.label = QLabel("invalid pathway input!")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: rgba(250, 0, 0, 0.5)")
        cont_layout = QVBoxLayout()
        cont_layout.addWidget(self.label)
        self.setLayout(cont_layout)


class InvalidPathwayTitleError(QDialog):
    """popup window for an invalid tract title"""
    def __init__(self):
        super().__init__()

        self.setWindowTitle("invalid title")
        self.setGeometry(150, 150, 300, 80)

        label = QLabel("invalid pathway name!")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: rgba(250, 0, 0, 0.5)")
        cont_layout = QVBoxLayout()
        cont_layout.addWidget(label)
        self.setLayout(cont_layout)


class TractAdder(QDialog):
    """the tract adder window. this window allows the user to add his own pathways into the software's data"""
    # we define a successful tract addition signal in order for the tract adder to be able to interact with the main
    # window
    TractAdded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tract Adder")
        self.setGeometry(150, 150, 600, 120)

        # this index will be useful later on
        self.beginning_col_i = tracts.columns.get_loc('beginning')

        # the main layouts
        self.title_layout = QHBoxLayout()
        self.top_layout = QHBoxLayout()
        self.mid_bot_layout = QVBoxLayout()
        self.bottom_layout = QHBoxLayout()
        self.whole_layout = QVBoxLayout()
        # first let's handle the tract title-
        title_line_edit = QLineEdit()
        title_line_edit.setPlaceholderText("tract name")
        # each stop is in fact a vertical layout \ 'column'. look at the TractAdderStop class for more information
        self.valid_words = nodes_on_map
        bgn = TractAdderStop("beginning", self.valid_words, with_nt=True)
        self.end = TractAdderStop("stop1", self.valid_words, with_nt=False)
        # create a button for adding the tract
        add_tract_btn = QPushButton("Add Tract")
        add_tract_btn.clicked.connect(self.AddTractToPathwaysFile)
        # create a "+" button
        plus_btn = QPushButton("+")
        plus_btn.clicked.connect(self.AnotherOne)
        # create a place to enter the tract's description
        self.big_line_e = QTextEdit()
        #big_line_e.setWordWrapMode(QTextOption.WordWrap)
        self.big_line_e.setMinimumSize(500, 100)
        self.big_line_e.setPlaceholderText("You can enter this tract's description here...")
        # set up layouts
        self.title_layout.addWidget(title_line_edit)
        self.title_layout.addStretch()
        self.top_layout.addWidget(bgn)
        self.top_layout.addWidget(self.end)
        self.top_layout.addWidget(plus_btn)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(add_tract_btn)
        self.mid_bot_layout.addWidget(self.big_line_e)
        self.mid_bot_layout.addLayout(self.bottom_layout)
        title_container = QWidget()
        top_container = QWidget()
        bot_container = QWidget()
        title_container.setLayout(self.title_layout)
        top_container.setLayout(self.top_layout)
        bot_container.setLayout(self.mid_bot_layout)
        self.whole_layout.addWidget(title_container)
        self.whole_layout.addWidget(top_container)
        self.whole_layout.addWidget(bot_container)
        self.setLayout(self.whole_layout)

    def AnotherOne(self):
        """this method adds a stop to the window's layout"""
        if self.top_layout.count() == (len(tracts.columns) - self.beginning_col_i):
            stop = TractAdderStop(f"stop{self.top_layout.count()-1}", self.valid_words, with_nt=False)
            self.top_layout.insertWidget(self.top_layout.count() - 1, stop)
            btn = self.top_layout.itemAt(self.top_layout.count()-1).widget()
            self.top_layout.removeWidget(btn)
        else:
            # change last stop to with nt
            #self.end.changestopnum(self.top_layout.count() - 1)
            last_col = self.top_layout.itemAt(self.top_layout.count() - 2).widget()
            last_col.add_nt_box()
            # add the new stop
            stop = TractAdderStop(f"stop{self.top_layout.count() - 1}", self.valid_words, with_nt=False)
            self.top_layout.insertWidget(self.top_layout.count() - 1, stop)

    def AddTractToPathwaysFile(self):
        """this method handles the users tract addition attempts
        it is triggered when the user presses the 'Add Tract' button"""
        row = [np.nan]*(tracts.shape[1] - self.beginning_col_i)
        clear_me = []
        reindex_me = []
        # get the row
        for col_i in range(self.top_layout.count()-1):
            col = self.top_layout.itemAt(col_i)
            col = col.widget()
            col = col.layout()
            ind_drop = 2
            if col_i==self.top_layout.count()-2:
                ind_drop -= 1
            col_nt = None
            try:
                col_nt = col.itemAt(col.count() - 2).widget().currentText()
            except AttributeError:  # last stop has no neuro-transmitter
                pass
            col_text = [col.itemAt(i).widget().text() for i in range(col.count() - ind_drop)]
            row[col_i] = col_text
            # save it for a reset
            clear_me.append([col.itemAt(i).widget() for i in range(col.count() - ind_drop)])
            reindex_me.append(col_nt)
        # turn spaces into nans
        row = list(map(lambda x: np.nan if x == [''] else x, row))
        # get the name of the tract
        title = self.title_layout.itemAt(0).widget()
        if title.text() == "" or topG.graph.attribute_dict[title.text()+" (P)"] != [] or title.text() in list(topG.graph.composite_tracts.values()):
            self.invalid_title_error()
        elif valid_line_check(row) and valid_node_check(row, self.valid_words):
            r = tracts.shape[0]
            tracts.loc[r] = [None] * len(tracts.columns)  # make a new row
            for i, stopCol in enumerate(row):
                if isinstance(stopCol, type(np.nan)):
                    tracts.loc[r, tracts.columns[i + self.beginning_col_i]] = np.nan
                else:
                    tracts.loc[r, tracts.columns[i + self.beginning_col_i]] = word_bind(stopCol, reindex_me[i])
            tracts.loc[r, 'tract name'] = title.text()
            if self.big_line_e.toPlainText() == "":
                tracts.loc[r, 'description'] = np.nan
            else:
                tracts.loc[r, 'description'] = self.big_line_e.toPlainText()
            tracts.to_csv("paths.csv", index=False)
            # integrate the new tract into the software
            self.TractAdded.emit()

            # reset the line edit slots
            self.valid_addition_msg(pthway_title=title.text())
            title.clear()
            for line_edit_list in clear_me:
                for line_edit in line_edit_list:
                    line_edit.clear()
        else:
            self.invalidinputerror()

    def invalid_title_error(self):
        """calls the invalid title dialog"""
        dialog = InvalidPathwayTitleError()
        dialog.exec()

    def invalidinputerror(self):
        """calls the invalid input dialog"""
        dialog2 = InvalidPathwayAdditionError()
        dialog2.exec()

    def valid_addition_msg(self, pthway_title):
        """calls the successful addition dialog"""
        dialog3 = SuccessfulPathwayAdditionMsg(pthway_title)
        dialog3.exec()


class CompositeTractAdder(QDialog):
    """a class for the 'composite tract adder'. this window which lets the user add composite (group) tracts, which
    are tracts which consist of existing tracts (for example: vagus nerve, which consists of its different portions"""
    compTractAdded = pyqtSignal(list)

    def __init__(self, parent, valid_titles):
        super().__init__(parent)
        self.setWindowTitle("Group Tract Maker")
        self.setGeometry(150, 150, 600, 120)

        self.valid_titles = valid_titles

        self.layout = QVBoxLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter your group's name here...")
        label = QLabel("Choose the tracts you wish to include in this group:")
        line_edit1 = RestrictedLineEdit(self.valid_titles)
        line_edit2 = RestrictedLineEdit(self.valid_titles)
        add_another_tract = QPushButton("+")
        add_another_tract.pressed.connect(self.add_line_edit)

        bot_layout = QHBoxLayout()
        add_comp_tract = QPushButton("Add Tract")
        add_comp_tract.pressed.connect(self.add_comp_tract)
        bot_layout.addStretch()
        bot_layout.addWidget(add_comp_tract)

        self.layout.addWidget(self.title_input)
        self.layout.addWidget(label)
        self.layout.addWidget(line_edit1)
        self.layout.addWidget(line_edit2)
        self.layout.addWidget(add_another_tract)
        self.layout.addLayout(bot_layout)

        self.setLayout(self.layout)

    def add_line_edit(self):
        line_edit = RestrictedLineEdit(self.valid_titles)
        self.layout.insertWidget(self.layout.count()-2, line_edit)

    def add_comp_tract(self):  # this method handles (comp) tract adding attempts
        # get the title line edit and check if it's empty
        title = self.layout.itemAt(0).widget()
        if title.text() == "":
            dialog = InvalidPathwayTitleError()
            dialog.exec()
        else:
            # get the tract line edit objects
            line_edits = [self.layout.itemAt(i).widget() for i in range(2, self.layout.count() - 2)]
            # perform title check up
            if self.title_input.text() == "" or self.title_input.text() in list(topG.graph.composite_tracts.values()) \
                    or topG.graph.attribute_dict[title.text()+" (P)"] != []:
                dialog = InvalidPathwayTitleError()
                dialog.exec_()
                return
            # perform check up
            for line_e in line_edits:
                if line_e.text() not in self.valid_titles:
                    dialog = InvalidPathwayAdditionError()
                    dialog.exec_()
                    break
            for line_e in line_edits:
                # 1) df and file:
                ind = list(tracts['tract name']).index(line_e.text())
                if isinstance(tracts.loc[ind, 'hashtags'], str):
                    tracts.loc[ind, 'hashtags'] += f", {title.text()}"
                else:
                    tracts.loc[ind, 'hashtags'] = title.text()
            # add the line
            r = tracts.shape[0]
            tracts.loc[r] = [None] * len(tracts.columns)  # make a new row
            tracts.loc[r, 'tract name'] = title.text()  # set title
            tracts.loc[r, 'beginning'] = f"#{title.text()}"  # set beginning according to our format

            tracts.to_csv("paths.csv", index=False)

            # 2) to the fucking current UI
            self.compTractAdded.emit([line_e.text() for line_e in line_edits])

            # show success popup and clear
            dialog = SuccessfulPathwayAdditionMsg(title.text())
            dialog.exec()
            for line_e in line_edits:
                line_e.clear()
            title.clear()


# now for the tract remover-
class SuccessfulPathwayRemovalMsg(QDialog):
    """popup window for a successful tract removal"""
    def __init__(self, tract_name):
        super().__init__()

        self.setWindowTitle("valid input")
        self.setGeometry(150, 150, 300, 80)

        label = QLabel(f"{tract_name} was removed")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: rgba(250, 250, 0, 0.5)")
        cont_layout = QVBoxLayout()
        cont_layout.addWidget(label)
        self.setLayout(cont_layout)


class TractRemover(QDialog):
    """the tract remover window. this window allows the user to remove tracts from the software's database and view"""
    # we define a tract removal signal in order for the tract remover to be able to interact with the main
    # window
    TractRemoved = pyqtSignal(TractLabelV2)

    def __init__(self, parent, valid_titles):
        super().__init__(parent)
        self.setWindowTitle("Tract Remover")
        self.setGeometry(150, 150, 600, 120)

        # this index will be useful later on
        #self.beginning_col_i = tracts.columns.get_loc('beginning')

        # init valid pathway titles, a list holding the titles of the current pathways which exist in the program
        self.valid_titles = valid_titles
        # init the layouts and widgets
        self.title_layout = QHBoxLayout()
        self.bottom_layout = QHBoxLayout()
        self.whole_layout = QVBoxLayout()
        self.title_line_edit = RestrictedLineEdit(self.valid_titles)
        self.title_line_edit.setPlaceholderText("tract name")
        remove_tract_btn = QPushButton("Remove Tract")
        remove_tract_btn.clicked.connect(self.RemoveTractFromPathwaysFile)
        # fill up layouts and put inside container widgets
        self.title_layout.addWidget(self.title_line_edit)
        self.title_layout.addStretch()
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(remove_tract_btn)
        title_container = QWidget()
        bot_container = QWidget()
        title_container.setLayout(self.title_layout)
        bot_container.setLayout(self.bottom_layout)
        self.whole_layout.addWidget(title_container)
        self.whole_layout.addWidget(bot_container)
        self.setLayout(self.whole_layout)

    def invalid_title_error(self):  # method which causes an invalid input title popup
        dialog = InvalidPathwayTitleError()
        dialog.exec()

    def valid_removal_msg(self, pthway_title):  # method which causes a valid removal popup with the given name
        dialog3 = SuccessfulPathwayRemovalMsg(pthway_title)
        dialog3.exec()

    def RemoveTractFromPathwaysFile(self):  # this method handles tract removal attempts
        # check if a valid title was entered
        if self.title_line_edit.valid_inp is False:
            self.invalid_title_error()
        else:
            label = self.parent().items2[self.parent().items2.index(self.title_line_edit.text())]
            # it would be much easier if we were to get the label from the beginning
            # getting the label from the beginning would be easier if were to have a title to label dict
            # but let's just ignore that shit for now
            # if the tract is a group button we also need to remove every occurence of it in the hashtags column
            # we ponder-
            # let's just deal with this right now, check comptract adder later for name\hashtag buisness
            # we want to check if the hashtag exists in the thingy
            # if it's group button:
            if hasattr(label, 'hashtag'):   # if its a group tract
                t_name = topG.graph.composite_tracts[label.hashtag]
                ind = tracts.index[tracts["tract name"] == t_name].tolist()[0]
                for i in range(tracts.shape[0]):
                    if isinstance(tracts.loc[i, 'hashtags'], str):
                        if label.hashtag in tracts.loc[i, 'hashtags']:
                            split = tracts.loc[i, 'hashtags'].split(", ")
                            split.remove(self.title_line_edit.text())
                            tracts.loc[i, 'hashtags'] = "".join(split)
            else:   # if it's not a group tract
                ind = tracts.index[tracts["tract name"] == label.text()].tolist()[0]

            # remove the pathway from the file
            tracts.drop(index=ind, inplace=True)
            tracts.to_csv("paths.csv", index=False)
            # remove it from internal data storing lists
            self.valid_titles.remove(self.title_line_edit.text())  # within this class
            self.title_line_edit.completer.setModel(QStringListModel(self.valid_titles))  # within the line edit class
            # method which causes a valid removal popup with the pathway's name
            self.valid_removal_msg(pthway_title=self.title_line_edit.text())
            # remove the pathway from the toolbar
            self.TractRemoved.emit(label)  # kind of redundant to do it outside, but, meh
            # clear the line edit widget
            self.title_line_edit.clear()


class TractEditor(QDialog):
    """the tract editor window. this window allows the user to edit existing tracts. a successful change will change
    the database as well as the current view"""
    TractEdited = pyqtSignal(tuple)

    def __init__(self, parent=None, button=False):
        super().__init__(parent)
        self.setWindowTitle("Tract Editor")
        self.setGeometry(150, 150, 600, 120)

        self.tract_titles = [x.text() for x in self.parent().items2[1:-1] if isinstance(x, TractLabelV2)]

        # this index will be useful later on
        self.beginning_col_i = tracts.columns.get_loc('beginning')

        # the main layouts
        self.title_layout = QHBoxLayout()
        self.top_layout = QHBoxLayout()
        self.mid_bot_layout = QVBoxLayout()
        self.bottom_layout = QHBoxLayout()
        self.whole_layout = QVBoxLayout()
        # first let's handle the tract title-
        title_line_edit = RestrictedLineEdit(self.tract_titles)
        title_line_edit.setPlaceholderText("type in the tract you'd like to edit...")
        # each stop is in fact a vertical layout \ 'column'. look at the TractAdderStop class for more information
        self.valid_words = nodes_on_map
        bgn = TractAdderStop("beginning", self.valid_words, with_nt=True)
        end = TractAdderStop("stop1", self.valid_words, with_nt=False)
        # create a button for adding the tract
        add_tract_btn = QPushButton("Save Tract")
        add_tract_btn.clicked.connect(self.ReplaceTractInPathwaysFile)
        # create a "+" button
        plus_btn = QPushButton("+")
        plus_btn.clicked.connect(self.AnotherOne)
        # create a button to trigger the loading of a tract
        load_btn = QPushButton("load")
        load_btn.pressed.connect(self.load_thru_button)
        # create a place to enter the tract's description
        self.big_line_e = QTextEdit()
        self.big_line_e.setMinimumSize(500, 100)
        self.big_line_e.setPlaceholderText("You can enter this tract's description here...")
        # set up layouts
        self.title_layout.addWidget(title_line_edit)
        self.title_layout.addWidget(load_btn)
        self.top_layout.addWidget(bgn)
        self.top_layout.addWidget(end)
        self.top_layout.addWidget(plus_btn)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(add_tract_btn)
        self.mid_bot_layout.addWidget(self.big_line_e)
        self.mid_bot_layout.addLayout(self.bottom_layout)
        title_container = QWidget()
        top_container = QWidget()
        bot_container = QWidget()
        title_container.setLayout(self.title_layout)
        top_container.setLayout(self.top_layout)
        bot_container.setLayout(self.mid_bot_layout)
        self.whole_layout.addWidget(title_container)
        self.whole_layout.addWidget(top_container)
        self.whole_layout.addWidget(bot_container)
        self.setLayout(self.whole_layout)

        # set initial form variable to True
        self.initial_form = True

        # set current label to None
        self.current_label = None

        # hide initially
        top_container.hide()
        bot_container.hide()

        # good, now load-
        if button:
            self.load_tract(button)

    def AnotherOne(self):  # this method adds a stop to the layout
        if self.top_layout.count() == (len(tracts.columns) - self.beginning_col_i):
            stop = TractAdderStop(f"stop{self.top_layout.count()-1}", self.valid_words, with_nt=False)
            self.top_layout.insertWidget(self.top_layout.count() - 1, stop)
            btn = self.top_layout.itemAt(self.top_layout.count()-1).widget()
            self.top_layout.removeWidget(btn)
        else:
            # change last stop to with nt
            last_col = self.top_layout.itemAt(self.top_layout.count() - 2).widget()
            last_col.add_nt_box()
            # add the new stop
            stop = TractAdderStop(f"stop{self.top_layout.count() - 1}", self.valid_words, with_nt=False)
            self.top_layout.insertWidget(self.top_layout.count() - 1, stop)

    def load_thru_button(self):
        """this method handles loading by pressing this window's LOAD button"""
        # check if valid
        # if we want to enable name changing we should capture the old name at this point in time
        if self.title_layout.itemAt(0).widget().valid_inp:
            title = self.title_layout.itemAt(0).widget().text()
            label = self.parent().items2[self.parent().items2.index(title)]  # i have a slight feeling this fucks shit up
            self.load_tract(label)
        else:
            dial = InvalidPathwayTitleError()
            dial.exec()

    def load_tract(self, tract_button: TractLabelV2):
        """this method handles loading a chosen tract into the window"""
        # set current label to tract_button
        self.current_label = tract_button
        if self.initial_form is False:  # if the adder is not in its initial state we need to reinitialize
            # step 1: remove items
            for i in range(self.top_layout.count()-1):
                item = self.top_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            # step 2: add two first columns again
            bgn = TractAdderStop("beginning", self.valid_words, with_nt=True)
            end = TractAdderStop("stop1", self.valid_words, with_nt=False)
            self.top_layout.insertWidget(0, bgn)
            self.top_layout.insertWidget(1, end)

        # show layouts
        self.top_layout.parent().show()
        self.mid_bot_layout.parent().show()
        # we use the label's .region_for_figure attribute here
        # the structure of this attribute is: [( [beginning, beginning, ...], nt ) , ( [stop1, stop1, ...], nt ) , ...]
        # fill in title with the tracts title:
        self.title_layout.itemAt(0).widget().setText(tract_button.text())
        # let's try using the graph's dict_for_figure attribute instead-
        vals = list(topG.graph.dict_for_figure[tract_button.text()].values())
        # fill in description with the tract's description:
        if isinstance(tract_button.description, str):
            self.mid_bot_layout.itemAt(0).widget().setText(tract_button.description)
        # init the number of stop columns-
        for i in range(len(vals)):
            if i > 1:
                self.AnotherOne()
            current_areas = list(vals[i][0])
            stop_col_item = self.top_layout.itemAt(i).widget()
            # load areas into the line edits
            for j, area in enumerate(current_areas):
                if j > 0:  # if an additional area needs to be added, add it
                    stop_col_item.add_area()
                stop_col_item.layout().itemAt(j).widget().setText(area)
            # load neuro-transmitter into QComboBox
            if i > 0:
                prev_stop = self.top_layout.itemAt(i - 1).widget()
                nt_comb = prev_stop.layout().itemAt(prev_stop.layout().count() - 2).widget()
                nt_comb.setCurrentText(vals[i - 1][1])

        self.initial_form = False

    def ReplaceTractInPathwaysFile(self):
        """this method handles the user's tract saving attempts. it is triggered when we press the window's "SAVE"
         button"""
        row = [np.nan]*(tracts.shape[1] - self.beginning_col_i)
        clear_me = []
        reindex_me = []
        # get the row
        for col_i in range(self.top_layout.count()-1):
            col = self.top_layout.itemAt(col_i)
            col = col.widget()
            col = col.layout()
            ind_drop = 2
            if col_i == self.top_layout.count()-2:
                ind_drop -= 1
            col_nt = None
            try:
                col_nt = col.itemAt(col.count() - 2).widget().currentText()
            except AttributeError:  # last stop has no neuro-transmitter
                pass
            col_text = [col.itemAt(i).widget().text() for i in range(col.count() - ind_drop)]
            row[col_i] = col_text
            # save it for a reset
            clear_me.append([col.itemAt(i).widget() for i in range(col.count() - ind_drop)])
            reindex_me.append(col_nt)
        # turn spaces into nans
        row = list(map(lambda x: np.nan if x == [''] else x, row))
        # get the name of the tract
        title = self.title_layout.itemAt(0).widget()
        if self.current_label.text() != title.text():
            if title.text() == "" or title.text() in list(
                    topG.graph.composite_tracts.values()) or topG.graph.attribute_dict[title.text()+" (P)"] != []:
                self.invalid_title_error()
                return
        if valid_line_check(row) and valid_node_check(row, self.valid_words):
            #r = list(tracts['tract name']).index(title.text())
            r = list(tracts['tract name']).index(self.current_label)  # will use the old name, the one used for loading
            tracts.loc[r] = [None] * len(tracts.columns)  # make all of row r's values into None (kind of sus)
            for i, stopCol in enumerate(row):
                if isinstance(stopCol, type(np.nan)):
                    tracts.loc[r, tracts.columns[i + self.beginning_col_i]] = np.nan
                else:
                    tracts.loc[r, tracts.columns[i + self.beginning_col_i]] = word_bind(stopCol, reindex_me[i])
            tracts.loc[r, 'tract name'] = title.text()   # will use the name you entered
            if self.big_line_e.toPlainText() == "":
                tracts.loc[r, 'description'] = np.nan
            else:
                tracts.loc[r, 'description'] = self.big_line_e.toPlainText()
            tracts.to_csv("paths.csv", index=False)
            # integrate the new tract into the software
            self.TractEdited.emit((r, self.current_label))
            # update the completer
            self.tract_titles.remove(self.current_label.text())  # kick the old title
            self.tract_titles.append(title.text())  # add the new one
            title.completer.setModel(QStringListModel(self.tract_titles))  # apply to completer
            # reset the line edit slots
            self.valid_addition_msg(pthway_title=title.text())
            title.clear()
            for line_edit_list in clear_me:
                for line_edit in line_edit_list:
                    line_edit.clear()
            # reset the current label var
            self.current_label = None
        else:
            self.invalidinputerror()

    def invalid_title_error(self):
        dialog = InvalidPathwayTitleError()
        dialog.exec()

    def invalidinputerror(self):
        dialog2 = InvalidPathwayAdditionError()
        dialog2.exec()

    def valid_addition_msg(self, pthway_title):
        dialog3 = SuccessfulPathwayAdditionMsg(pthway_title)
        dialog3.exec()


class NtEditor(QDialog):
    """this window enables the user to add neurotransmitters, edit their names and choose their color"""
    # define some signals
    colorFramePressed = pyqtSignal(str)
    colorFrameRemove = pyqtSignal(str)
    arrowDispChanged = pyqtSignal()

    # before we init, lets define an interactive frame class for the neuro-transmitter colors
    class InteractiveColorFrame(QFrame):
        # define right click and left click signals for later use
        leftClicked = pyqtSignal()
        rightClicked = pyqtSignal()
        removeTriggered = pyqtSignal()
        changeColor = pyqtSignal()

        def __init__(self, color):
            super().__init__()
            # init graphic features
            self.color = color
            self.setFixedSize(36, 36)
            self.setStyleSheet(f"background-color: rgba{QColor(color).getRgb()}; border: 1px solid black;")

        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self.leftClicked.emit()
            elif event.button() == Qt.RightButton:
                self.rightClicked.emit()

        def contextMenuEvent(self, event):
            # create a QMenu
            menu = QMenu(self)
            #menu.setStyleSheet("background-color: white;")

            # add actions to the menu
            action1 = menu.addAction("Change Color")
            action2 = menu.addAction("Remove")

            # connect actions to functions (you can define these functions)
            action1.triggered.connect(self.trigger_edit)
            action2.triggered.connect(self.trigger_remove)

            # show the menu at the position of the right-click
            menu.exec_(event.globalPos())

        def trigger_edit(self):
            self.changeColor.emit()

        def trigger_remove(self):
            self.removeTriggered.emit()

    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("Neuro-transmitter Editor")
        self.setGeometry(150, 150, 600, 120)

        whole_layt = QVBoxLayout()
        # button for changing arrow coloring style
        btn = QPushButton("SWITCH ARROW COLORING (HEAD/FULL)")
        btn.setStyleSheet('background-color: rgba(255,255,255)')
        btn.pressed.connect(self.toggle_arrow_style)
        # palette (color frames need to be intractable)
        self.grid_layout = QGridLayout()
        # loop with row and column tracking
        row, col = 0, 0
        max_columns = 3

        for i, duo in enumerate(n_ts_palette.items()):
            # create pair (label + color frame)
            nt = duo[0]
            color = duo[1]
            pair = QHBoxLayout()
            label = QLabel(nt)
            font = QFont()
            font.setPointSize(15)
            label.setFont(font)
            pair.addWidget(label)

            frame = self.InteractiveColorFrame(color)
            frame.leftClicked.connect(lambda nt=nt, color=color, coords=(row, col): self.open_color_picker((nt, color, coords)))
            frame.removeTriggered.connect(self.remove_nt)
            frame.changeColor.connect(lambda nt=nt, color=color, coords=(row, col): self.open_color_picker((nt, color, coords)))
            pair.addWidget(frame)

            # wrap the pair in a QWidget
            container = QWidget()
            container.setLayout(pair)

            # add the container to the grid layout at the correct position
            self.grid_layout.addWidget(container, row, col)

            # update column and row positions
            col += 1
            if col >= max_columns:  # move to the next row after reaching max columns
                col = 0
                row += 1

        whole_layt.addWidget(btn)
        # create add new neuro transmitter button
        self.add_btn = QPushButton("add a neurotransmitter")
        self.add_btn.pressed.connect(self.open_clear_picker)
        self.grid_layout.addWidget(self.add_btn, row, col)
        whole_layt.addLayout(self.grid_layout)
        self.setLayout(whole_layt)

    class NtAddedPopup(QDialog):
        def __init__(self, nt_name, parent=None):
            super().__init__(parent)
            # set window geometry
            self.setWindowTitle("valid input")
            self.setGeometry(150, 150, 300, 80)

            label = QLabel(f"{nt_name} was added successfully")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("background-color: rgba(0, 250, 0, 0.5)")
            cont_layout = QVBoxLayout()
            cont_layout.addWidget(label)
            self.setLayout(cont_layout)

        def closeEvent(self, event):
            self.parent().close()
            super().closeEvent(event)

    class NtRemovedPopup(QDialog):
        def __init__(self, nt_name, parent=None):
            super().__init__(parent)
            # set window geometry
            self.setWindowTitle("valid input")
            self.setGeometry(150, 150, 300, 80)

            label = QLabel(f"{nt_name} has been removed. All instances of it (if there are any) have been turned into 'idk'")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("background-color: rgba(250, 250, 0, 0.5)")
            cont_layout = QVBoxLayout()
            cont_layout.addWidget(label)
            self.setLayout(cont_layout)

    def open_color_picker(self, trio):
        picker = QColorDialog(QColor(n_ts_palette[trio[0]]))
        picker.colorSelected.connect(lambda color: self.change_nt_color(color, nt=trio[0], inds=trio[2]))
        picker.exec()

    def change_nt_color(self, color_chosen, nt, inds):
        # change the color to the chosen color
        # in the dict
        n_ts_palette[nt] = color_chosen.name()
        # in the color picker
        frame = self.grid_layout.itemAtPosition(inds[0], inds[1]).widget().layout().itemAt(1).widget()
        frame.setStyleSheet(f"background-color: rgba{color_chosen.getRgb()}; border: 1px solid black;")
        # in the color palette view
        self.colorFramePressed.emit(nt)
        # in the nt file
        file_ind = list(nt_data['neurotransmitter']).index(nt)
        nt_data.loc[file_ind, 'color'] = color_chosen.name()
        nt_data.to_csv('nt_palette.csv', index=False)

    def open_clear_picker(self):
        picker = QColorDialog()
        picker.colorSelected.connect(self.open_namedialog)
        picker.exec()

    def open_namedialog(self, color):
        enter_name_dia = QDialog(self)
        layout = QVBoxLayout()
        label = QLabel("Enter your neurotransmitter's name here:")
        enter_name_line = QLineEdit()
        bot_layout = QHBoxLayout()
        enter_btn = QPushButton("Apply")
        bot_layout.addStretch(1)
        bot_layout.addWidget(enter_btn)
        layout.addWidget(label)
        layout.addWidget(enter_name_line)
        layout.addLayout(bot_layout)
        enter_btn.mousePressEvent = lambda event, nt=enter_name_line, color=color.name(): self.add_nt(nt, color, enter_name_dia)
        enter_name_dia.setLayout(layout)
        enter_name_dia.exec()

    def add_nt(self, nt, color, line_dialog):
        """this method adds a new transmitter to the system"""
        nt = nt.text()
        # to the dict
        n_ts_palette.update({nt: color})
        # to the color picker
        row, col = self.grid_layout.getItemPosition(self.grid_layout.indexOf(self.add_btn))[0], self.grid_layout.getItemPosition(self.grid_layout.indexOf(self.add_btn))[1]
        self.grid_layout.removeWidget(self.add_btn)
        self.add_btn.hide()
        # repeat all of this again (should probably put into a function):
        pair = QHBoxLayout()
        label = QLabel(nt)
        font = QFont()
        font.setPointSize(15)
        label.setFont(font)
        pair.addWidget(label)
        # let's try to understand what is going on.
        frame = self.InteractiveColorFrame(color)
        frame.leftClicked.connect(lambda nt=nt, color=color, coords=(row, col): self.open_color_picker((nt, color, coords)))
        frame.removeTriggered.connect(self.remove_nt)
        frame.changeColor.connect(
            lambda nt=nt, color=color, coords=(row, col): self.open_color_picker((nt, color, coords)))
        pair.addWidget(frame)

        # wrap the pair in a QWidget
        container = QWidget()
        container.setLayout(pair)

        # add the container to the grid layout at the correct position
        self.grid_layout.addWidget(container, row, col)
        # update column and row positions
        col += 1  # update row and col
        if col >= 3:  # update row if needed
            col = 0
            row += 1
        # re-add the button:
        self.grid_layout.addWidget(self.add_btn, row, col)
        self.add_btn.show()
        # to the color palette display
        self.colorFramePressed.emit(nt)
        # to the nt file
        nt_data.loc[len(nt_data)] = [nt, color]
        nt_data.to_csv('nt_palette.csv', index=False)
        # show success popup
        dialog = self.NtAddedPopup(nt, parent=line_dialog)
        dialog.exec()

    def remove_nt(self):
        # derive the neuro-transmitter's name from signal
        hlayout = self.sender().parent().layout()
        nt_name = hlayout.itemAt(0).widget().text()

        # remove from the dict
        n_ts_palette.pop(nt_name, None)

        # remove from the nt editor, dynamically-
        # get the widget’s index
        ind = self.grid_layout.indexOf(self.sender().parent())
        if ind == -1:
            return  # The widget is already removed, so exit

        # remove the widget
        widget = self.sender().parent()
        self.grid_layout.removeWidget(widget)
        widget.hide()
        widget.deleteLater()

        # store widgets and their positions BEFORE modifying the layout
        widgets = []
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                r, c, _, _ = self.grid_layout.getItemPosition(self.grid_layout.indexOf(w))
                widgets.append((w, r, c))

        # remove all widgets from layout to avoid shifting issues
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().hide()

        # re-add widgets in the correct order, shifting them left
        for i, (w, r, c) in enumerate(sorted(widgets, key=lambda x: (x[1], x[2]))):
            new_row, new_col = divmod(i, self.grid_layout.columnCount())
            self.grid_layout.addWidget(w, new_row, new_col)
            w.show()
        # remove from the color palette display
        self.colorFrameRemove.emit(nt_name)
        # from the nt file
        line_i = list(nt_data['neurotransmitter']).index(nt_name)
        print(nt_name, line_i)
        nt_data.drop(nt_data.index[line_i], inplace=True)
        nt_data.to_csv("nt_palette.csv", index=False)
        # delete all instances of it in the tracts file
        for i in range(tracts.shape[0]):
            for j in range(tracts.columns.get_loc('beginning'), tracts.shape[1]):
                if isinstance(tracts.iloc[i, j], str):
                    if f"@{nt_name}" in tracts.iloc[i, j]:
                        cleaned = tracts.iloc[i, j].replace(f"@{nt_name}", "")
                        tracts.iloc[i, j] = cleaned
        # update file
        tracts.to_csv("paths.csv", index=False)
        # show nt removed msg
        dialog = self.NtRemovedPopup(nt_name)
        dialog.exec()

    def toggle_arrow_style(self):
        self.arrowDispChanged.emit()

# this needs to be a nested class within FigWindow
class figLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)

        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
        self.setStyleSheet("background-color: rgba(250,250,250,1); border: 1px solid black;")


class figTitleLabel(QLabel):
    """class for an area label which appears within the simplified figure window"""
    def __init__(self, text=""):
        super().__init__(text)

        font = QFont()
        font.setPointSize(12)
        self.setFont(font)
        self.setStyleSheet("background-color: rgba(250,0,250,0.2); border: 2px dotted black;")
        self.setAlignment(Qt.AlignCenter)


class figArrow(QLabel):
    """class for a neuro-transmission arrow which appears within the simplified figure window"""
    def __init__(self, text, nt, parent=None):
        super().__init__(parent)
        self.text = nt
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
        self.setMinimumSize(100, 50)
        self.color = QColor(n_ts_palette[nt]) if nt in n_ts_palette else QColor(n_ts_palette['idk'])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # get widget dimensions
        w, h = self.width(), self.height()

        fat_fact = h/4

        # define arrow shape
        arrow_points = QPolygonF([
            QPointF(0, h / 2 - fat_fact),
            QPointF(w - h / 2,  h / 2 - fat_fact),
            QPointF(w - h / 2, 0),
            QPointF(w, h / 2),
            QPointF(w - h / 2, h),
            QPointF(w - h / 2, h / 2 + fat_fact),
            QPointF(0, h / 2 + fat_fact)
        ])

        # draw arrow
        self.color.setAlphaF(0.5)
        painter.setBrush(self.color)
        painter.setPen(Qt.black)
        painter.drawPolygon(arrow_points)

        # draw text inside the arrow
        painter.setPen(Qt.black)
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text)

        painter.end()


class FigWindow(QWidget):
    """a window which displays simplified figures for currently active (pressed) tracts"""
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("Figure Viewer")
        self.setGeometry(850, 150, 600, 120)
        self.setBaseSize(600, 120)

        self.whole_layout = QVBoxLayout()
        self.setLayout(self.whole_layout)

    def add_pathway_figure(self, tract_button: TractLabelV2):
        full_layout = QVBoxLayout()
        title = figTitleLabel(tract_button.text())
        full_layout.addWidget(title)
        figure_layout = QHBoxLayout()
        values = list(topG.graph.dict_for_figure[tract_button.text()].values())

        for value in values:
            stop = value[0]
            nt = value[1]
            col_layout = QVBoxLayout()
            for part in stop:
                layout = QHBoxLayout()
                label = figLabel(part)
                layout.addWidget(label)
                arrow_label = figArrow(f"--({nt})-->", nt)
                col_layout.addLayout(layout)  # done filling the col
            figure_layout.addLayout(col_layout)
            if stop != values[-1][0]:
                figure_layout.addWidget(arrow_label)
        full_layout.addLayout(figure_layout)
        full_layout_container = QWidget()
        full_layout_container.setLayout(full_layout)
        self.whole_layout.addWidget(full_layout_container)

    def remove_pathway_figure(self, tract_button: TractLabelV2):
        for i in range(self.whole_layout.count()):
            itm = self.whole_layout.itemAt(i).widget()
            if tract_button.text() == itm.layout().itemAt(0).widget().text():
                self.whole_layout.removeWidget(itm)
                itm.deleteLater()
                break

        self.adjustSize()
        if self.whole_layout.count() == 0:
            self.resize(600, 120)


class DescWindow(QWidget):
    """a window which displays the descriptions of currently active (pressed) tracts"""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Description Window")
        self.setGeometry(850, 150, 600, 120)
        self.setBaseSize(600, 120)

        self.whole_layout = QVBoxLayout()
        self.setLayout(self.whole_layout)

    def add_descript(self, tract_button: TractLabelV2):
        label = QLabel(f"{tract_button.description}") if not isinstance(tract_button.description, type(np.nan)) else False
        if label:
            font = QFont()
            font.setPointSize(12)
            label.setFont(font)

            sublayout = QVBoxLayout()
            title = figTitleLabel(tract_button.text())
            sublayout.addWidget(title)
            sublayout.addWidget(label)

            container = QWidget()
            container.setLayout(sublayout)
            self.whole_layout.addWidget(container)

    def remove_descript(self, tract_button: TractLabelV2):
        itm = [self.layout().itemAt(i) for i in range(self.layout().count()) if self.layout().itemAt(i).widget().layout().itemAt(0).widget().text()==tract_button.text()]
        if itm:
            self.layout().removeWidget(itm[0].widget())

            self.adjustSize()
            if self.whole_layout.count() == 0:
                self.resize(600, 120)


# this is the beginning of the end-the node tree window
class TreeNodeItem(QGraphicsItem):
    """represents a node in the tree (rectangle with label)."""
    def __init__(self, label, position, parent=None):
        super().__init__(parent)
        self.label = label
        self.position = position

        # setup font
        self.font = QFont("Arial", 15)
        font_metrics = QFontMetrics(self.font)

        # calculate the room needed for the text
        text_width = font_metrics.horizontalAdvance(self.label) + 10
        text_height = font_metrics.height() + 10

        self.bounding_rect = QRectF(self.position.x() - text_width / 2,
                                    self.position.y() - text_height / 2,
                                    text_width, text_height)

        self.required_width = text_width + 40
        self.required_height = text_height + 50

        self.setZValue(2)

    def boundingRect(self):
        """Return the bounding rectangle of the item."""
        return self.bounding_rect

    def paint(self, painter, option, widget=None):
        """Draw the item (rectangle with label)."""
        painter.setBrush(QColor(100, 100, 255))  # Blue fill
        painter.drawRect(self.bounding_rect)  # Draw rectangle

        # draw text centered inside the rectangle
        painter.setFont(self.font)
        painter.setPen(QColor(255, 255, 255))  # White text
        text_x = self.bounding_rect.x() + (
                    self.bounding_rect.width() - painter.fontMetrics().horizontalAdvance(self.label)) / 2
        text_y = self.bounding_rect.y() + (self.bounding_rect.height() + painter.fontMetrics().ascent()) / 2
        painter.drawText(int(text_x), int(text_y), self.label)


class TreeViewWidget(QGraphicsView):
    """this class is a window which displays the current data's node hierarchy"""
    def __init__(self, base_path):
        super().__init__()

        # set up scene and view
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # layout configuration
        self.vertical_spacing = 100

        # calculate subtree sizes for layout
        self.subtree_sizes = {}
        self.calculate_subtree_sizes(base_path)

        # draw the tree from the root
        root_width = self.subtree_sizes.get(base_path, 200)
        self.draw_tree(base_path, QPointF(500, 50), None, 0, root_width)

        self.setRenderHint(QPainter.Antialiasing)

    def calculate_subtree_sizes(self, folder_path):
        """recursively calculates subtree sizes to ensure proper spacing."""
        items = sorted([f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))])

        # compute text width for this node
        font = QFont("Arial", 15)
        font_metrics = QFontMetrics(font)
        text_width = font_metrics.horizontalAdvance(os.path.basename(folder_path)) + 20

        if not items:  # Leaf node
            self.subtree_sizes[folder_path] = text_width
            return text_width

        # calculate widths of child subtrees
        child_sizes = [self.calculate_subtree_sizes(os.path.join(folder_path, f)) for f in items]
        total_width = sum(child_sizes) + (len(child_sizes) - 1) * 50  # 50px padding between siblings

        # ensure node is at least as wide as its own text
        final_width = max(total_width, text_width)
        self.subtree_sizes[folder_path] = final_width
        return final_width

    def draw_tree(self, folder_path, position, parent_position, depth, available_width):
        """recursively draw the tree with dynamically calculated spacing."""
        items = sorted([f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))])

        if not items:
            return

        # compute starting position to center the subtree
        total_subtree_width = self.subtree_sizes[folder_path]
        start_x = position.x() - total_subtree_width / 2

        for folder_name in items:
            subfolder_path = os.path.join(folder_path, folder_name)
            subtree_width = self.subtree_sizes[subfolder_path]

            # position child node within its allocated space
            new_pos = QPointF(start_x + subtree_width / 2, position.y() + self.vertical_spacing)

            # create the tree node item and add to the scene
            tree_node = TreeNodeItem(folder_name, new_pos)
            self.scene.addItem(tree_node)

            # draw line to parent node if exists
            if parent_position:
                self.scene.addLine(parent_position.x(), parent_position.y(), new_pos.x(), new_pos.y())

            # recursively process subfolders
            self.draw_tree(subfolder_path, new_pos, new_pos, depth + 1, subtree_width)

            # move start position for the next node
            start_x += subtree_width + 50  # Ensure spacing

    def wheelEvent(self, event):
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8

            # get mouse position in scene coordinates BEFORE zooming
            mouse_scene_pos = self.mapToScene(event.pos())

            # apply zoom
            self.scale(zoom_factor, zoom_factor)

            # get mouse position in scene coordinates AFTER zooming
            new_mouse_scene_pos = self.mapToScene(event.pos())

            # calculate the difference and shift the view accordingly
            delta = new_mouse_scene_pos - mouse_scene_pos
            self.centerOn(self.mapToScene(self.viewport().rect().center()) - delta)

        else:
            super().wheelEvent(event)


class NodeTreeWind(QWidget):
    """this a container widget for that node hierarchy business"""
    def __init__(self, base_path):
        super().__init__()

        self.tree_view = TreeViewWidget(base_path)

        layout = QVBoxLayout()
        layout.addWidget(self.tree_view)
        self.setLayout(layout)

        self.setWindowTitle("Tree View")
        self.resize(1000, 800)


# the following class is a window which is meant for integrating a new area which the user has drawn on the map, into
# a valid node in the software, which the user can than use as a stop in his graph
# let's try to plan:
# the window will have a - search for new nodes button. pressing this button will scan for AREAS WHICH HAVE A PLACE
# ON THE MAP, BUT ARE NOT INTEGRATED AS NODES
# then let you place these new nodes within the desired region using this class- (which I decided to leave outside of
# the node integrator because who knows, maybe it will be useful in other contexts.
class NodeTreeWidget(QDialog):
    """this window is meant for integrating a new area which the has been drawn on the map, into a valid node within
    the software, which the user can then use as a stop for within a pathway."""
    parentPicked = pyqtSignal(list)

    def __init__(self, base_path, parent=None):
        super().__init__(parent)

        self.setWindowTitle("AREAS")
        self.setGeometry(150, 150, 600, 700)
        # label
        choose_place_label = QLabel("Choose a parent for this area:")
        choose_place_label.font().setPointSize(12)
        # tree widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("Nodes Hierarchy")
        self.tree_widget.setColumnCount(1)
        # self.tree_widget.show()
        # populate the tree widget
        self.initial_tree_item = QTreeWidgetItem(["NODES"])
        self.populate_tree(base_path, self.initial_tree_item)
        self.tree_widget.addTopLevelItem(self.initial_tree_item)

        # button
        btn = QPushButton("Pick")
        btn.pressed.connect(self.picked)

        # layout
        layout = QVBoxLayout()
        layout.addWidget(choose_place_label)
        layout.addWidget(self.tree_widget)
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(btn)
        layout.addLayout(h_layout)
        self.setLayout(layout)

    def populate_tree(self, folder_path, parent_item, items=None):
        if items is None:
            # initialize the sorted list of items in the folder
            items = sorted(os.listdir(folder_path))

        if not items:
            return  # base case: no more items to process

       # process the first item
        first_item = items[0]
        item_path = os.path.join(folder_path, first_item)

        if os.path.isdir(item_path):  # only folders
            tree_item = QTreeWidgetItem([first_item])
            parent_item.addChild(tree_item)
            self.populate_tree(item_path, tree_item)

        self.populate_tree(folder_path, parent_item, items[1:])

    def picked(self):
        parents = []
        item = self.tree_widget.currentItem()
        parents.append(item.text(0))
        while item and item.parent():
            item = item.parent()
            parents.append(item.text(0))
        self.parentPicked.emit(parents)
        self.tree_widget.collapseAll()
        self.close()


# the button we talked about-
class NodeIntegrator(QDialog):

    class NewAreaLabel(QLabel):
        def __init__(self, text=""):
            super().__init__(text)
            font = QFont()
            font.setPointSize(8)
            self.setFont(font)
            self.setStyleSheet("""
                                QLabel {
                                    background-color: white;
                                }
                                QLabel:hover {
                                    background-color: lightblue;
                                }
                            """)

        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self.parent().pick_parent_node(self)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        btn = QPushButton("Check For New Areas")
        btn.pressed.connect(self.check)
        self.label = QLabel()
        layout.addWidget(btn)
        layout.addWidget(self.label)

        self.setLayout(layout)

        self.parent_picker = NodeTreeWidget("NODES", self)

    def check(self):
        """this method scans for areas which have a place on the map, but are not integrated as nodes"""
        new_areas = []
        for name, data, tr in svg_paths:
            if (name not in topG.graph.nodes
                    and "view" not in name
                    and "leminiscus" not in name.lower()  # try to avoid white matter
                    and "fasciculus" not in name.lower()
                    and "tract" not in name.lower()
                    and name not in [self.layout().itemAt(i).widget().text() for i in range(self.layout().count())]):
                new_areas.append(name)
        if new_areas:
            self.label.setText("The following areas need to be incorprated as nodes:")
            for area in list(set(new_areas)):
                self.layout().addWidget(self.NewAreaLabel(area))

    def pick_parent_node(self, node_name:QLabel):
        picker = NodeTreeWidget("NODES", self)
        picker.parentPicked.connect(lambda parents: self.integrate_node(node_name, parents))
        picker.exec()

    def integrate_node(self, node_name:QLabel, parents: list):
        parents.reverse()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        remainder_path = "\\".join(parents)+"\\"+node_name.text()
        full_path = script_dir+"\\"+remainder_path
        # create a directory
        os.makedirs(full_path, exist_ok=True)
        # add node to the graph with its parents as regions
        topG.graph.add_node(node_name.text(), region=parents)
        # get path and add pos attribute to this node
        mini_painter_path = [(name, data) for name, data in painter_paths if name==node_name.text()]
        store_path_centers_in_graph(mini_painter_path)
        # remove from node integrator UI
        self.layout().removeWidget(node_name)
        node_name.deleteLater()


class TagsBox(QWidget):
    """this checkbox widgets appears on the left side of the interface (at the 'tabs' tab). it enables the user
    to filter the buttons which currently appear in the 'areas' and 'tracts' tabs according to certain tags"""

    class TagCheckBox(QCheckBox):
        def __init__(self, text):
            super().__init__(text)

            font = QFont()
            font.setPointSize(10)
            self.setFont(font)

            self.setStyleSheet("""
                QCheckBox::indicator {
                    width: 25px;
                    height: 25px;
                }
            """)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.grid_layout = QGridLayout()

        self.active_tags = []
        self.mainWind = self.parent()
        self.tab_item = self.mainWind.tabs
        self.tags_on_flag = False

        self.refresh()

        self.setLayout(self.grid_layout)

    def handle_check(self, state):
        # this is some retarded ass shit and must be changed
        labelmenu = [item for item in self.mainWind.items2
                     if isinstance(item, TractLabelV2)
                     or isinstance(item, LeftAlignedPressableLabel_composite)]+[item for item in self.mainWind.items
                                                                                if isinstance(item, LeftAlignedPressableLabel_area)
                                                                                or isinstance(item, LeftAlignedPressableLabel_composite)]
        # the method that is triggered by the event of a check-box being clicked
        check_name = self.sender().text()
        if state == 2:  # if we have a check-in event
            self.active_tags.append(check_name)
        if state == 0:  # if we have a clear-check event
            self.active_tags.remove(check_name)
        if not self.active_tags:
            self.tags_on_flag = False
            self.tab_item.setTabText(2, 'tags')
            self.tab_item.tabBar().setTabTextColor(2, Qt.black)
        # if active tags isn't empty i.e. there are active tags, show an astrix
        elif self.active_tags and not self.tags_on_flag:
            self.tab_item.setTabText(2, 'tags*')
            self.tab_item.tabBar().setTabTextColor(2, Qt.green)
            self.tags_on_flag = True
        # fill-in the active labels list:
        active_labels = []
        for label in labelmenu:
            exit = False
            for tag in self.active_tags:
                if tag not in label.get_categories():
                    exit = True
                    break
            if exit:
                continue
            else:
                active_labels.append(label)

        # iterate over labels. if we have a label which isn't in the active labels list, .hide() it
        for lab in labelmenu:
            if lab not in active_labels:
                lab.filter()
            else:
                lab.unfilter()

    def refresh(self):
        # if grid has items, delete em
        if self.grid_layout.count() != 0:
            for i in range(self.grid_layout.count()):
                item = self.grid_layout.itemAt(i)
                widg = item.widget()
                if widg.text() in self.active_tags:
                    widg.setCheckState(0)
                widg.deleteLater()

        # fill the grid
        row, col = 0, 0
        # get tags from file
        # self.tags_list = list(set(elem for slot in tracts['tags'] if isinstance(slot, str) for elem in slot.split(", ")))
        # get tags from the graph attribute we created
        tags_list = sorted(list(topG.graph.tags))
        # fill up grid
        for tag in tags_list:
            check_box = self.TagCheckBox(tag)
            check_box.stateChanged.connect(self.handle_check)
            self.grid_layout.addWidget(check_box, row, col)
            # update column and row positions
            col += 1
            if col >= 3:  # move to the next row after reaching max columns
                col = 0
                row += 1


class TagManager(QDialog):
    """a window which lets you incorporate a new tag into the program"""

    class TagManagerLabel(QLabel):
        def __init__(self, text=""):
            super().__init__(text)

            self.setAlignment(Qt.AlignCenter)
            font = QFont()
            font.setPointSize(10)
            self.setFont(font)
            self.setStyleSheet("""
                                QLabel {
                                    background-color: white;
                                }
                                QLabel:hover {
                                    background-color: lightblue;
                                }
                                """)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tag Manager")
        #self.setGeometry(150, 150, 600, 120)

        stacked_layout = QStackedLayout()

        # define first page layout
        layout2 = QHBoxLayout()
        add_label = self.TagManagerLabel("Add a Tag")
        add_label.mousePressEvent = lambda ev: stacked_layout.setCurrentIndex(1)
        remove_label = self.TagManagerLabel("Remove a Tag")
        remove_label.mousePressEvent = lambda ev: stacked_layout.setCurrentIndex(2)
        layout2.addWidget(add_label)
        layout2.addWidget(remove_label)
        # define add page
        layout1 = QVBoxLayout()
        label = QLabel("Enter Your New Tag Below:")
        font = QFont()
        font.setPointSize(10)
        label.setFont(font)
        self.line_e = QLineEdit()
        self.line_e.setPlaceholderText("tag name...")
        h_layout = QHBoxLayout()
        back_btn = QPushButton("<--")
        back_btn.mousePressEvent = lambda ev: stacked_layout.setCurrentIndex(0)
        h_layout.addWidget(back_btn)
        h_layout.addStretch()
        apply_btn = QPushButton("Add")
        apply_btn.pressed.connect(self.addition_attempt)
        h_layout.addWidget(apply_btn)
        # (add to layout1)
        layout1.addWidget(label)
        layout1.addWidget(self.line_e)
        layout1.addLayout(h_layout)
        # define remove page
        layout3 = QVBoxLayout()
        label2 = QLabel("Type in the tag you would want to remove:")
        label2.setFont(font)
        self.rem_line_e = RestrictedLineEdit(list(topG.graph.tags))
        self.rem_line_e.setPlaceholderText("tag name...")
        h_layout2 = QHBoxLayout()
        back_btn2 = QPushButton("<--")
        back_btn2.mousePressEvent = lambda ev: stacked_layout.setCurrentIndex(0)
        h_layout2.addWidget(back_btn2)
        h_layout2.addStretch()
        remove_btn = QPushButton("Remove")
        remove_btn.pressed.connect(self.removal_attempt)
        h_layout2.addWidget(remove_btn)
        layout3.addWidget(label2)
        layout3.addWidget(self.rem_line_e)
        layout3.addLayout(h_layout2)

        # set up stacked layout thing
        start_cont = QWidget()
        start_cont.setLayout(layout2)
        addition_cont = QWidget()
        addition_cont.setLayout(layout1)
        remove_cont = QWidget()
        remove_cont.setLayout(layout3)
        stacked_layout.addWidget(start_cont)
        stacked_layout.addWidget(addition_cont)
        stacked_layout.addWidget(remove_cont)
        self.setLayout(stacked_layout)

    def addition_attempt(self):
        if self.line_e.text() == "":
            dial = InvalidPathwayAdditionError()
            dial.label.setText("tag name cannot be empty!")
            dial.exec()
        else:
            topG.graph.tags.add(self.line_e.text())
            # add to the tabs
            self.parent().tags_disp.refresh()
            dial = SuccessfulPathwayAdditionMsg(self.line_e.text())
            dial.exec()
            self.close()

    def removal_attempt(self):
        if self.rem_line_e.valid_inp:
            # remove from graph tags attribute
            tag = self.rem_line_e.text()
            topG.graph.tags.remove(tag)
            # refresh tags tab
            self.parent().tags_disp.refresh()
            # but.... next time we open software it will still be on
            # for it to not happen, we need to remove every instance of this tag from the tag from the file
            # which should be pretty easy actually
            for i in range(tracts.shape[0]):
                if isinstance(tracts.loc[i, 'tags'], str):
                    if tag in tracts.loc[i, 'tags']:
                        lst = tracts.loc[i, 'tags'].split(", ")
                        lst.remove(tag)
                        tracts.loc[i, 'tags'] = ", ".join(lst)
            # update file
            tracts.to_csv("paths.csv", index=False)
            # show massage
            dial = SuccessfulPathwayRemovalMsg(tag)
            dial.exec()
            self.close()
        else:
            dial = InvalidPathwayAdditionError()
            dial.label.setText("invalid input")
            dial.exec()


class CustomGraphicsView(QGraphicsView):
    """a custom graphics view class in order to enable zooming towards mouse direction"""
    def __init__(self, scene):
        super().__init__(scene)

    def wheelEvent(self, event):
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8

            # get mouse position in scene coordinates before zooming
            mouse_scene_pos = self.mapToScene(event.pos())

            # apply zoom
            self.scale(zoom_factor, zoom_factor)

            # get mouse position in scene coordinates after zooming
            new_mouse_scene_pos = self.mapToScene(event.pos())

            # calculate the difference and shift the view accordingly
            delta = new_mouse_scene_pos - mouse_scene_pos
            self.centerOn(self.mapToScene(self.viewport().rect().center()) - delta)

        else:
            super().wheelEvent(event)
