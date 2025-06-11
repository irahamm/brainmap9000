import networkx as nx
import pandas as pd
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from PyQt5.QtCore import QPointF, QRectF, pyqtSignal, QObject
from PyQt5.QtGui import QPainterPath
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
THIS FILE LOADS THE DATA AND CONTAINS ALL THE DATA STRUCTURE VARIABLES
"""


# EXPLANATION - The main data structure of this project is a subclass of nx.MultiDiGraph class. The reason I subclass
# it is to add some functionality (namely the 'attribute_dict' dictionary) that would later enable the graphic elements
# in the GUI to comfortably adapt to possible changes in the data that the user has caused.
# LET'S DEFINE THE SAID CLASS-
class AttributeTrackingGraph(nx.MultiDiGraph):
    def __init__(self):
        super().__init__()
        # Init the composite_tracts dictionary. This holds hashtag names as keys, group titles as values.
        self.composite_tracts = {}
        # Init the attribute dict. this dictionary will include pathways and areas as keys and lists of arrow items
        # (which are graphical representations of edges) as values.
        # It will be the main data structure the GUI elements (namely tract and area buttons) interact with.
        self.attribute_dict = defaultdict(list)
        # Init figure dict. This will be useful for the simplified figure window.
        self.dict_for_figure = defaultdict(lambda: defaultdict(lambda: [set(), None]))
        # Init a tracts by hashtag dict. Hashtags as keys, buttons of pathway names with those hashtags as values
        self.hashtag_to_button_dict = defaultdict(list)
        # Init a set for tags (such as Motor, Sensory, etc.)
        self.tags = set()
        # Hardcode area tags
        self.region_tags = {'Hypothalamus', 'Thalamus', 'Cerebellum', 'Pons', 'Medulla', 'Midbrain', 'Frontal Lobe',
                            'Parietal Lobe', 'Occipital Lobe', 'Temporal Lobe', 'Basal Ganglia', 'Spinal Cord', 'BOB'}
        # Init a list for group buttons.
        self.group_buttons = []  # (this is somewhat sus because I don't remember using this in the comptract adder)

    def add_edge(self, u, v, key=None, **attr):
        super().add_edge(u, v, key=key, **attr)
        pathway_name = attr['name']
        number = attr['numb']
        neuro_ts = attr['neuro_trs']
        # update the figure dict
        self.dict_for_figure[pathway_name][number][0].add(u)
        self.dict_for_figure[pathway_name][number+1][0].add(v)
        self.dict_for_figure[pathway_name][number][1] = neuro_ts

    def remove_edge(self, u, v, key=None):
        # we assume the program did provide a key here, since we would be referring to a specific edge through
        # it's title. I won't change it to non-default though, just in-case that could screw something else up.
        data = self.get_edge_data(u, v, key)
        arr_item = data['arrow_item']
        pathway_name = data['name']
        # update the attribute dict
        try:
            self.attribute_dict[pathway_name+" (P)"].remove(arr_item)
            self.attribute_dict[u+" (A)"].remove(arr_item)
            self.attribute_dict[v+" (A)"].remove(arr_item)
        except ValueError:
            print("error occurred with this edge: ", u, v, pathway_name)
        super().remove_edge(u, v, key)

    def concise_attribute_update(self, u, v, key, pathway_name: str, arr_item, neuro_ts):
        """this method updates the arrow_item attribute of a node and applies that change to the attribute_dict"""
        # first, update regularly
        self.edges[(u, v, key)]['arrow_item'] = arr_item
        # then, update attribute dict with the graphic representation of this edge
        self.attribute_dict[pathway_name+" (P)"].append(arr_item)  # P for pathway
        self.attribute_dict[u+" (A)"].append(arr_item)  # A for area (because we might have a node and a pathway which
        self.attribute_dict[v+" (A)"].append(arr_item)  # have the same name)


class GraphEnvelope(QObject):
    """this class is pyqt5 object which essentially warps around a nx.graph and emits signals when the nx.graph is
     being altered"""
    """the class enables us to dynamically interact with UI when we want to make changes to the data"""
    edgeAdded = pyqtSignal(tuple)
    edgeRemoved = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.graph = AttributeTrackingGraph()

    def ADD_EDGE_env(self, u, v, key=0, **attr):
        self.graph.add_edge(u, v, key=key, **attr)
        self.edgeAdded.emit((u, v, key))

    def REMOVE_EDGE_env(self, u, v, key=0):
        name = self.graph.edges[(u, v, key)]['name']
        hashtags = [val for val in self.graph.edges[(u, v, key)]['categories'] if val not in self.graph.tags]
        self.graph.remove_edge(u, v, key=key)
        self.edgeRemoved.emit((u, v, key, name, hashtags))


# CREATE THE GRAPH OBJECT
topG = GraphEnvelope()
rel_start = os.path.join("NODES")


# FILL IN THE AREAS\NODES
def fill_nx_graph(path:str, empty_graph:nx.Graph, items=None):
    # this recursive function takes an empty graph and fills it with nodes based on folder hierarchy
    if items is None:
        # initialize the sorted list of items in the folder
        items = sorted(os.listdir(path))

    if not items:
        return  # base case: no more items to process

    # process the first item
    first_item = items[0]
    item_path = os.path.join(path, first_item)

    if os.path.isdir(item_path):  # only folders
        empty_graph.add_node(first_item, region=path.split("\\"))
        fill_nx_graph(item_path, empty_graph)

    fill_nx_graph(path, empty_graph, items[1:])


# run the function above on our empty graph- notice- we are running it on the nx.graph, not on the envelope
fill_nx_graph(rel_start, topG.graph)
# LOAD EDGES\TRACTS FILE
tracts = pd.read_csv("paths.csv")


# the loop inside this function iterates over the tracts file and adds the edges to the graph object. this function
# calls the envelope, not solely the nx.graph. We call this function at the main window after the GUI framework has
# been set up.
# we will use this at a later stage
def df_to_edges(tracts):
    """this function renders a dataframe containing tracts into edges in the nx.graph through the envelopes methods"""
    for i in range(tracts.shape[0]):
        j = 1
        current_area = tracts["beginning"][i]
        # if it's a group tract, store it in the composite tracts dict
        if isinstance(current_area, str):
            if "#" in current_area:
                topG.graph.composite_tracts.update({current_area.strip("#"): tracts["tract name"][i]})
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
            invalid_nodes = [ar0 for ar0 in current_areas if ar0 not in topG.graph.nodes] + [ar1 for ar1 in next_areas if
                                                                                       ar1 not in topG.graph.nodes]
            current_areas = [ar0 for ar0 in current_areas if ar0 in topG.graph.nodes]
            next_areas = [ar1 for ar1 in next_areas if ar1 in topG.graph.nodes]
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

            categories = []
            if isinstance(tracts.loc[i, "tags"], str):
                lst = tracts.loc[i, "tags"].split(", ")
                categories += lst
                for elm in lst:
                    topG.graph.tags.add(elm)
            if isinstance(tracts.loc[i, "hashtags"], str):
                lst = tracts.loc[i, "hashtags"].split(", ")
                #for elm in lst:
                #    topG.graph.hashtag_to_name_dict[elm].append(str(tracts["tract name"][i]))
                categories += lst
            #for lst in [cat.split(", ") for cat in tracts.loc[i, "tags":"hashtags"] if isinstance(cat, str)]:
            #    categories += lst
            # else connect any current area with any next area
            for ar0 in current_areas:
                for ar1 in next_areas:
                    # calls the envelope's method (which will in turn call add_edge method of the nx graph, and emit)
                    topG.ADD_EDGE_env(ar0, ar1, name=str(tracts["tract name"][i]), neuro_trs=neuro_ts,
                                  categories=categories, numb=j, arrow_item=[], description=str(tracts["description"][i]))
            # update current area
            current_area = tracts[f"stop{j}"][i]
            j += 1


# to later deal with said 'composite' pathways we first set up a dictionary
'''
composite_paths = {}
for i, item in enumerate(tracts["beginning"]):
    if isinstance(item, str) and "#" in item:
        # I put it in a 'name, beginning' tuple
        #composite_paths[(tracts["tract name"][i], item.strip("#"))] = []
        topG.graph.composite_tracts.update({(tracts["tract name"][i], item.strip("#")): []})
'''


# another function which checks for isolated nodes which we will use later
def check_for_isolated_nodes(tracts:pd.DataFrame):
    nodes = []
    bgn = tracts.at[0, "beginning"]
    nodes.append(bgn[:bgn.index('@')])
    j = 1
    while isinstance(tracts.at[0, f"stop{j}"], str):
        stop = tracts.at[0, f"stop{j}"]
        if '@' in stop:
            nodes.append(stop[:stop.index("@")])
        else:
            nodes.append(stop)
        j += 1
    nodes = sum([x.split("\\\\") for x in nodes], [])
    output = []
    for node in nodes:
        if node in list(nx.isolates(topG.graph)):
            output.append(node)
    return output


# LOAD NEUROTRANSMITTER FILE
nt_data = pd.read_csv("nt_palette.csv")
n_ts_palette = {}
for i in range(nt_data.shape[0]):
    n_ts_palette.update({nt_data['neurotransmitter'][i]: nt_data['color'][i]})


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
        if label and "text" not in label and "path" not in label:
            paths.append((label, d, transform))
    return paths


# use the function on the map SVG
svg_file = "MAP_1.svg"
svg_paths = extract_svg_paths(svg_file)


# this function converts SVG paths into QPainterPaths
def svgpathTOqpainterpath(svg_path:str, tr):  # IMPORTANT - MAKE THIS ROBUST TO ALL SVG COMMANDS
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
# then gather the centers (also gather the names of nodes which appear on the map for later use)
# we make this into a function so we can use it later
nodes_on_map = []
def store_path_centers_in_graph(painter_paths):
    for name, path in painter_paths:
        if name in topG.graph.nodes:
            # option: (add this to cond)  and 'pos' not in topG.nodes
            nodes_on_map.append(name)
            if len(path.toSubpathPolygons()) > 1:  # if the path has more than one sub polygon
                # choose the bigger polygon
                subpaths = []
                for polygon in path.toSubpathPolygons():
                    subpath = QPainterPath()
                    subpath.addPolygon(polygon)
                    subpaths.append((subpath, calculate_path_area(subpath)))
                if len(subpaths) % 2 == 0:
                    ratios = [subpaths[i][1] / subpaths[0][1] for i in range(len(subpaths))]
                    if all(1.5 > rat > 0.92 for rat in ratios):
                        output = find_meatiest_center(
                            sorted(subpaths, key=lambda x: x[0].boundingRect().x(), reverse=True)[0][0], 20)
                    else:
                        output = find_meatiest_center(sorted(subpaths, key=lambda x: x[1], reverse=True)[0][0], 20)
                else:
                    output = find_meatiest_center(sorted(subpaths, key=lambda x: x[1], reverse=True)[0][0], 20)

                topG.graph.nodes[name]['pos'] = (output.x(), output.y())
            else:
                output = find_meatiest_center(path, 20)
                topG.graph.nodes[name]['pos'] = (output.x(), output.y())


# run it on our painter paths list
store_path_centers_in_graph(painter_paths=painter_paths)


# make the lines into arrows using this class:

# this loop makes the lines into arrows
#for i in range(len(lines)):
#    lines[i] = (lines[i][0], MyArrow(lines[i][1].x1(), lines[i][1].y1(), lines[i][1].x2(), lines[i][1].y2()))
#    lines[i] = (lines[i][0], MyArrow(lines[i][1].x1(), lines[i][1].y1(), lines[i][1].x2(), lines[i][1].y2()))
