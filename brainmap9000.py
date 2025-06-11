import sys
import os
from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtGui import QPen, QFont, QColor, QPainterPath, QPainterPathStroker, QPolygonF, QFontMetrics, QPixmap, QPainter, QIcon
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QPointF, QLineF, QRectF, QSize, QVariantAnimation, pyqtSignal, QTimer
import networkx as nx
import pandas as pd
import numpy as np
import math
import xml.etree.ElementTree as ET
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
# Now that we got that covered, let's dive in
"""
PART A - LOAD THE DATA
"""
# LOAD EDGES FILE
tracts = pd.read_csv("paths.csv")
# LOAD NODES FILE
text = open("nodes.txt")
areas = text.read()
areas = areas.replace("-", " ")
# CREATE THE GRAPH OBJECT
topG = nx.MultiDiGraph()
# FILL IN THE AREAS\NODES
'''
Explanation about the nodes file:
The nodes file is a text file which is written hierarchically, in such a way that each area that is found within the 
square brackets which follow after another area, is considered to be contained within that area. 
For example: this syntax Brain[[Forebrain][Midbrain][Hindbrain]] means that the Forebrain, the Midbrain and the
Hindbrain are all part of the Brain region. 
'''
for i in range(len(areas)):   # this loop iterates over the nodes\brain areas and adds them into the graph object
    if i == 0:
        last_s = 0
        regions = []
        continue
    # if it's a start
    if areas[i] == "[":
        # if it's not brackets
        if areas[i-1] != "]":
            # add node
            topG.add_node(areas[last_s:i].strip("["), region=regions.copy())
        # update regions
            regions.append(areas[last_s:i].strip("["))
        # anyhow update last start
        last_s = i
    elif areas[i] == "]":
        # if it's not a bracket:
        if areas[i-1] != "]":
            # add node
            topG.add_node(areas[last_s:i].strip("["), region=regions.copy())
            # update regions
            regions.append(areas[last_s:i].strip("["))
        # anyhow de-update regions
        regions.pop()

#topG.remove_node("")

# create neurotransmitter palette. this will later determine the color of the arrow heads of each neurotransmitter.
n_ts_palette = {
    'idk': QColor(0, 0, 0), 'GABA(-)': QColor(200, 0, 0),
    'Glutamate(+)': QColor(0, 150, 0)
}

# ADD THE TRACTS\EDGES TO THE GRAPH
'''
Explanation about the tracts file:
The tracts file is a csv containing known pathways. Notable variables within this csv include the tracts name, it's 
beginning and it's stops. If a given stage diverges from an area to more then one area, '\\' is used between the
afferent areas. Also, to signify the efferent neuron's neurotransmitter (if known), '@' is used at the end of the
receiving stop. 
Another symbol used is the '#' symbol. It is used for pathways which are made of existing pathways. Specifically, it
means that every pathway which includes the expression after the hashtag as one of it's categories, will be assigned as
part of this pathway.
'''
# to later deal with said 'composite' pathways we first set up a dictionary
composite_paths = {}
for i, item in enumerate(tracts["beginning"]):
    if isinstance(item, str) and "#" in item:
        # I put it in an 'name, beginning'
        composite_paths[(tracts["tract name"][i], item.strip("#"))] = []


# the loop inside this function iterates over the tracts file and adds the edges to the graph object
def df_to_edges(tracts):
    for i in range(tracts.shape[0]):
        j = 1
        current_area = tracts["beginning"][i]
        # add the edge
        while isinstance(tracts[f"stop{j}"][i], str):
            next_area = tracts[f"stop{j}"][i]
            exit_loop = False
            current_areas = current_area.split(r"\\")
            next_areas = next_area.split(r"\\")  # split these stops into a list
            if '@' in current_areas[-1]:
                current_areas = current_areas[:-1] + current_areas[-1].split("@")
                neuro_ts = current_areas[-1]
                current_areas.remove(neuro_ts)
            else:
                neuro_ts = 'idk'
            if '@' in next_areas[-1]:
                next_areas = next_areas[:-1] + [next_areas[-1].split("@")[0]]
            # detect and un-include any unreal nodes
            invalid_nodes = [ar0 for ar0 in current_areas if ar0 not in topG.nodes] + [ar1 for ar1 in next_areas if
                                                                                       ar1 not in topG.nodes]
            current_areas = [ar0 for ar0 in current_areas if ar0 in topG.nodes]
            next_areas = [ar1 for ar1 in next_areas if ar1 in topG.nodes]
            # print the invalid nodes so that I know what to fix or add
            print(f"invalid node\s:{invalid_nodes} in {tracts['tract name'][i]}") if invalid_nodes != [] else None
            if len(current_areas) == 0:
                exit_loop = True
                break
            elif len(next_areas) == 0:
                exit_loop = True
                break
            if exit_loop:
                break
            categories = [cat for cat in tracts.loc[i, "category1":"category5"] if isinstance(cat, str)]
            # else connect any current area with any next area
            for ar0 in current_areas:
                for ar1 in next_areas:
                    topG.add_edge(ar0, ar1, name=str(tracts["tract name"][i]) + f" ({j})", neuro_trs=neuro_ts,
                                  categories=categories)
            # update current area
            current_area = tracts[f"stop{j}"][i]
            j += 1


df_to_edges(tracts)  # run this function on our pathway data frame


# LOAD THE VECTOR GRAPHIC PATHS (in order to enable hovering and other functionalities later on)
def extract_svg_paths(svg_file):   # this function takes in and SVG file and extracts the paths of all labeled items
    tree = ET.parse(svg_file)
    root = tree.getroot()

    # SVG namespaces (adjust if your SVG uses different ones)
    ns = {'svg': 'http://www.w3.org/2000/svg'}

    # extract all path elements, their "d" (data) attribute, their label attribute (name), and their transform att
    paths = []
    for path_element in root.findall('.//svg:path', ns):
        d = path_element.attrib.get('d')
        label = path_element.attrib.get('{http://www.inkscape.org/namespaces/inkscape}label')
        transform = path_element.attrib.get('transform')
        if label and "text" not in label:
            paths.append((label, d, transform))
    return paths


# use the function on the map SVG
svg_file = "MAP_1.svg"
svg_paths = extract_svg_paths(svg_file)


# this function converts SVG paths into QPainterPaths
def svgpathTOqpainterpath(svg_path:str, tr):  # IMPORTANT - MAKE THIS ROBUST TO ALL SVG COMMANDS MATE
    painter_path = QPainterPath()
    # handle transforming
    if tr is None:
        tr = 1.0
    else:
        tr = float(tr.strip("scale()"))
    # split the path into lines following each command
    svg_path = svg_path.replace(" M", "\nM")
    svg_path = svg_path.replace(" m", "\nm")
    svg_path = svg_path.replace(" c", "\nc")
    svg_path = svg_path.replace(" C", "\nC")
    svg_path = svg_path.replace(" l", "\nl")
    svg_path = svg_path.replace(" L", "\nL")
    svg_path = svg_path.replace(" V", "\nV")
    svg_path = svg_path.replace(" v", "\nv")
    svg_path = svg_path.replace(" H", "\nH")
    svg_path = svg_path.replace(" h", "\nh")
    svg_path = svg_path.replace(" a", "\na")
    svg_path = svg_path.replace(" z", "\nz")
    svg_path = svg_path.splitlines()
    # if it's an absolute path change its format
    if 'M' in svg_path[0]:
        space_counter = 0
        result = []
        for command in svg_path:
            for char in command:
                if char==" ":
                    space_counter +=1
                    if space_counter % 2 == 0:
                        result.append(",")
                    else:
                        result.append(" ")
                else:
                    result.append(char)
        svg_path = "".join(result)
        # do it again (I know, stupid)
        svg_path = svg_path.replace("M", "\nM")
        svg_path = svg_path.replace("m", "\nm")
        svg_path = svg_path.replace("c", "\nc")
        svg_path = svg_path.replace("C", "\nC")
        svg_path = svg_path.replace("l", "\nl")
        svg_path = svg_path.replace("L", "\nL")
        svg_path = svg_path.replace("V", "\nV")
        svg_path = svg_path.replace("v", "\nv")
        svg_path = svg_path.replace("h", "\nh")
        svg_path = svg_path.replace("H", "\nH")
        svg_path = svg_path.replace("z", "\nz")
        svg_path = svg_path.splitlines()[1:]
    else:
        # replace first m with M
        svg_path[0] = svg_path[0].replace("m", "M")
    start_coords = (0, 0)
    # iterate over the path's commands and translate each command into an appropriate QPainterPath move
    for comm in svg_path:
        data = comm[2:]
        if comm[0] == "M" or comm[0] == "m":
            data = data.replace(" ", "\n")
            data = data.splitlines()
            for i in range(len(data)):
                if i == 0:
                    if comm[0] == "M":  # absolute move
                        painter_path.moveTo(tr*float(data[i][0:(data[i].index(","))]),
                                            tr*float(data[i][(data[i].index(",") + 1):]))
                        start_coords = (tr*float(data[i][0:(data[i].index(","))]), tr*float(data[i][(data[i].index(",") + 1):]))
                    elif comm[0] == "m":  # relative move
                        painter_path.moveTo(tr*float(data[i][0:(data[i].index(","))]) + start_coords[0],
                                            tr*float(data[i][(data[i].index(",") + 1):]) + start_coords[1])
                        start_coords = (tr*float(data[i][0:(data[i].index(","))]) + start_coords[0],
                                        tr*float(data[i][(data[i].index(",") + 1):]) + start_coords[1])
                else:                 # any subsequents are relative lineTos
                    painter_path.lineTo(tr*float(data[i][0:(data[i].index(","))]) + start_coords[0],
                                        tr*float(data[i][(data[i].index(",") + 1):]) + start_coords[1])
                    start_coords = (tr*float(data[i][0:(data[i].index(","))]) + start_coords[0],
                                    tr*float(data[i][(data[i].index(",") + 1):]) + start_coords[1])

        elif comm[0] == "c":  # if it's a curve, split the command into sub-commands. (relative move)
            data = data.replace(" ", "\n")
            data = data.splitlines()
            for i in range(0,(len(data)-1), 3):   # then, iterate using a 3 step (first two are control points, third is an end point)
                painter_path.cubicTo(
                    tr*float(data[i][0:(data[i].index(","))])+start_coords[0], tr*float(data[i][(data[i].index(",")+1):])+start_coords[1],
                    tr*float(data[i+1][0:(data[i+1].index(","))])+start_coords[0], tr*float(data[i+1][(data[i+1].index(",")+1):])+start_coords[1],
                    tr*float(data[i+2][0:(data[i+2].index(","))])+start_coords[0], tr*float(data[i+2][(data[i+2].index(",")+1):])+start_coords[1])
                start_coords = (tr*float(data[i+2][0:(data[i+2].index(","))])+start_coords[0], tr*float(data[i+2][(data[i+2].index(",")+1):])+start_coords[1])
        elif comm[0] == "C":  # if it's a curve, split the command into sub-commands. (absolute move)
            data = data.replace(" ", "\n")
            data = data.splitlines()
            for i in range(0,(len(data)-1), 3):   # then, iterate using a 3 step (first two are control points, third is an end point)
                painter_path.cubicTo(
                    tr*float(data[i][0:(data[i].index(","))]), tr*float(data[i][(data[i].index(",")+1):]),
                    tr*float(data[i+1][0:(data[i+1].index(","))]), tr*float(data[i+1][(data[i+1].index(",")+1):]),
                    tr*float(data[i+2][0:(data[i+2].index(","))]), tr*float(data[i+2][(data[i+2].index(",")+1):]))
                start_coords = (tr*float(data[i+2][0:(data[i+2].index(","))]), tr*float(data[i+2][(data[i+2].index(",")+1):]))
        elif comm[0] == "l":    # relative line move
            data = data.replace(" ", "\n")
            data = data.splitlines()
            for i in range(len(data)):
                painter_path.lineTo(tr*float(data[i][0:(data[i].index(","))])+start_coords[0], tr*float(data[i][(data[i].index(",")+1):])+start_coords[1])
                start_coords = (tr*float(data[i][0:(data[i].index(","))])+start_coords[0], tr*float(data[i][(data[i].index(",")+1):])+start_coords[1])
        elif comm[0] == "L":    # absolute line move
            data = data.replace(" ", "\n")
            data = data.splitlines()
            for i in range(len(data)):
                painter_path.lineTo(tr*float(data[i][0:(data[i].index(","))]), tr*float(data[i][(data[i].index(",")+1):]))
                start_coords = (tr*float(data[i][0:(data[i].index(","))]), tr*float(data[i][(data[i].index(",")+1):]))
        elif comm[0] == "V":
            data = data.replace(" ", "\n")
            data = data.splitlines()
            for val in data:
                painter_path.lineTo(start_coords[0], tr*float(val))
                start_coords = (start_coords[0], tr*float(val))
        elif comm[0] == "v":
            data = data.replace(" ", "\n")
            data = data.splitlines()
            for val in data:
                painter_path.lineTo(start_coords[0], start_coords[1] + tr*float(val))
                start_coords = (start_coords[0], start_coords[1] + tr*float(val))
        elif comm[0] == "h":
            data = data.replace(" ", "\n")
            data = data.splitlines()
            for val in data:
                painter_path.lineTo(start_coords[0] + tr*float(val), start_coords[1])
                start_coords = (start_coords[0] + tr*float(val), start_coords[1])
        elif comm[0] == "H":
            data = data.replace(" ", "\n")
            data = data.splitlines()
            for val in data:
                painter_path.lineTo(tr*float(val), start_coords[1])
                start_coords = (tr*float(val), start_coords[1])
        elif comm[0] == 'a':
            data = data.replace(" ", "\n")
            data = data.splitlines()
            for i in range(0, 5, 5):     # the worst, most lazy, ungeneralizable piece of code you'll ever see:
                rx, ry = float(data[i][0:(data[i].index(","))]), float(data[i][(data[i].index(",")+1):])
                angle, lrg_arc_flag, sweep_flag = float(data[i+1]), float(data[i+2]), float(data[i+3])
                dx, dy = float(data[i+4][0:(data[i+4].index(","))]), float(data[i+4][(data[i+4].index(",") + 1):])

                rect_x = start_coords[0]-2*rx*tr
                rect_y = start_coords[1]-ry*tr
                rect_width = 2 * rx * tr
                rect_height = 2 * ry * tr
                dest_x = start_coords[0] + dx * tr
                dest_y = start_coords[1] + dy * tr
                center_x = (start_coords[0] + dest_x) / 2
                center_y = (start_coords[1] + dest_y) / 2

                start_angle = i*0
                sweep_length = 360
                painter_path.arcMoveTo(rect_x, rect_y, rect_width, rect_height, start_angle)
                painter_path.arcTo(rect_x, rect_y, rect_width, rect_height, start_angle, sweep_length)

                start_coords = (dest_x, dest_y)
        elif comm[0] == "z":
            painter_path.closeSubpath()
            start_coords = (painter_path.currentPosition().x(), painter_path.currentPosition().y())
    return painter_path

# PREPARE FOR CONVERTING THE SVG PATHS, GETTING THEIR CENTERS, AND CREATING ARROW OBJECTS FOR THE EDGES
painter_paths = []
path_centers = []
number_of_subpaths = {}
lines = []
# GATHER PATHS
for name, path, transform in svg_paths:
    try:
        painter_paths.append((name, svgpathTOqpainterpath(path, transform)))
    except Exception as e:
        print(f"there's an error with {name}'s svg path: ", e)
# GATHER PATH CENTERS
# we want centers that are smart, not simply the center of the bounding rect of the shape
# so- let's use these two functions which are supposed to help us find the meatiest point in the path
# first function - estimates a polygon's area using the 'shoelace' formula
def calculate_path_area(path: QPainterPath) -> float:
    # convert QPainterPath to QPolygonF
    polygon = path.toFillPolygon()

    # use the shoelace formula to calculate the area
    area = 0.0
    n = len(polygon)
    for i in range(n):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % n]
        area += p1.x() * p2.y() - p2.x() * p1.y()

    area = round(abs(area) / 2.0, 3)
    return area


# second function - uses the first function to determine the point in the area\path which is the 'meatiest'
def find_meatiest_center(path: QPainterPath, num_of_subrecs: int) -> QPointF:
    br = path.boundingRect()
    x = br.x()
    y = br.y()
    width = br.width()
    height = br.height()
    # get meatiest X
    high_rec_areas = []
    high_centers = []
    high_recs = []
    # the following will 'divide' the path and its 'background' to sub rectangles throughout the x-axis (resulting in
    # thin, high rectangles). then, the meatiest X will be determined as that of the middle point of the rectangle which
    # is maximally filled by the part of the path which is bounded by it.
    for i in range(num_of_subrecs):
        high_rec_i = QPainterPath()
        high_rec_i.addRect(QRectF(x + width/num_of_subrecs * i, y, width / num_of_subrecs, height))
        sub_polygon_i = path.intersected(high_rec_i)
        high_rec_areas.append(calculate_path_area(sub_polygon_i))
        high_centers.append(x + (width / num_of_subrecs * (i+0.5)))
        high_recs.append(high_rec_i)
    meatiest_x = high_centers[high_rec_areas.index(max(high_rec_areas))]
    meatiest_rec = high_recs[high_rec_areas.index(max(high_rec_areas))]

    # once we got meatiest X, lets get meatiest Y (within X's rectangle)
    new_width = meatiest_rec.boundingRect().width()
    new_x = meatiest_rec.boundingRect().x()
    wide_rec_areas = []
    wide_centers = []
    for i in range(num_of_subrecs):
        wide_rec_i = QPainterPath()
        wide_rec_i.addRect(QRectF(new_x, y + height / num_of_subrecs * i, new_width, height / num_of_subrecs))
        sub_polygon_i = path.intersected(wide_rec_i)
        wide_rec_areas.append(calculate_path_area(sub_polygon_i))
        wide_centers.append(y + height / num_of_subrecs * (i + 0.5))
    max_area = max(wide_rec_areas)
    max_indices = [i for i, area in enumerate(wide_rec_areas) if area == max_area]
    # split the list
    if len(max_indices) % 2 == 1:
        meatiest_y = wide_centers[max_indices[len(max_indices)//2]]
    else:
        meatiest_y = wide_centers[max_indices[len(max_indices)//2]]

    return QPointF(meatiest_x, meatiest_y)


# DETERMINING THE PATH CENTERS (I.E. THE COORDINATE IN WHICH OUTPUT ARROW WILL START AND INPUT ARROW WILL END)
# first gather number of subpaths for each path
# now gather the centers (also gather the names of nodes which appear on the map for later use)
nodes_on_map = []
for name, path in painter_paths:
    if name in topG.nodes:
        nodes_on_map.append(name)
        if len(path.toSubpathPolygons()) > 1:   # if the path has more than one sub polygon
            # choose the bigger polygon
            subpaths = []
            for polygon in path.toSubpathPolygons():
                subpath = QPainterPath()
                subpath.addPolygon(polygon)
                subpaths.append((subpath, calculate_path_area(subpath)))
            if len(subpaths) % 2 == 0:
                ratios = [subpaths[i][1]/subpaths[0][1] for i in range(len(subpaths))]
                if all(1.5 > rat > 0.92 for rat in ratios):
                    output = find_meatiest_center(sorted(subpaths, key=lambda x: x[0].boundingRect().x(), reverse=True)[0][0], 20)
                else:
                    output = find_meatiest_center(sorted(subpaths, key=lambda x: x[1], reverse=True)[0][0], 20)
            else:
                output = find_meatiest_center(sorted(subpaths, key=lambda x: x[1], reverse=True)[0][0], 20)

            topG.nodes[name]['pos'] = (output.x(), output.y())
        else:
            output = find_meatiest_center(path, 20)
            topG.nodes[name]['pos'] = (output.x(), output.y())
# GATHER EDGES
edges = []  # this will be useful later on
for edge in topG.edges:
    try:
        lines.append((edge, QLineF(topG.nodes[edge[0]]['pos'][0], topG.nodes[edge[0]]['pos'][1],
                                   topG.nodes[edge[1]]['pos'][0], topG.nodes[edge[1]]['pos'][1])))
        edges.append((edge[0], edge[1]))
    except KeyError:
        print(f"one or more of these nodes doesnt have a place on the map: {edge}")


# make the lines into arrows using this class:
class MyArrow(QPainterPath):
    def __init__(self, x1, y1, x2, y2, arrow_size=12):
        super().__init__()
        # save the points and constrain the arrow size
        self.p1 = (x1, y1)
        self.p2 = (x2, y2)
        self.arrow_size = max(3, min(arrow_size, 30))

        # calculate the angle of the line
        angle = math.atan2(self.p2[1] - self.p1[1], self.p2[0] - self.p1[0])

        # calculate the points for the arrowhead
        arrow_p1 = QPointF(
            self.p2[0] - self.arrow_size * math.cos(angle - math.pi / 6),
            self.p2[1] - self.arrow_size * math.sin(angle - math.pi / 6)
        )
        arrow_p2 = QPointF(
            self.p2[0] - self.arrow_size * math.cos(angle + math.pi / 6),
            self.p2[1] - self.arrow_size * math.sin(angle + math.pi / 6)
        )

        midpoint_x = (arrow_p1.x() + arrow_p2.x()) / 2
        midpoint_y = (arrow_p1.y() + arrow_p2.y()) / 2

        # draw the arrowhead as a triangle
        self.moveTo(self.p1[0], self.p1[1])
        self.lineTo(midpoint_x, midpoint_y)
        self.lineTo(arrow_p1)
        self.lineTo(self.p2[0], self.p2[1])
        self.lineTo(arrow_p2)
        self.lineTo(midpoint_x, midpoint_y)
        self.closeSubpath()


# this loop makes the lines into arrows
lines_of_area_buttons = []
for i in range(len(lines)):
    lines_of_area_buttons.append((lines[i][0],
                                 MyArrow(lines[i][1].x1(), lines[i][1].y1(), lines[i][1].x2(), lines[i][1].y2())))
    lines[i] = (lines[i][0], MyArrow(lines[i][1].x1(), lines[i][1].y1(), lines[i][1].x2(), lines[i][1].y2()))


"""
PART B - DEFINE THE CLASSES
"""


class CustomPathItem(QGraphicsPathItem):    # class for the areas
    def __init__(self, path, label: QLabel, name: str):
        super().__init__(path)
        self.setAcceptHoverEvents(True)
        self.label = label
        self.name = name

    def hoverEnterEvent(self, event):
        self.setBrush(QColor(50, 25, 50, 120))
        self.label.setText(self.name)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QColor(0, 0, 0, 0))
        self.label.setText("")
        super().hoverLeaveEvent(event)


class CustomArrowPathItem(QGraphicsPathItem):      # class for the edges
    def __init__(self, path: MyArrow, label: QLabel, name: str, start: str, end: str, neuro_trs: str, categories=[]):
        super().__init__(path)
        self.setVisible(False)
        self.setAcceptHoverEvents(True)
        #self.pen1 = QPen(n_ts_palette[neuro_trs])
        self.pen1 = QPen(QColor(0,0,0))
        self.pen1.setWidth(1)
        self.pen1.setCosmetic(True)
        self.setPen(self.pen1)
        self.pen2 = QPen(QColor(0, 0, 250))
        self.pen2.setWidth(2)
        self.pen2.setCosmetic(True)
        self.label = label
        self.name = name
        self.start = start
        self.end = end
        self.path = path
        self.setBrush(n_ts_palette[neuro_trs])
        self.color = n_ts_palette[neuro_trs]
        self.categories = categories
        # in order for things to run smooth we set a QTimer
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)  # Only trigger once
        self.hover_timer.timeout.connect(self.on_hover_timeout)
        # init title
        self.title = f"{self.start}--->{self.end}, {self.name}"
        # set hover threshold
        self.hover_threshold = 3
        # the transform
        self.head_and_body = self.path.toSubpathPolygons()
        self.original_arrow_size = self.path.arrow_size

    def paint(self, painter, option, widget=None):      # this method feels quite heavy somehow. but, if every (g_view) scale
        current_scale = self.scene().views()[0].viewportTransform().m11()   # triggers an item paint event? then is it heavy?

        if getattr(self, "last_scale", None) != current_scale:
            self.last_scale = current_scale
            # recompute arrow size only if scale changed
            self.hover_threshold = 3 * (1 / current_scale)
            arrow_sz = self.original_arrow_size * (1 / (1.2*current_scale))
            self.scaled_path = MyArrow(self.path.p1[0], self.path.p1[1], self.path.p2[0], self.path.p2[1], arrow_sz)

        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawPath(self.scaled_path)

    def shape(self):
        # create a path that is wider than the actual line by adding a larger stroke
        copied_path = QPainterPath(self.path)

        # create a stroke around the line with the hover threshold added
        stroker = QPainterPathStroker()
        stroker.setWidth(self.pen1.width() + 2 * self.hover_threshold)  # increase detection width
        return stroker.createStroke(copied_path)

    def hoverEnterEvent(self, event):
        '''
        self.setPen(self.pen2)
        self.setBrush(self.pen2.color())
        self.label.setText(self.title)
        super().hoverEnterEvent(event)
        '''
        self.hover_timer.start(100)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.hover_timer.stop()

        self.setPen(self.pen1)
        self.setBrush(self.color)
        self.label.setText("")
        super().hoverLeaveEvent(event)

    def on_hover_timeout(self):
        # this function is called when the timer finishes
        self.setPen(self.pen2)
        self.setBrush(self.pen2.color())
        self.label.setText(self.title)


# FOR THE TOOLBAR ON THE LEFT OF THE APP, WE WANT TO MAKE SOME CUSTOM BUTTONS
# custom QLabels that are aligned to the left - one class for tracts and one for areas
# ARROWS
class LeftAlignedPressableLabel_tract(QLabel):
    # let's try to define a pyqt signal
    off = pyqtSignal()
    on = pyqtSignal()

    def __init__(self, text="", region=[]):
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
        if self.region:
            self.categories = region[0].categories
        else:
            self.categories=[]
        self.mouseReleaseEvent = self.released
        # create a toggle attribute
        self.toggle = False

    def released(self, event=None):
        # switch toggle
        self.toggle = not self.toggle
        if self.toggle:
            for arrow in self.region:
                arrow.show()
            self.setStyleSheet("background-color: rgba(173, 216, 255, 1)")
            self.on.emit()
        else:  # (copy code like a maniac)
            for arrow in self.region:
                arrow.hide()
            self.setStyleSheet("""
                                QLabel {
                                    background-color: white;
                                }
                                QLabel:hover {
                                    background-color: lightblue;
                                }
                            """)
            self.off.emit()


# AREAS
class LeftAlignedPressableLabel_area(QLabel):
    def __init__(self, text="", region=[], inputs=[], outputs=[]):
        # init variables
        self.region = region
        self.inputs = inputs
        self.outputs = outputs
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
        # create a toggle attribute
        self.toggle = False

    def add_input(self, inp):
        self.inputs.append(inp)

    def add_output(self, out):
        self.outputs.append(out)

    def released(self, event):
        # switch toggle
        self.toggle = not self.toggle
        if self.toggle:
            for arrow in self.inputs+self.outputs:
                arrow.show()
            self.setStyleSheet("background-color: rgba(173, 216, 255, 1)")
        else:  # copy code like a maniac
            for arrow in self.inputs+self.outputs:
                arrow.hide()
            self.setStyleSheet("""
                                QLabel {
                                    background-color: white;
                                }
                                QLabel:hover {
                                    background-color: lightblue;
                                }
                            """)


# A CLASS FOR TRACT BUTTONS WHICH ARE A GROUP OF EXISTING TRACT BUTTONS
class LeftAlignedPressableLabel_composite_tract(QLabel):
    def __init__(self, text="", sub_tracts=[]):
        self.sub_tracts = sub_tracts
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
        for button in self.sub_tracts:
            button.off.connect(self.deactivate_self)
            button.on.connect(self.group_handler)
        # set toggle attribute
        self.toggle = False

    def activate(self):
        # activates all buttons of the group
        self.setStyleSheet("background-color: rgba(230, 216, 255, 1)")
        for button in self.sub_tracts:
            button.released()
        self.num_of_subt_on = len(self.sub_tracts)

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
        for button in self.sub_tracts:
            button.released()
        self.num_of_subt_on = 0

    def group_handler(self):
        # if I got an on, add 1 to num_of_subt and check if I it its equal to group size (ie all buttons are on)
        self.num_of_subt_on += 1
        if self.num_of_subt_on == len(self.sub_tracts):
            self.setStyleSheet("background-color: rgba(230, 216, 255, 1)")
            self.toggle = True

    def deactivate_self(self):
        if self.num_of_subt_on == len(self.sub_tracts):
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
        if self.num_of_subt_on == len(self.sub_tracts) or self.num_of_subt_on == 0:
            # switch toggle
            self.toggle = not self.toggle
            if self.toggle:
                self.activate()
            else:
                self.deactivate()
        else:
            # turn on the buttons which are not currently on
            for button in self.sub_tracts:
                if button.toggle is False:
                    button.released()
            self.toggle = True


# we make a custom graphics view class in order to enable zooming
class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)

    def wheelEvent(self, event):
        # check if ctrl is pressed
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 0.8

            if event.angleDelta().y() > 0:
                self.scale(zoom_in_factor, zoom_in_factor)
            else:
                self.scale(zoom_out_factor, zoom_out_factor)
        else:
            # call the default scroll behavior if ctrl is not pressed
            super().wheelEvent(event)


# let's make a little color palette thing for the neurotransmitter
class ColorPal(QWidget):
    def __init__(self):
        super().__init__()

        self.setMouseTracking(True)
        self.setStyleSheet("background-color: rgba(230, 230, 230, 1);")

        font = QFont()
        font.setPointSize(9)
        self.setFixedSize(150, 100)

        v_layout = QVBoxLayout()
        for neuro_ts, color in n_ts_palette.items():
            h_layout = QHBoxLayout()

            label = QLabel(neuro_ts)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            label.setFont(font)

            color_frame = QFrame()
            color_frame.setFixedWidth(30)
            color_frame.setStyleSheet(f"background-color: rgba{color.getRgb()}; border: 1px solid black;")

            h_layout.addWidget(label)
            h_layout.addSpacing(1)
            h_layout.addWidget(color_frame)

            v_layout.addLayout(h_layout)

        v_layout.setSpacing(0)
        self.setLayout(v_layout)

        # animation thing
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(300)
        self.animation.valueChanged.connect(self.update_background_color)

    def enterEvent(self, event):
        self.start_color_animation(QColor(230, 230, 230), QColor(173, 216, 230))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.start_color_animation(QColor(173, 216, 230), QColor(230, 230, 230))
        super().leaveEvent(event)

    def start_color_animation(self, start_color, end_color):
        self.animation.setStartValue(start_color)
        self.animation.setEndValue(end_color)
        self.animation.start()

    def update_background_color(self, color):
        self.setStyleSheet(f"background-color: {color.name()};")


# this class is created for dynamic text displaying, which is activated by hovering over areas in the map
class ResizingTextLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.text_size = 12
        self.default_text_size = self.text_size
        self.font = QFont()
        self.font.setPointSize(self.text_size)
        self.initial_h = -1    # set initial height
        self.scale_factor = 1    # set scale factor in order to control base text size (to reduce computational load)

    def paintEvent(self, event):    # basically, it's a paint event which handles painting the text at appropriate size
        if self.text():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setFont(self.font)
            # set initial font metrics to measure the bounding rectangle the current text will take with current font
            font_metrics = QFontMetrics(self.font)
            bounding_rect = font_metrics.boundingRect(self.rect(), Qt.TextWordWrap | Qt.AlignCenter, self.text())
            # set the label's current space (rectangle)
            rect = self.rect()
            # a loop which adapts the font so the text will fit inside the labels space \ rectangle
            while rect.height() < bounding_rect.height() and self.font.pointSize()>1:
                self.text_size += math.copysign(0.2, self.height() - bounding_rect.height())
                self.font.setPointSize(int(self.text_size))
                painter.setFont(self.font)
                font_metrics = QFontMetrics(self.font)
                bounding_rect = font_metrics.boundingRect(self.rect(), Qt.TextWordWrap | Qt.AlignCenter,
                                                          self.text())

            painter.setFont(self.font)
            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.drawText(self.rect(), Qt.TextWordWrap | Qt.AlignCenter, self.text())

        else:
            self.text_size = int(12*self.scale_factor)
            self.font.setPointSize(self.text_size)
            pass

    def setText(self, text):
        super().setText(text)
        self.repaint()

    def updateTextSize(self):    # this method is triggered by a signal which is emitted by main window resize events
        # set original base_line
        if self.initial_h == -1:
            self.initial_h = self.height()
        # scale
        self.scale_factor = self.height()/self.initial_h
        self.text_size = int(12 * self.scale_factor)
        self.font.setPointSize(self.text_size)

# good. we're done defining the classes of the main program. now we define the functions and classes needed for us
# to be able to add tracts (i.e. for the 'tract adder' window to work)

# define this word binder function according to our file's syntax
def word_bind(words:list):
    s = ""
    for word in words:
        s += word + r"\\"
    s = s[:-2]
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


class RestrictedLineEdit(QLineEdit):  # a special line edit which changes colors according to word validity
    cleared = pyqtSignal()

    def __init__(self, valid_words):
        super().__init__()

        self.valid_words = valid_words
        self.completer = QCompleter(valid_words)
        self.completer.setCaseSensitivity(False)  # Case-insensitive matching
        self.completer.setFilterMode(Qt.MatchContains)
        self.setCompleter(self.completer)

        self.cleared.connect(self.reset_background)

        # Connect the editingFinished signal to validation
        self.editingFinished.connect(self.validate_input)

    def validate_input(self):
        current_text = self.text()
        if current_text not in self.valid_words:
            self.setStyleSheet("background-color: rgba(250, 0, 0, 0.5)")
        else:
            self.setStyleSheet("background-color: rgba(0, 250, 0, 0.5)")

    def clear(self):
        super().clear()
        self.cleared.emit()

    def reset_background(self):
        self.setStyleSheet("background-color: white")


class TractAdderStop(QWidget):  # a class for a "stop column" within the tract adder
    def __init__(self, stop_num, valid_words):
        super().__init__()

        # initialize things
        self.lyt = QVBoxLayout()
        self.stop_num = stop_num
        self.valid_words = valid_words
        # place to write your stop
        beginning = RestrictedLineEdit(self.valid_words)
        beginning.setPlaceholderText(self.stop_num)
        # button to add another stop
        add_area_btn = QPushButton("+")
        add_area_btn.setFixedSize(15, 15)
        add_area_btn.clicked.connect(self.add_area)
        # add the text taker and button to the layout and set it
        self.lyt.addWidget(beginning)
        self.lyt.addWidget(add_area_btn)
        self.setLayout(self.lyt)

    def add_area(self):
        beginning = RestrictedLineEdit(self.valid_words)
        beginning.setPlaceholderText(self.stop_num)
        self.lyt.insertWidget(self.lyt.count()-1, beginning)


class SuccessfulPathwayAdditionMsg(QDialog):  # popup window for a successful tract addition
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


class InvalidPathwayAdditionError(QDialog):   # popup window for an invalid tract
    def __init__(self):
        super().__init__()

        self.setWindowTitle("invalid input")
        self.setGeometry(150, 150, 300, 80)

        label = QLabel("invalid pathway input!")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: rgba(250, 0, 0, 0.5)")
        cont_layout = QVBoxLayout()
        cont_layout.addWidget(label)
        self.setLayout(cont_layout)


class InvalidPathwayTitleError(QDialog):  # another popup window for an invalid tract
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


class TractAdder(QDialog):  # the tract adder window
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
        self.bottom_layout = QHBoxLayout()
        self.whole_layout = QVBoxLayout()
        # first let's handle the tract title-
        title_line_edit = QLineEdit()
        title_line_edit.setPlaceholderText("tract name")
        # each stop is in fact a vertical layout \ 'column'. look at the TractAdderStop class for more information
        self.valid_words = nodes_on_map
        bgn = TractAdderStop("beginning", self.valid_words)
        stop1 = TractAdderStop("stop1", self.valid_words)
        add_tract_btn = QPushButton("Add Tract")
        add_tract_btn.clicked.connect(self.AddTractToPathwaysFile)
        # create a "+" button
        plus_btn = QPushButton("+")
        plus_btn.clicked.connect(self.AnotherOne)
        # set up layouts
        self.title_layout.addWidget(title_line_edit)
        self.title_layout.addStretch()
        self.top_layout.addWidget(bgn)
        self.top_layout.addWidget(stop1)
        self.top_layout.addWidget(plus_btn)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(add_tract_btn)
        title_container = QWidget()
        top_container = QWidget()
        bot_container = QWidget()
        title_container.setLayout(self.title_layout)
        top_container.setLayout(self.top_layout)
        bot_container.setLayout(self.bottom_layout)
        self.whole_layout.addWidget(title_container)
        self.whole_layout.addWidget(top_container)
        self.whole_layout.addWidget(bot_container)
        self.setLayout(self.whole_layout)

    def AnotherOne(self):  # this method adds a stop to the layout
        if self.top_layout.count() == (len(tracts.columns) - self.beginning_col_i):
            stop = TractAdderStop(f"stop{self.top_layout.count()-1}", self.valid_words)
            self.top_layout.insertWidget(self.top_layout.count() - 1, stop)
            btn = self.top_layout.itemAt(self.top_layout.count()-1).widget()
            self.top_layout.removeWidget(btn)
        else:
            stop = TractAdderStop(f"stop{self.top_layout.count() - 1}", self.valid_words)
            self.top_layout.insertWidget(self.top_layout.count() - 1, stop)

    def AddTractToPathwaysFile(self):  # this method handles tract addition attempts
        row = [np.nan]*(tracts.shape[1] - self.beginning_col_i)
        clear_me = []
        # get the row
        for col_i in range(self.top_layout.count()):
            if not isinstance(self.top_layout.itemAt(col_i).widget(), QPushButton):
                col = self.top_layout.itemAt(col_i)
                col = col.widget()
                col = col.layout()
                col_text = [col.itemAt(i).widget().text() for i in range(col.count() - 1)]
                row[col_i] = col_text
                # clear it
                clear_me.append([col.itemAt(i).widget() for i in range(col.count() - 1)])
        # turn spaces into nans
        row = list(map(lambda x: np.nan if x == [''] else x, row))
        # get the name of the tract
        title = self.title_layout.itemAt(0).widget()
        if title.text() == "":
            self.invalid_title_error()
        elif valid_line_check(row) and valid_node_check(row, self.valid_words):
            r = tracts.shape[0]
            tracts.loc[r] = [None] * len(tracts.columns)  # make a new row
            for i, stopCol in enumerate(row):
                if isinstance(stopCol, type(np.nan)):
                    tracts.loc[r, tracts.columns[i + self.beginning_col_i]] = np.nan
                else:
                    tracts.loc[r, tracts.columns[i + self.beginning_col_i]] = word_bind(stopCol)
            tracts['tract name'][r] = title.text()
            tracts.to_csv("paths.csv", index=False)
            # integrate the new tract into the software without having to restart using the signal we defined
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
        dialog = InvalidPathwayTitleError()
        dialog.exec()

    def invalidinputerror(self):
        dialog2 = InvalidPathwayAdditionError()
        dialog2.exec()

    def valid_addition_msg(self, pthway_title):
        dialog3 = SuccessfulPathwayAdditionMsg(pthway_title)
        dialog3.exec()


class SuccessfulPathwayRemovalMsg(QDialog):  # popup window for when a tract has been removed
    def __init__(self, tract_name):
        super().__init__()

        self.setWindowTitle("invalid input")
        self.setGeometry(150, 150, 300, 80)

        label = QLabel(f"{tract_name} was removed")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: rgba(250, 250, 0, 0.5)")
        cont_layout = QVBoxLayout()
        cont_layout.addWidget(label)
        self.setLayout(cont_layout)


class TractRemover(QDialog):  # the tract remover window
    # we define a tract removal signal in order for the tract remover to be able to interact with the main
    # window
    TractRemoved = pyqtSignal(str)

    def __init__(self, parent, valid_titles):
        super().__init__(parent)
        self.setWindowTitle("Tract Remover")
        self.setGeometry(150, 150, 600, 120)

        # this index will be useful later on
        #self.beginning_col_i = tracts.columns.get_loc('beginning')

        # init valid pathway titles
        self.valid_titles = valid_titles
        # the main layouts
        self.title_layout = QHBoxLayout()
        #self.top_layout = QHBoxLayout() (I left this in for the day i'll make the tract remover into a tract editor)
        self.bottom_layout = QHBoxLayout()
        self.whole_layout = QVBoxLayout()
        # first let's handle the tract title-
        #tract_titles = list(x for x in tracts['tract name'] if not isinstance(x, type(np.nan)))
        #print(f"tract titles:{tract_titles}")
        title_line_edit = RestrictedLineEdit(self.valid_titles)
        title_line_edit.setPlaceholderText("tract name")
        # each stop is in fact a vertical layout \ 'column'. look at the TractAdderStop class for more information
        #self.valid_words = nodes_on_map
        #bgn = TractAdderStop("beginning", self.valid_words)
        #stop1 = TractAdderStop("stop1", self.valid_words)
        remove_tract_btn = QPushButton("Remove Tract")
        remove_tract_btn.clicked.connect(self.RemoveTractFromPathwaysFile)
        # create a "+" button
        #plus_btn = QPushButton("+")
        #plus_btn.clicked.connect(self.AnotherOne)
        # set up layouts
        self.title_layout.addWidget(title_line_edit)
        self.title_layout.addStretch()
        #self.top_layout.addWidget(bgn)
        #self.top_layout.addWidget(stop1)
        #self.top_layout.addWidget(plus_btn)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(remove_tract_btn)
        title_container = QWidget()
        #top_container = QWidget()
        bot_container = QWidget()
        title_container.setLayout(self.title_layout)
        #top_container.setLayout(self.top_layout)
        bot_container.setLayout(self.bottom_layout)
        self.whole_layout.addWidget(title_container)
        #self.whole_layout.addWidget(top_container)
        self.whole_layout.addWidget(bot_container)
        self.setLayout(self.whole_layout)

    def invalid_title_error(self):
        dialog = InvalidPathwayTitleError()
        dialog.exec()

    def valid_removal_msg(self, pthway_title):
        dialog3 = SuccessfulPathwayRemovalMsg(pthway_title)
        dialog3.exec()

    def RemoveTractFromPathwaysFile(self):  # this method handles tract removal attempts
        title = self.title_layout.itemAt(0).widget()
        # check if a valid title was entered
        if title.text() not in self.valid_titles:
            self.invalid_title_error()
        else:
            ind = tracts.index[tracts["tract name"] == title.text()].tolist()[0]
            # remove the pathway from the file
            tracts.drop(index=ind, inplace=True)
            tracts.to_csv("paths.csv", index=False)
            self.valid_removal_msg(pthway_title=title.text())
            # remove the pathway from the toolbar
            self.TractRemoved.emit(title.text())
            # clear?
            title.clear()


# DEFINE THE MAIN WINDOW
class MainWindow(QMainWindow):
    window_resize_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle('brainmap9000')
        # define window's size
        self.setGeometry(300, 300, 400, 400)
        # set icon
        self.setWindowIcon(QIcon("icon\\icon.ico"))
        # TEXT DISPLAYER
        self.text_disp = ResizingTextLabel("")
        #self.text_disp = QLabel("")
        self.text_disp.setFixedHeight(int(self.height()/15))
        self.text_disp.setWordWrap(True)
        # resizing signal
        self.window_resize_signal.connect(self.text_disp.updateTextSize)
        # MAP
        self.g_scene = QGraphicsScene()
        pen = QPen(QColor(0, 0, 0))
        pen.setWidth(1)
        # load ze svg
        svg_map = QGraphicsSvgItem("MAP_1.svg")
        '''
        IMPORTANT- I figured out the following scale number numerically and I still didn't find out why it might be a
        DPI related difference between the way QPainterPaths load and how an SVG item loads. 
        # This is important because until this is not figured out the project CANNOT generalize to any other map.
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
        # draw arrows for tract buttons
        arrow_items_tract_buttons = []
        for edge, line in lines:
            name = topG.edges[edge]['name']
            start = f"{edge[0]}"
            end = f"{edge[1]}"
            neuro_tr = topG.edges[edge]['neuro_trs']
            categories = topG.edges[edge]['categories']
            self.g_scene.addItem(CustomArrowPathItem(line, self.text_disp, name, start, end, neuro_tr, categories))
            arrow_items_tract_buttons.append(self.g_scene.items()[0])
        # draw arrows for node buttons
        arrow_items = []
        for edge, line in lines_of_area_buttons:
            name = topG.edges[edge]['name']
            start = f"{edge[0]}"
            end = f"{edge[1]}"
            neuro_tr = topG.edges[edge]['neuro_trs']
            self.g_scene.addItem(CustomArrowPathItem(line, self.text_disp, name, start, end, neuro_tr))
            arrow_items.append(self.g_scene.items()[0])

        # add color palette
        self.color_pal_inst = ColorPal()
        # put graphics scene in a graphics view
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
        self.tabs = QTabWidget()
        # now create to two tabs-one for areas and one for pathways
        # create layout
        self.myMenu = QVBoxLayout()
        self.myMenu2 = QVBoxLayout()
        # set size of spaces between the options
        self.myMenu.setSpacing(5)
        self.myMenu2.setSpacing(5)
        # add a search bar
        searchbar = QLineEdit()
        searchbar.setPlaceholderText("search me...")
        searchbar.textChanged.connect(self.search)
        self.myMenu.addWidget(searchbar)
        searchbar2 = QLineEdit()
        searchbar2.setPlaceholderText("search me...")
        searchbar2.textChanged.connect(self.search2)
        self.myMenu2.addWidget(searchbar2)
        # add the buttons for the areas.
        edges_arrows_dict = {edges[i]:arrow_items[i] for i in range(len(edges))}
        # we want to load em in alphabetical order so let's make another list yey
        the_area_buttons_frfr = []
        for node in [x for x in topG.nodes if list(topG.in_edges(x))+list(topG.out_edges(x))!=[]]:
            # inputs and outputs
            inputs = topG.in_edges(node)
            outputs = topG.out_edges(node)

            inputs = list(set(inputs).intersection(edges))
            outputs = list(set(outputs).intersection(edges))
            input_arrows = []
            output_arrows = []
            for edge in inputs:
                input_arrows.append(edges_arrows_dict[edge])
            for edge in outputs:
                output_arrows.append(edges_arrows_dict[edge])
            the_area_buttons_frfr.append(LeftAlignedPressableLabel_area(node, topG.nodes[node]["region"], input_arrows, output_arrows))
        # now load by alphabet
        for button in sorted(the_area_buttons_frfr, key=lambda x: x.text()):
            self.myMenu.addWidget(button)
        # create the buttons for the tracts
        the_tract_buttons_frfr = []
        for tract in tracts['tract name']:
            if isinstance(tract, str):
                tract_parts = []
                for item in arrow_items_tract_buttons:
                    if isinstance(item, CustomArrowPathItem) and tract in item.name:  # if it's an arrow that is part of this tract
                        tract_parts.append(item)   # append to 'tract parts' each arrow of the tract
                the_tract_buttons_frfr.append(LeftAlignedPressableLabel_tract(tract, tract_parts))
        # alphabetize
        the_tract_buttons_frfr = sorted(the_tract_buttons_frfr, key=lambda x: x.text())
        # now add 'group buttons'
        for key in composite_paths.keys():
            for item in the_tract_buttons_frfr:
                try:
                    if str(key[1]) in item.categories:
                        composite_paths[key].append(item)
                except AttributeError:
                    continue
            index = [x.text() for x in the_tract_buttons_frfr].index(key[0])
            the_tract_buttons_frfr[index] = LeftAlignedPressableLabel_composite_tract(str(key[0]), composite_paths[key])

        # finally, add the tract buttons
        for button in the_tract_buttons_frfr:
            if isinstance(button, LeftAlignedPressableLabel_tract) and button.region==[]:
                print(f"will not include this empty button: {button.text()}")
            else:
                self.myMenu2.addWidget(button)
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
        layout3 = QHBoxLayout()
        layout3.addWidget(self.tabs)
        layout3.addWidget(frame)
        layout3.addWidget(Textdisp_Image)

        Bar_Buttons_Image = QWidget()
        Bar_Buttons_Image.setLayout(layout3)

        self.setCentralWidget(Bar_Buttons_Image)

        # add the menu from which we can add a tract
        file_menu = QMenu("File", self)
        option1 = QAction("Add a Tract\Pathway", self)
        option2 = QAction("Remove", self)
        file_menu.addAction(option1)
        file_menu.addAction(option2)
        option1.triggered.connect(self.open_tract_adder)
        option2.triggered.connect(self.open_tract_remover)
        self.menuBar().addMenu(file_menu)

        # init dialog windows
        self.dialog = TractAdder()
        self.dialog2 = TractRemover(self, [x.text() for x in self.items2[1:-1]])

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
        for item in self.items2[1:-1]:    # (the layouts items not including the search bar and the stretcher)
            item.setVisible(text.lower() in item.text().lower())

    def one_fifth(self):
        # returns one fifth of window's current width
        # this might be retarded, but it works
        return int(self.width()/5)

    def open_tract_adder(self):  # opens the tract adder window
        self.dialog.TractAdded.connect(self.add_tract_to_toolbar)
        self.dialog.exec()

    def add_tract_to_toolbar(self):
        # translate last line (which was just added) to edges
        df_to_edges(tracts.iloc[[-1]].reset_index(drop=True))
        title = tracts.iloc[-1]['tract name']
        arrows = []
        for edg in topG.edges:  # make lines out of edges
            if title in topG.edges[edg]['name']:
                arrows.append((edg, QLineF(topG.nodes[edg[0]]['pos'][0], topG.nodes[edg[0]]['pos'][1],
                                           topG.nodes[edg[1]]['pos'][0], topG.nodes[edg[1]]['pos'][1])))

        for i in range(len(arrows)):  # make arrows out of lines
            arrows[i] = (arrows[i][0], MyArrow(arrows[i][1].x1(), arrows[i][1].y1(), arrows[i][1].x2(), arrows[i][1].y2()))
        arrow_items_for_tract_buttons = []
        for edge, line in arrows:  # make CustomArrowPathItems out of arrows and add them to the g_scene
            name = topG.edges[edge]['name']
            start = f"{edge[0]}"
            end = f"{edge[1]}"
            neuro_tr = topG.edges[edge]['neuro_trs']
            categories = topG.edges[edge]['categories']
            self.g_scene.addItem(CustomArrowPathItem(line, self.text_disp, name, start, end, neuro_tr, categories))
            arrow_items_for_tract_buttons.append(self.g_scene.items()[0])

        tract_parts = []
        for item in arrow_items_for_tract_buttons:
            tract_parts.append(item)
        # make a button and upgrade toolbar and searchbar
        self.myMenu2.insertWidget(1, LeftAlignedPressableLabel_tract(title, tract_parts))
        itm = self.myMenu2.itemAt(1).widget()
        itm.setStyleSheet("background-color: rgba(0,250,0,0.4)")

    def open_tract_remover(self):  # opens the tract adder window
        self.dialog2.TractRemoved.connect(self.remove_tract_from_toolbar)
        self.dialog2.exec()

    def remove_tract_from_toolbar(self, title):
        # remove label (title is stored in the signal)
        for i in range(self.myMenu2.count()):
            item = self.myMenu2.itemAt(i).widget()
            if isinstance(item, LeftAlignedPressableLabel_tract):
                if item.text()==title:
                    self.myMenu2.removeWidget(item)
                    self.items2.pop(i)
                    break

        '''
        df_to_edges(tracts.iloc[[-1]].reset_index(drop=True))
        title = tracts.iloc[-1]['tract name']
        arrows = []
        for edg in topG.edges:  # make lines out of edges
            if title in topG.edges[edg]['name']:
                arrows.append((edg, QLineF(topG.nodes[edg[0]]['pos'][0], topG.nodes[edg[0]]['pos'][1],
                                           topG.nodes[edg[1]]['pos'][0], topG.nodes[edg[1]]['pos'][1])))

        for i in range(len(arrows)):  # make arrows out of lines
            arrows[i] = (arrows[i][0], MyArrow(arrows[i][1].x1(), arrows[i][1].y1(), arrows[i][1].x2(), arrows[i][1].y2()))
        arrow_items_for_tract_buttons = []
        for edge, line in arrows:  # make CustomArrowPathItems out of arrows and add them to the g_scene
            name = topG.edges[edge]['name']
            start = f"{edge[0]}"
            end = f"{edge[1]}"
            neuro_tr = topG.edges[edge]['neuro_trs']
            categories = topG.edges[edge]['categories']
            self.g_scene.addItem(CustomArrowPathItem(line, self.text_disp, name, start, end, neuro_tr, categories))
            arrow_items_for_tract_buttons.append(self.g_scene.items()[0])
        '''


"""
PART C - ACTIVATE THE APP
"""
app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
