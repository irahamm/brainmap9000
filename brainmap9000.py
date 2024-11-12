import sys
import os
from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtGui import QPen, QFont, QColor, QPainterPath, QPainterPathStroker, QPolygonF
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QPointF, QLineF, QRectF, QSize, QVariantAnimation, pyqtSignal, QTimer
import networkx as nx
import pandas as pd
import math
import xml.etree.ElementTree as ET
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
for i in range(len(areas)):
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

# create neurotransmitter palette
n_ts_palette = {
    'idk': QColor(0, 0, 0), 'GABA(-)': QColor(200, 0, 0),
    'Glutamate(+)': QColor(0, 150, 0)
}

# ADD THE TRACTS\EDGES TO THE GRAPH
for i in range(tracts.shape[0]):
    j=1
    current_area = tracts["beginning"][i]
    # add the edge
    while isinstance(tracts[f"stop{j}"][i], str):
        next_area = tracts[f"stop{j}"][i]
        exit_loop = False
        current_areas = current_area.split(r"\\")
        next_areas = next_area.split(r"\\")  # split these stops into a list
        # s = s[:-1]+s[-1].split("@")
        if '@' in current_areas[-1]:
            current_areas = current_areas[:-1] + current_areas[-1].split("@")
            neuro_ts = current_areas[-1]
            current_areas.remove(neuro_ts)
        else:
            neuro_ts = 'idk'
        if '@' in next_areas[-1]:
            next_areas = next_areas[:-1] + [next_areas[-1].split("@")[0]]
        # detect and un-include any unreal nodes
        invalid_nodes = [ar0 for ar0 in current_areas if ar0 not in topG.nodes] + [ar1 for ar1 in next_areas if ar1 not in topG.nodes]
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
        # else connect any current area with any next area
        for ar0 in current_areas:
            for ar1 in next_areas:
                topG.add_edge(ar0, ar1, name=str(tracts["tract name"][i]) + f" ({j})", neuro_trs=neuro_ts)
        # update current area
        current_area = tracts[f"stop{j}"][i]
        j += 1


# LOAD THE VECTOR GRAPHIC PATHS (in order hovering and other functionalities later on)
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
    # handle transfroming
    if tr is None:
        tr = 1.0
    else:
        tr = float(tr.strip("scale()"))
    # if it's an absolute path change its format
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
        # do it again, i know, stupid
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
    #print(svg_path)
    start_coords = (0, 0)
    for comm in svg_path:
        data = comm[2:]
        if comm[0] == "M" or comm[0] == "m":
            data = data.replace(" ", "\n")
            data = data.splitlines()
            for i in range(len(data)):
                if i == 0:
                    if comm[0] == "M":  # absolute move
                        #print(data)
                        #print(float(data[i][0:(data[i].index(",") - 1)]))
                        painter_path.moveTo(tr*float(data[i][0:(data[i].index(","))]),
                                            tr*float(data[i][(data[i].index(",") + 1):]))
                        start_coords = (tr*float(data[i][0:(data[i].index(","))]), tr*float(data[i][(data[i].index(",") + 1):]))
                    elif comm[0] == "m":  # relative move
                        painter_path.moveTo(tr*float(data[i][0:(data[i].index(","))]) + start_coords[0],
                                            tr*float(data[i][(data[i].index(",") + 1):]) + start_coords[1])
                        start_coords = (tr*float(data[i][0:(data[i].index(","))]) + start_coords[0],
                                        tr*float(data[i][(data[i].index(",") + 1):]) + start_coords[1])
                else:                 # Any subsequents are relative lineTos
                    #print(data)
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
                #bounding_rect = QRectF(center_x - rx * tr, center_y - ry * tr, rect_width, rect_height)

                start_angle = i*0
                sweep_length = 360
                painter_path.arcMoveTo(rect_x, rect_y, rect_width, rect_height, start_angle)
                painter_path.arcTo(rect_x, rect_y, rect_width, rect_height, start_angle, sweep_length)

                start_coords = (dest_x, dest_y)
        elif comm[0] == "z":
            painter_path.closeSubpath()
            start_coords = (painter_path.currentPosition().x(), painter_path.currentPosition().y())  # LOLLLL got to change this later
    return painter_path


painter_paths = []
path_centers = []
number_of_subpaths = {}
lines = []
# gather paths
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
#for name, path, transform in svg_paths:
#    number_of_subpaths[name] = path.count("m")  # this way is redundant
# very dumb way of doing it
for name, path in painter_paths:
    number_of_subpaths[name] = len(path.toSubpathPolygons())
# now gather the centers
for name, path in painter_paths:
    if name in topG.nodes:
        if number_of_subpaths[name] > 1:
            # choose the bigger polygon
            subpaths = []
            for polygon in path.toSubpathPolygons():
                subpath = QPainterPath()
                subpath.addPolygon(polygon)
                subpaths.append((subpath, calculate_path_area(subpath)))
            #print(name,subpaths)
            '''
            if [x[1] for x in subpaths].count(max([x[1] for x in subpaths])) == 2:
                left_sp = [x[0] for x in subpaths if x[0].boundingRect().x()<path.boundingRect().x()+path.boundingRect().width()//2][0]
                output = find_meatiest_center(left_sp, 20)
            else:
                output = find_meatiest_center(sorted(subpaths, key=lambda x: x[1], reverse=True)[0][0], 20)
            topG.nodes[name]['pos'] = (output.x(), output.y())
            '''
            if len(subpaths) % 2 == 0:
                ratios = [subpaths[i][1]/subpaths[0][1] for i in range(len(subpaths))]
                if all(1.5 > rat > 0.92 for rat in ratios):
                    output = find_meatiest_center(sorted(subpaths, key=lambda x: x[0].boundingRect().x(),reverse=True)[0][0], 20)
                else:
                    output = find_meatiest_center(sorted(subpaths, key=lambda x: x[1], reverse=True)[0][0], 20)
            else:
                output = find_meatiest_center(sorted(subpaths, key=lambda x: x[1], reverse=True)[0][0], 20)

            topG.nodes[name]['pos'] = (output.x(), output.y())


            #topG.nodes[name]['pos'] = (first_subpath.boundingRect().x() + first_subpath.boundingRect().width() / 2, first_subpath.boundingRect().y() + first_subpath.boundingRect().height() / 2)
        else:
            output = find_meatiest_center(path, 20)
            topG.nodes[name]['pos'] = (output.x(), output.y())
            #topG.nodes[name]['pos'] = (path.boundingRect().x() + path.boundingRect().width() / 2, path.boundingRect().y() + path.boundingRect().height() / 2)

# gather lines - we use a name_of_tract, start, end, line item tuple
# some silly shit
edges = []
for edge in topG.edges:
    try:
        lines.append((topG.edges[edge]['name'], f"{edge[0]}", f"{edge[1]}", topG.edges[edge]['neuro_trs'], QLineF(topG.nodes[edge[0]]['pos'][0], topG.nodes[edge[0]]['pos'][1],
                            topG.nodes[edge[1]]['pos'][0], topG.nodes[edge[1]]['pos'][1])))
        edges.append((edge[0], edge[1]))
    except KeyError:
        print(f"one or more of these nodes doesnt have a place on the map: {edge}")



# make lines the into arrows using this silly ol thing
class MyArrow(QPainterPath):
    def __init__(self, x1, y1, x2, y2, arrow_size=12):
        super().__init__()
        # Save the points and constrain the arrow size
        self.p1 = (x1, y1)
        self.p2 = (x2, y2)
        self.arrow_size = max(3, min(arrow_size, 30))

        # Calculate the angle of the line
        angle = math.atan2(self.p2[1] - self.p1[1], self.p2[0] - self.p1[0])

        # Calculate the endpoint of the line before the arrowhead
        #line_end_x = self.p2[0] - self.arrow_size * math.cos(angle)
        #line_end_y = self.p2[1] - self.arrow_size * math.sin(angle)

        # Draw the line up to where the arrowhead starts
        #self.moveTo(x1, y1)
        #self.lineTo(line_end_x, line_end_y)

        # Calculate the points for the arrowhead
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
        midpoint = QPointF(midpoint_x, midpoint_y)

        # Draw the arrowhead as a triangle
        self.moveTo(self.p1[0], self.p1[1])
        self.lineTo(midpoint_x, midpoint_y)
        self.lineTo(arrow_p1)
        self.lineTo(self.p2[0], self.p2[1])
        self.lineTo(arrow_p2)
        self.lineTo(midpoint_x, midpoint_y)
        self.closeSubpath()



lines_of_area_buttons = []
for i in range(len(lines)):
    lines_of_area_buttons.append((lines[i][0], lines[i][1], lines[i][2], lines[i][3],
                                  MyArrow(lines[i][4].x1(), lines[i][4].y1(), lines[i][4].x2(), lines[i][4].y2())))
    lines[i] = (lines[i][0], lines[i][1], lines[i][2], lines[i][3],
                MyArrow(lines[i][4].x1(), lines[i][4].y1(), lines[i][4].x2(), lines[i][4].y2()))

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
    def __init__(self, path: MyArrow, label: QLabel, name: str, start: str, end: str, neuro_trs: str):
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
        # in order for things to run smooth we want to set a QTimer
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

    def shape(self):   # isn't it kind of silly we calculate it inside the method?
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
# custom QLabels that are aligned to the left - one class for arrows and one for areas
# ARROWS
class LeftAlignedPressableLabel_tract(QLabel):
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
        self.mousePressEvent = self.pressed
        self.mouseReleaseEvent = self.released
        # create a toggle attribute
        self.toggle = False

    def pressed(self, event):
        pass

    def released(self, event):
        # switch toggle
        self.toggle = not self.toggle
        if self.toggle:
            for arrow in self.region:
                arrow.show()
            self.setStyleSheet("background-color: rgba(173, 216, 255, 1)")
        else:  # copy code like a maniac
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
        self.mousePressEvent = self.pressed
        self.mouseReleaseEvent = self.released
        # create a toggle attribute
        self.toggle = False

    def add_input(self, inp):
        print(f"Adding input arrow to {self.text()}: {inp.title}")
        self.inputs.append(inp)

    def add_output(self, out):
        print(f"Adding output arrow to {self.text()}: {out.title}")
        self.outputs.append(out)

    def pressed(self, event):
        pass

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


# we make custom graphics view class in order to enable zooming
class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)

    def wheelEvent(self, event):
        # check if Ctrl is pressed
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 0.8

            if event.angleDelta().y() > 0:
                self.scale(zoom_in_factor, zoom_in_factor)
            else:
                self.scale(zoom_out_factor, zoom_out_factor)
        else:
            # call the default scroll behavior if Ctrl is not pressed
            super().wheelEvent(event)


# lastly let's make a little color palette thing for the neurotransmitter
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('brainmap9000')
        # define window's size
        self.setGeometry(300, 300, 400, 400)
        # TEXT DISPLAYER
        self.text_disp = QLabel("")
        self.text_disp.setAlignment(Qt.AlignCenter | Qt.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        self.text_disp.setFont(font)
        # MAP
        g_scene = QGraphicsScene()
        pen = QPen(QColor(0, 0, 0))
        pen.setWidth(1)
        # load ze svg
        svg_map = QGraphicsSvgItem("MAP_1.svg")
        svg_map.setScale(0.28225)  # WHY this number? some "DPI" related difference? (so long as we don't figure this out, the project isn't generlizable)
        g_scene.addItem(svg_map)
        # load ze vayz
        self.path_items = []
        for name, path in painter_paths:
            self.path_items.append(CustomPathItem(path,self.text_disp, name))
        # drawwwww
        for path_item in self.path_items:
            path_item.setPen(pen)
            path_item.setBrush(QColor(0, 0, 0, 0))
            g_scene.addItem(path_item)
        # draw arrows for tract buttons
        arrow_items_tract_buttons = []
        for name, start, end, neuro_tr, line in lines:
            g_scene.addItem(CustomArrowPathItem(line, self.text_disp, name, start, end, neuro_tr))
            arrow_items_tract_buttons.append(g_scene.items()[0])
        # draw arrows for node buttons
        arrow_items = []
        for name, start, end, neuro_tr, line in lines_of_area_buttons:
            g_scene.addItem(CustomArrowPathItem(line, self.text_disp, name, start, end, neuro_tr))
            arrow_items.append(g_scene.items()[0])

        # add color palette
        self.color_pal_inst = ColorPal()
        # put graphics scene in a graphics view
        self.g_view = CustomGraphicsView(g_scene)
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
            # using set here might cause problems in displaying two identical arrows at once
            # (but we also haven't decided on how to remedy this issue)
            inputs = list(set(inputs).intersection(edges))
            outputs = list(set(outputs).intersection(edges))
            input_arrows = []
            output_arrows = []
            for edge in inputs:
                input_arrows.append(edges_arrows_dict[edge])
            for edge in outputs:
                output_arrows.append(edges_arrows_dict[edge])
            the_area_buttons_frfr.append(LeftAlignedPressableLabel_area(node, topG.nodes[node]["region"], input_arrows, output_arrows))
            #self.myMenu.addWidget(LeftAlignedPressableLabel_area(node, topG.nodes[node]["region"], input_arrows, output_arrows))
        # now load by alphabet
        for button in sorted(the_area_buttons_frfr, key=lambda x: x.text()):
            self.myMenu.addWidget(button)
        # add the buttons for the tracts
        # again let's alphabetize (honestly, not sure if this makes it less confusing)
        the_tract_buttons_frfr = []
        for tract in tracts["tract name"]:
            if isinstance(tract, str):
                tract_parts = []
                for item in arrow_items_tract_buttons:
                    if isinstance(item, CustomArrowPathItem) and tract in item.name:  # if it's an arrow that is part of this tract
                        tract_parts.append(item)   # append to 'tract parts' each arrow of the tract
                the_tract_buttons_frfr.append(LeftAlignedPressableLabel_tract(tract, tract_parts))
                #self.myMenu2.addWidget(LeftAlignedPressableLabel_tract(tract, tract_parts))  # add the button of the tract to the tract menu
        for button in sorted(the_tract_buttons_frfr, key=lambda x: x.text()):
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
        #self.setCentralWidget(self.tabs)
        layout3 = QHBoxLayout()
        layout3.addWidget(self.tabs)
        layout3.addWidget(frame)
        layout3.addWidget(Textdisp_Image)

        Bar_Buttons_Image = QWidget()
        Bar_Buttons_Image.setLayout(layout3)

        self.setCentralWidget(Bar_Buttons_Image)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.tabs.isVisible():  # yes, it's weird
            self.tabs.setFixedWidth(self.one_fifth())
            self.scroll_area.setFixedWidth(self.one_fifth())

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


"""
PART C - ACTIVATE THE APP
"""
app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
