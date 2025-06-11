from PyQt5.QtGui import QPen, QFont, QColor, QPainterPath, QPainterPathStroker,  QFontMetrics, QPainter
from PyQt5.QtWidgets import QLabel, QGraphicsPathItem, QWidget, QVBoxLayout, QFrame, QHBoxLayout
from PyQt5.QtCore import Qt, QVariantAnimation, QTimer, QPointF
from data import n_ts_palette
import math
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
THIS FILE CONTAINS ALL CLASSES WHICH ARE CONTAINED IN THE MAP
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


# WE WILL NOW DEFINE TWO ARROW CLASSES. DON'T TRY TO UNDERSTAND WHY.
class MyArrow(QPainterPath):
    def __init__(self, x1, y1, x2, y2, arrow_size=20):
        super().__init__()
        # save the points and constrain the arrow size
        self.p1 = (x1, y1)
        self.p2 = (x2, y2)
        self.arrow_size = max(5, min(arrow_size, 35))

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


class CustomArrowPathItem(QGraphicsPathItem):      # class for the edges
    def __init__(self, path, label: QLabel, name: str, start: str, end: str, neuro_trs: str, categories=[]):
        super().__init__(path)
        self.setVisible(False)
        self.setAcceptHoverEvents(True)
        self.pen1 = QPen(QColor(0, 0, 0))
        self.pen1.setWidth(1)
        self.pen1.setCosmetic(True)
        self.setPen(self.pen1)
        self.pen2 = QPen(QColor(0, 0, 250))
        self.pen2.setWidth(2)
        self.fill_toggle = False  # if this is on this means whole arrow painting, if not, just the head
        self.pen2.setCosmetic(True)
        self.label = label
        self.name = name
        self.start = start
        self.end = end
        self.path = path
        self.neuro_trs = neuro_trs
        self.active_pointers = 0  # set active pointers variable - the number of labels\buttons currently causing the activation of this arrow
        try:  # set color according to neuro-transmitter
            self.color = QColor(n_ts_palette[neuro_trs])
        except KeyError:  # if the neuro-transmitter does not exist in our palette set it to default
            self.color = QColor(n_ts_palette['idk'])
        self.setBrush(self.color)
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

    def add_active_pointer(self):
        if not self.isVisible():
            self.show()
        self.active_pointers += 1

    def decrease_active_pointer(self):
        self.active_pointers -= 1
        if self.active_pointers == 0:
            self.hide()

    def show(self):
        try:  # set color according to neuro-transmitter
            self.color = QColor(n_ts_palette[self.neuro_trs])
        except KeyError:  # if the neuro-transmitter does not exist in our palette set it to default
            self.color = QColor(n_ts_palette['idk'])

        self.setBrush(self.color)

        super().show()

    def change_filling(self):
        if self.fill_toggle:
            self.fill_toggle = False
            self.setPen(self.pen1)
        else:
            self.fill_toggle = True
            self.setPen(self.color)


# let's make a little color palette thing for the neurotransmitter
class ColorPal(QWidget):
    def __init__(self):
        super().__init__()

        self.setMouseTracking(True)
        self.setStyleSheet("background-color: rgba(230, 230, 230, 1);")

        font = QFont()
        font.setPointSize(9)

        v_layout = QVBoxLayout()
        for neuro_ts, color in n_ts_palette.items():
            h_layout = QHBoxLayout()

            label = QLabel(neuro_ts)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            label.setFont(font)

            color_frame = QFrame()
            color_frame.setFixedWidth(30)
            color_frame.setStyleSheet(f"background-color: rgba{QColor(color).getRgb()}; border: 1px solid black;")

            h_layout.addWidget(label)
            h_layout.addWidget(color_frame)

            v_layout.addLayout(h_layout)

        v_layout.setSpacing(0)
        self.setLayout(v_layout)
        self.setFixedWidth(150)

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

    def update_frame(self, nt):
        frame = [self.layout().itemAt(i) for i in range(self.layout().count()) if self.layout().itemAt(i).itemAt(0).widget().text()==nt]
        if frame:  # if the neuro-transmitter already exists in the palette:
            if nt in n_ts_palette:  # if the nt is in the dict, this means a change to an existing neuro-transmitter
                frame = frame[0].itemAt(1).widget()
                frame.setStyleSheet(f"background-color: {n_ts_palette[nt]}; border: 1px solid black;")
            else:  # if not, this means a deletion
                # first delete the widgets within this sub-layout
                frame[0].itemAt(0).widget().deleteLater()
                frame[0].itemAt(1).widget().deleteLater()
                self.layout().removeItem(frame[0])  # then remove the layout and update, not sure if this is actually neccessary
                self.layout().update()
        else:  # if the neurotransmitter is new
            h_layout = QHBoxLayout()
            label = QLabel(nt)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            font = QFont()
            font.setPointSize(9)
            label.setFont(font)

            color_frame = QFrame()
            color_frame.setFixedWidth(30)
            color_frame.setStyleSheet(f"background-color: rgba{QColor(n_ts_palette[nt]).getRgb()}; border: 1px solid black;")

            h_layout.addWidget(label)
            h_layout.addWidget(color_frame)

            self.layout().addLayout(h_layout)


# this class is created for dynamic text displaying, which is activated by hovering over areas in the map
class ResizingTextLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.text_size = 20
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
            self.text_size = int(20*self.scale_factor)
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
