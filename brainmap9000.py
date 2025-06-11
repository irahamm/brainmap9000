import bisect
import sys
from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtGui import QPen, QColor, QIcon
from PyQt5.QtWidgets import QMainWindow, QGraphicsScene, QWidget, QVBoxLayout, QPushButton, QTabWidget, QFrame\
    , QLineEdit, QScrollArea, QMenu, QAction, QHBoxLayout, QApplication
from PyQt5.QtCore import QLineF, QSize, pyqtSignal
from graphics import ResizingTextLabel, CustomPathItem, CustomArrowPathItem, ColorPal, MyArrow
from data import topG, tracts, painter_paths, df_to_edges
from UI import TractLabelV2, LeftAlignedPressableLabel_area, LeftAlignedPressableLabel_composite,  TagsBox, FigWindow,\
    NodeTreeWind, NodeTreeWidget, DescWindow, TractAdder, TractEditor, TractRemover, NodeIntegrator, CustomGraphicsView\
    , CompositeTractAdder, NtEditor, TagManager
from utils import insortWidget
# First - License notice:
'''
'brainmap9000' is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.
If not, see <https://www.gnu.org/licenses/>.
'''

# now that we got that covered, let's dive in


# DEFINE THE MAIN WINDOW
class MainWindow(QMainWindow):
    window_resize_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        # set title
        self.setWindowTitle('brainmap9000')
        # set icon
        self.setWindowIcon(QIcon("icon\\icon.ico"))
        # call initUI
        self.initUI()

    def initUI(self):
        """initializes the UI"""
        # TEXT DISPLAYER
        self.text_disp = ResizingTextLabel("")
        self.text_disp.setFixedHeight(int(self.height() / 15))
        self.text_disp.setWordWrap(True)
        # resizing signal
        self.window_resize_signal.connect(self.text_disp.updateTextSize)
        # MAP
        self.g_scene = QGraphicsScene()
        pen = QPen(QColor(0, 0, 0, 50))
        pen.setWidth(1)
        # load ze svg
        svg_map = QGraphicsSvgItem("MAP_1.svg")
        '''
        IMPORTANT- I figured out the following scale number by trial and error and I still didn't find out why it is
        this number.
        It might be a DPI related difference between the way QPainterPaths load and how an SVG item loads. 
        # This is important because until this is not figured out the project might not generalize to other maps.
        '''
        svg_map.setScale(0.28225)
        self.g_scene.addItem(svg_map)
        # use the paths to create instance of our custom graphicsitem class
        self.path_items = []
        for name, path in painter_paths:
            self.path_items.append(CustomPathItem(path, self.text_disp, name))
        # add the paths to the scene
        for path_item in self.path_items:
            path_item.setPen(pen)
            path_item.setBrush(QColor(0, 0, 0, 0))
            self.g_scene.addItem(path_item)
        # COLOR PALETTE
        self.color_pal_inst = ColorPal()
        # PUT GRAPHICS SCENE IN GRAPHICS VIEW
        self.g_view = CustomGraphicsView(self.g_scene)
        # layout
        colpal_Image = QWidget()
        layout1 = QVBoxLayout(colpal_Image)
        layout1.addWidget(self.g_view)
        # create widget and set the layout
        self.open_color_pal = QPushButton("+")
        self.open_color_pal.setParent(colpal_Image)
        self.open_color_pal.setFixedSize(QSize(30, 30))
        self.open_color_pal.move(20, 20)
        self.g_view.setMinimumSize(QSize(200, 200))
        self.color_pal_inst.move(7, 7)
        self.color_pal_inst.setParent(colpal_Image)
        layout2 = QVBoxLayout()
        layout2.addWidget(self.text_disp)
        layout2.addWidget(colpal_Image)
        Textdisp_Image = QWidget()
        Textdisp_Image.setLayout(layout2)

        self.color_pal_inst.setVisible(False)
        self.color_pal_inst.mousePressEvent = self.hide_ns_palette
        self.open_color_pal.pressed.connect(self.open_ns_palette)
        # FRAME
        frame = QFrame()
        frame.setMinimumWidth(30)
        frame.setStyleSheet("""
                    QFrame {
                        background-color: lightgray;
                    }
                    QFrame:hover {
                        background-color: lightblue;
                    }
                """)
        frame.mousePressEvent = self.meth4

        # TAB MENU
        self.tabs = QTabWidget(self)
        # now create to two tabs-one for areas and one for pathways
        # create layout
        self.myMenu = QVBoxLayout()
        self.myMenu2 = QVBoxLayout()
        # set size of spaces between the options
        self.myMenu.setSpacing(5)
        self.myMenu2.setSpacing(5)
        # add search bars
        searchbar = QLineEdit()
        searchbar.setPlaceholderText("search me...")
        searchbar.textChanged.connect(self.search)
        self.myMenu.addWidget(searchbar)
        searchbar2 = QLineEdit()
        searchbar2.setPlaceholderText("search me...")
        searchbar2.textChanged.connect(self.search2)
        self.myMenu2.addWidget(searchbar2)

        # add a stretcher in order to keep the labels at minimal size
        self.myMenu.addStretch(1)
        self.myMenu2.addStretch(1)
        self.items = [self.myMenu.itemAt(i).widget() for i in range(self.myMenu.count())]
        self.items2 = [self.myMenu2.itemAt(i).widget() for i in range(self.myMenu2.count())]
        whole = QWidget()
        whole.setLayout(self.myMenu)
        whole2 = QWidget()
        whole2.setLayout(self.myMenu2)
        # add scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(whole)
        self.scroll_area2 = QScrollArea()
        self.scroll_area2.setWidgetResizable(True)
        self.scroll_area2.setWidget(whole2)
        # add the tabs (tracts first)
        self.tabs.addTab(self.scroll_area2, "Tracts")
        self.tabs.addTab(self.scroll_area, "Areas")
        # also, create an instance of the TagsBox class for the tags add it as a tab
        self.tags_disp = TagsBox(self)
        self.tabs.addTab(self.tags_disp, "tags")

        # wai
        layout3 = QHBoxLayout()
        layout3.addWidget(self.tabs)
        layout3.addWidget(frame)
        layout3.addWidget(Textdisp_Image)

        Bar_Buttons_Image = QWidget()
        Bar_Buttons_Image.setLayout(layout3)

        self.setCentralWidget(Bar_Buttons_Image)

        # create figure window (window which will contain simplified figures of current active pathways)
        self.figwind_inst = FigWindow(None)
        self.figwind_inst.setWindowIcon(QIcon("icon\\icon.ico"))

        # node tree
        self.blah = NodeTreeWind("NODES")

        #
        self.widg = NodeTreeWidget(parent=None, base_path="NODES")

        # create description window (window which will contain descriptions of each pathway which the user can edit)
        self.descwind_inst = DescWindow(None)
        self.descwind_inst.setWindowIcon(QIcon("icon\\icon.ico"))

        # add the menu from which we can do some stuff (namely open tract adder and tract remover)
        file_menu = QMenu("File", self)
        view_menu = QMenu("View", self)
        option1 = QAction("Add a Tract\Pathway", self)
        option1_0 = QAction("Edit a Tract\Pathway", self)
        option1_1 = QAction("Create a Group Tract", self)
        option2 = QAction("Remove a Tract", self)
        option3 = QAction("Add\Edit Neurotransmitter", self)
        option4 = QAction("Simplified Figure View", self)
        option5 = QAction("Tree Figure View", self)
        option6 = QAction("Description View", self)
        option7 = QAction("Sync Map", self)
        option7_5 = QAction("Add/Remove a Tag", self)
        #option8 = QAction("remove", self)  # just checking something
        file_menu.addAction(option1)
        file_menu.addAction(option1_0)
        file_menu.addAction(option1_1)
        file_menu.addAction(option2)
        file_menu.addAction(option3)
        view_menu.addAction(option4)
        view_menu.addAction(option6)
        view_menu.addAction(option5)
        file_menu.addAction(option7)
        file_menu.addAction(option7_5)
        #file_menu.addAction(option8)

        option1.triggered.connect(self.open_tract_adder)
        option1_0.triggered.connect(self.open_tract_editor)
        option1_1.triggered.connect(self.open_comp_tract_adder)
        option2.triggered.connect(self.open_tract_remover)
        option3.triggered.connect(self.open_nt_editor)
        option4.triggered.connect(self.open_figure_window)
        option5.triggered.connect(self.open_nodetree)
        option6.triggered.connect(self.open_descriptions)
        option7.triggered.connect(self.open_mapsync)
        option7_5.triggered.connect(self.open_tag_manager)
        #option8.triggered.connect(self.remove1)

        self.menuBar().addMenu(file_menu)
        self.menuBar().addMenu(view_menu)

        # connect the envelope graphs signals to the appropriate methods of the main window
        topG.edgeAdded.connect(self.add_edge_to_UI)
        topG.edgeRemoved.connect(self.remove_edge_from_UI)
        # CALL 'df_to_edges' after this connection. this will create arrows and corresponding pathway and area labels
        # the function will add the edges to the nx.graph and also to the UI
        # corresponding pathway, area and group buttons will also be created.
        df_to_edges(tracts)
        # refresh the tags box
        self.tags_disp.refresh()
        # plug group buttons to their children buttons
        for btn in topG.graph.group_buttons:
            btn.connect_to_subtract_buttons()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.tabs.isVisible():  # yes, it's weird
            self.tabs.setFixedWidth(self.one_fifth())
            self.scroll_area.setFixedWidth(self.one_fifth())
        self.text_disp.setFixedHeight(int(self.height()/15))
        self.window_resize_signal.emit()

    def hide_ns_palette(self, event):
        self.color_pal_inst.setVisible(False)

    def open_ns_palette(self):
        self.color_pal_inst.setVisible(True)

    def meth4(self, event):
        """this method hides the side tabs area"""
        """the method is triggered by pressing the frame separating the side tabs area from the map"""
        if self.tabs.isVisible():
            self.tabs.setVisible(False)
            self.scroll_area.setFixedWidth(0)
        else:
            self.tabs.setVisible(True)
            self.scroll_area.setFixedWidth(self.one_fifth())

    def search(self, text):
        for item in self.items[1:-1]:    # (the layouts items not including the search bar and the stretcher)
            item.setVisible(text.lower() in item.text().lower())

    def search2(self, text):
        try:
            for item in self.items2[1:-1]:    # (the layouts items not including the search bar and the stretcher)
                item.setVisible(text.lower() in item.text().lower())
        except RuntimeError:
            pass

    def one_fifth(self):
        # returns one fifth of window's current width
        # this might be retarded, but it works
        return int(self.width()/5)

    def open_tract_adder(self):  # opens the tract adder window
        dialog = TractAdder(self)
        dialog.TractAdded.connect(self.add_tract_to_toolbar)
        dialog.exec()

    def add_tract_to_toolbar(self, r=None):
        """this function will cause line[r] to be rendered into edges and added to the graph"""
        """the function is triggered by a successful tract addition from the tract adder or editor"""
        if not isinstance(r, int):  # if no input number is given, the last line will get picked
            r = -1
        df_to_edges(tracts.iloc[[r]].reset_index(drop=True))

    def open_comp_tract_adder(self):
        """this function creates a composite tract adder window and launches it"""
        """it is triggered by pressing File --> Create a Group Tract in the menu bar"""
        dialog = CompositeTractAdder(self, [x.text() for x in self.items2[1:-1]])
        dialog.compTractAdded.connect(self.add_comptract_to_toolbar)
        dialog.exec()

    def add_comptract_to_toolbar(self, sub_titles):
        """this function handles successful composite tract addition attempts"""
        """the function takes in the titles of the sub tracts (tracts composing the given group tract), (list of str)"""
        # we will now try to fit it to the new format
        title = tracts.loc[tracts.shape[0] - 1, 'tract name']
        hashtag = tracts.loc[tracts.shape[0] - 1, 'beginning'][1:]
        topG.graph.composite_tracts[hashtag] = title
        #sub_labels = []
        # a bit heavy, might find some better way later
        for widget in self.items2[1:-1]:
            if widget.text() in sub_titles:
                #sub_labels.append(widget)
                topG.graph.hashtag_to_button_dict[title].append(widget)
        # add the item without messing alphabetical order
        btn = LeftAlignedPressableLabel_composite(title, hashtag, [])
        # plug it properly
        btn.connect_to_subtract_buttons()
        #self.myMenu2.insertWidget(1, LeftAlignedPressableLabel_composite(title, hashtag, []))
        insortWidget(self.myMenu2, btn)
        #self.myMenu2.itemAt(1).widget().setStyleSheet("background-color: rgba(0,250,0,0.4)")
        bisect.insort(self.items2, btn, lo=1, hi=len(self.items2)-1)

    def open_tract_editor(self, button=False):
        if not button:
            dialog = TractEditor(self)
        else:
            dialog = TractEditor(self, button)
        dialog.TractEdited.connect(self.replace_tract_in_toolbar)
        dialog.exec()

    def replace_tract_in_toolbar(self, ind_lbl_tpl):
        line_ind, label = ind_lbl_tpl
        # get title
        #title = tracts.loc[line_ind, 'tract name']
        # delete those edges
        # why here tho bruh
        # this shit got me fucked up g. we already have a method for removal. it handles that search bar mystery
        # why you out here copying code and shit
        # haven't you copied enough
        # shit's so weird homey.
        # use the label this would solve the fucking name changing problem
        self.remove_tract_from_toolbar(label)
        #for edg in [ed for ed in topG.graph.edges if title in topG.graph.edges[ed]['name']]:
        #    topG.REMOVE_EDGE_env(edg[0], edg[1], edg[2])
        # pop from the figure dict
        topG.graph.dict_for_figure.pop(label.text())
        # add the new tract to the toolbar
        self.add_tract_to_toolbar(line_ind)

    def open_tract_remover(self):  # opens the tract remover window
        dialog2 = TractRemover(self, [x.text() for x in self.items2[1:-1]])
        dialog2.TractRemoved.connect(self.remove_tract_from_toolbar)
        dialog2.exec()

    def remove_tract_from_toolbar(self, label):
        # reset search bars to avoid that mystery
        self.myMenu.itemAt(0).widget().clear()
        self.myMenu2.itemAt(0).widget().clear()
        if isinstance(label, TractLabelV2):
            # let's do it CLEAN:
            # first hide arrows in case they happen to be active
            label.hide_arrows()
            # remove the edges from the graph (calls the envelope's method)
            for edg in [ed for ed in topG.graph.edges if label.text() in topG.graph.edges[ed]['name']]:
                topG.REMOVE_EDGE_env(edg[0], edg[1], edg[2])
        elif isinstance(label, LeftAlignedPressableLabel_composite):
            topG.graph.hashtag_to_button_dict.pop(label.hashtag)
            topG.graph.composite_tracts.pop(label.hashtag)
            print(label, label.text())
            self.myMenu2.removeWidget(label)
            self.items2.remove(label)
            label.deleteLater()

    def open_nt_editor(self):
        dialog = NtEditor(self)
        dialog.colorFramePressed.connect(self.reinit_colorpal)
        dialog.colorFrameRemove.connect(self.reinit_colorpal)
        dialog.arrowDispChanged.connect(self.reinit_arrows)
        dialog.exec()

    def reinit_colorpal(self, nt):
        self.color_pal_inst.update_frame(nt)

    def reinit_arrows(self):
        for item in self.g_scene.items():
            if isinstance(item, CustomArrowPathItem):
                item.change_filling()

    def open_figure_window(self):
        self.show()
        self.figwind_inst.show()
        self.figwind_inst.raise_()

    def add_active_tract_to_figure_view(self):  # says to figure view, but its also to the description view
        sender = self.sender()
        self.figwind_inst.add_pathway_figure(sender)
        self.descwind_inst.add_descript(sender)

    def remove_tract_from_figure_view(self):
        self.figwind_inst.remove_pathway_figure(self.sender())
        self.descwind_inst.remove_descript(self.sender())

    def closeEvent(self, event):
        self.figwind_inst.close()
        self.descwind_inst.close()
        super().close()

    def open_nodetree(self):
        self.blah.show()

    def open_descriptions(self):
        self.descwind_inst.show()
        self.descwind_inst.raise_()
        #desc.show()

    def close_descriptions(self):
        self.descwind_inst.close()

    def open_mapsync(self):
        #self.widg.show()
        dialog = NodeIntegrator(self)
        dialog.exec()

    def open_tag_manager(self):
        dialog = TagManager(self)
        dialog.exec()

    def edge_to_arrow_item(self, edge):
        """this function takes in an edge, outputs a CustomArrowPathItem which is connected to the text displayer"""
        """it will also add the CustomArrowPathItem to the arrow_item attribute of the edge"""
        # make the edge into a line
        q_line = QLineF(topG.graph.nodes[edge[0]]['pos'][0], topG.graph.nodes[edge[0]]['pos'][1],
                        topG.graph.nodes[edge[1]]['pos'][0], topG.graph.nodes[edge[1]]['pos'][1])
        # make an arrow out of the line
        m_arrow = MyArrow(q_line.x1(), q_line.y1(), q_line.x2(), q_line.y2())
        # make a CustomArrowPathItem out of the arrow
        name = topG.graph.edges[edge]['name']  # +topG.edges[edge]['numb']
        numb = f" ({topG.graph.edges[edge]['numb']})"
        start = f"{edge[0]}"
        end = f"{edge[1]}"
        neuro_tr = topG.graph.edges[edge]['neuro_trs']
        categories = topG.graph.edges[edge]['categories']
        arr_item = CustomArrowPathItem(m_arrow, self.text_disp, name + numb, start, end, neuro_tr, categories)
        return arr_item

    def add_edge_to_UI(self, edge):
        try:
            # get the edge's pathway name
            name = topG.graph.edges[edge]['name']
            # make a CustomArrowPathItem out of the edge
            arr_item = self.edge_to_arrow_item(edge)
            # check if it's the first edge of it's pathway or areas
            first_in_p = topG.graph.attribute_dict[f"{name} (P)"] == []
            first_in_a0 = topG.graph.attribute_dict[f"{edge[0]} (A)"] == []
            first_in_a1 = topG.graph.attribute_dict[f"{edge[1]} (A)"] == []
            # thoughts-
            # check if it's the first edge of it's hashtag
            # add the custom arrow item to the edges attribute in the graph
            topG.graph.concise_attribute_update(edge[0], edge[1], edge[2], topG.graph.edges[edge]['name'],
                                                arr_item, topG.graph.edges[edge]['neuro_trs'])
            # add it into the UI
            self.g_scene.addItem(arr_item)
            # if the edge is the first of its pathway, create a pathway button for it.
            if first_in_p:
                description = topG.graph.edges[edge]['description']
                button = TractLabelV2(name, [], description)
                # insert to the menu without messing up alphabetical order
                insortWidget(self.myMenu2, button)
                # insert to the search bar options without messing up alphabetical order
                bisect.insort(self.items2, button, lo=1, hi=len(self.items2)-1)
                # plug the activation of the button to the simplified figure and description views
                button.on.connect(self.add_active_tract_to_figure_view)
                button.off.connect(self.remove_tract_from_figure_view)
                # get hashtags:
                e_hashtags = [val for val in topG.graph.edges[edge]['categories'] if val not in topG.graph.tags]
                for hashtag in e_hashtags:
                    # before adding the button into the hashtag_to_button dict,
                    # check if it is the first button to be added
                    first_in_g = topG.graph.hashtag_to_button_dict[hashtag] == []
                    if first_in_g:  # if it is the first we need to create a group button
                        try:
                            g_button = LeftAlignedPressableLabel_composite(topG.graph.composite_tracts[hashtag], hashtag)
                        except KeyError:
                            g_button = LeftAlignedPressableLabel_composite(hashtag, hashtag)
                        insortWidget(self.myMenu2, g_button)
                        bisect.insort(self.items2, g_button, lo=1, hi=len(self.items2) - 1)
                        topG.graph.group_buttons.append(g_button)
                    # now add the button to the dict
                    topG.graph.hashtag_to_button_dict[hashtag].append(button)

            # if u is the first of its area, create an area button for it
            if first_in_a0:
                regions = topG.graph.nodes[edge[0]]["region"]
                button = LeftAlignedPressableLabel_area(edge[0], regions)
                insortWidget(self.myMenu, button)
                bisect.insort(self.items, button, lo=1, hi=len(self.items) - 1)
                # handle group area button
                for reg in regions:
                    if reg in topG.graph.region_tags:
                        first_in_reg = topG.graph.hashtag_to_button_dict[reg] == []
                        if first_in_reg:  # a group button is created only if it has not already been created
                            ga_button = LeftAlignedPressableLabel_composite(reg, reg)
                            insortWidget(self.myMenu, ga_button)
                            bisect.insort(self.items, ga_button, lo=1, hi=len(self.items) - 1)
                            topG.graph.group_buttons.append(ga_button)

                        # now add the button to the dict
                        topG.graph.hashtag_to_button_dict[reg].append(button)

            # same for v
            if first_in_a1:
                regions = topG.graph.nodes[edge[1]]["region"]
                button = LeftAlignedPressableLabel_area(edge[1], regions)
                insortWidget(self.myMenu, button)
                bisect.insort(self.items, button, lo=1, hi=len(self.items) - 1)
                # handle group area button
                for reg in regions:
                    if reg in topG.graph.region_tags:
                        first_in_reg = topG.graph.hashtag_to_button_dict[reg] == []
                        if first_in_reg:
                            ga_button = LeftAlignedPressableLabel_composite(reg, reg)
                            insortWidget(self.myMenu, ga_button)
                            bisect.insort(self.items, ga_button, lo=1, hi=len(self.items) - 1)
                            topG.graph.group_buttons.append(ga_button)

                        # now add the button to the dict
                        topG.graph.hashtag_to_button_dict[reg].append(button)

        except KeyError:
            print(f"one or more of these nodes doesnt have a place on the map: {edge}")

    def remove_edge_from_UI(self, edge):
        # get the edge's pathway name
        name = edge[3]
        # get the edge's hashtags
        hashtags = edge[4]
        # check if it's areas or pathway are empty
        p_empty = topG.graph.attribute_dict[f"{name} (P)"] == []
        a0_empty = topG.graph.attribute_dict[f"{edge[0]} (A)"] == []
        a1_empty = topG.graph.attribute_dict[f"{edge[1]} (A)"] == []

        # if they are found empty, we remove the appropriate button

        if p_empty:
            for widget in self.items2[1:-1]:
                if widget.text() == name:
                    self.myMenu2.removeWidget(widget)
                    self.items2.remove(widget)
                    widget.deleteLater()
                    for hashtag in hashtags:
                        topG.graph.hashtag_to_button_dict[hashtag].remove(widget)
                        # handling the case where we have emptied a group and thus need to remove its button
                        g_empty = topG.graph.hashtag_to_button_dict[hashtag] == []
                        if g_empty:
                            # get the group's button
                            ind = topG.graph.group_buttons.index(hashtag)
                            grp_btn = topG.graph.group_buttons[ind]
                            # remove it from the UI
                            self.myMenu2.removeWidget(grp_btn)
                            self.items2.remove(grp_btn)
                            grp_btn.deleteLater()
                            # remove from group_buttons list
                            topG.graph.group_buttons.pop(ind)

        if a0_empty:
            for widget in self.items[1:-1]:
                if widget.text() == edge[0]:
                    self.myMenu.removeWidget(widget)
                    self.items.remove(widget)
                    widget.deleteLater()
                    # handling the case where we have emptied a region and thus need to delete its button
                    regions = set(topG.graph.nodes[edge[0]]['region'])
                    for reg in regions & topG.graph.region_tags:
                        # remove this area button from the region in the hashtag_to_button_dict
                        topG.graph.hashtag_to_button_dict[reg].remove(widget)
                        # check for emptiness, and handle
                        reg_empty = topG.graph.hashtag_to_button_dict[reg] == []
                        if reg_empty:
                            ind = topG.graph.group_buttons.index(reg)
                            grp_btn = topG.graph.group_buttons[ind]
                            # remove it from the UI
                            self.myMenu.removeWidget(grp_btn)
                            self.items.remove(grp_btn)
                            grp_btn.deleteLater()
                            # remove from group_buttons list
                            topG.graph.group_buttons.pop(ind)

        if a1_empty:
            for widget in self.items[1:-1]:
                if widget.text() == edge[1]:
                    self.myMenu.removeWidget(widget)
                    self.items.remove(widget)
                    widget.deleteLater()
                    # handling the case where we have emptied a region and thus need to delete its button
                    regions = set(topG.graph.nodes[edge[1]]['region'])
                    for reg in regions & topG.graph.region_tags:
                        # remove this area button from the region in the hashtag_to_button_dict
                        topG.graph.hashtag_to_button_dict[reg].remove(widget)
                        # check for emptiness, and handle
                        reg_empty = topG.graph.hashtag_to_button_dict[reg] == []
                        if reg_empty:
                            ind = topG.graph.group_buttons.index(reg)
                            grp_btn = topG.graph.group_buttons[ind]
                            # remove it from the UI
                            self.myMenu.removeWidget(grp_btn)
                            self.items.remove(grp_btn)
                            grp_btn.deleteLater()
                            # remove from group_buttons list
                            topG.graph.group_buttons.pop(ind)

    def remove1(self):
        pass


"""
PART C - ACTIVATE THE APP
"""
app = QApplication(sys.argv)
window = MainWindow()
window.showMaximized()
app.exec()
