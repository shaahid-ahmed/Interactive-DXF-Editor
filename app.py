import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QMessageBox, QLabel
from PyQt5.QtWidgets import QScrollArea, QSizePolicy
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtCore import Qt
import ezdxf
from ezdxf import transform
from ezdxf import bbox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas , NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Arc, Rectangle
from matplotlib.lines import Line2D
import numpy as np
import os
from PIL import Image
class DXFVisualizer(QWidget):
    def __init__(self):
        super().__init__()
        os.environ["MPLBACKEND"] = "Qt5Agg"
        self.dxf_path = None
        self.entities = None
        self.selected_entities = []
        self.is_selecting = False
        self.is_text_mode = False
        self.text_annotations = []
        self.rect_start = None
        self.rect_end = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Button to load DXF file
        load_button = QPushButton("Load DXF File")
        load_button.clicked.connect(self.load_dxf)
        layout.addWidget(load_button)

        # Button to toggle selection mode
        self.select_button = QPushButton("Select Entities")
        self.select_button.clicked.connect(self.toggle_selection_mode)
        layout.addWidget(self.select_button)

        # Button to toggle selection mode
        self.delete_button = QPushButton("Delete Entities")
        self.delete_button.clicked.connect(self.delete)
        layout.addWidget(self.delete_button)

        # Button to toggle selection mode
        self.save_button = QPushButton("Save image")
        self.save_button.clicked.connect(self.save)
        layout.addWidget(self.save_button)

        # Inside initUI method
        self.text_button = QPushButton("Text Mode")
        self.text_button.clicked.connect(self.toggle_text_mode)
        layout.addWidget(self.text_button)

        # Set the image dimensions
        self.image_width = 36717
        self.image_height = 3282
        # Matplotlib figure and canvas
        self.figure, self.ax = plt.subplots()
        self.figure.set_size_inches(self.image_width / 100, self.image_height / 100) 
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFixedSize(self.image_width, self.image_height)
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)  # Add scroll area to layout

        # Add the navigation toolbar for zooming and panning
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)

        self.setLayout(layout)
        self.setWindowTitle('DXF Visualizer')
        self.show()

        # Connect matplotlib events
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self.on_mouse_scroll)

        # Enable key press events
        self.setFocusPolicy(Qt.StrongFocus)
    def save(self):
        if self.figure:
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)", options=options)
            if file_path:
                try:
                    self.figure.savefig(file_path)
                    QMessageBox.information(self, "Success", "Image saved successfully!")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save image: {e}")
        else:
            QMessageBox.warning(self, "Warning", "No figure to save!")
    def toggle_text_mode(self):
        """Toggle between text mode for adding/editing text annotations."""
        self.is_text_mode = not self.is_text_mode
        self.text_button.setText("Exit Text Mode" if self.is_text_mode else "Text Mode")

    def delete(self):
        self.entities = [entity for entity in self.entities if entity not in self.selected_entities]
        self.plot_entities()
    def center(self,msp):
        extmin_x = extmin_y = float('inf')
        extmax_x = float('-inf')
        extmax_y = float('-inf')
        for entity in msp:
            if entity.dxftype() == 'LINE':
                start_point = entity.dxf.start
                end_point = entity.dxf.end
                extmin_x = min(extmin_x, start_point.x, end_point.x)
                extmin_y = min(extmin_y, start_point.y, end_point.y)
                extmax_x = max(extmax_x, start_point.x, end_point.x)
                extmax_y = max(extmax_y, start_point.y, end_point.y)
            elif entity.dxftype() == 'ARC':
                start_point = entity.start_point
                end_point = entity.end_point
                extmin_x = min(extmin_x, start_point.x, end_point.x)
                extmin_y = min(extmin_y, start_point.y, end_point.y)
                extmax_x = max(extmax_x, start_point.x, end_point.x)
                extmax_y = max(extmax_y, start_point.y, end_point.y)
            elif entity.dxftype() == 'SPLINE':
                for control_point in entity.control_points:
                    extmin_x = min(extmin_x, control_point[0])
                    extmin_y = min(extmin_y, control_point[-1])
                    extmax_x = max(extmax_x, control_point[0])
                    extmax_y = max(extmax_y, control_point[-1])
            elif entity.dxftype() == 'POLYLINE':
                for control_point in [x for x in entity.points()]:
                    print(control_point)
                    extmin_x = min(extmin_x, control_point[0])
                    extmin_y = min(extmin_y, control_point[1])
                    extmax_x = max(extmax_x, control_point[0])
                    extmax_y = max(extmax_y, control_point[1])
            elif entity.dxftype() == 'CIRCLE':
                center_point = entity.dxf.center
                radius = entity.dxf.radius
                extmin_x = min(extmin_x, center_point.x - radius)
                extmin_y = min(extmin_y, center_point.y - radius)
                extmax_x = max(extmax_x, center_point.x + radius)
                extmax_y = max(extmax_y, center_point.y + radius)
        center_x = (extmin_x + extmax_x) / 2
        center_y = (extmin_y + extmax_y) / 2
        return center_x,center_y,extmin_x,extmin_y,extmax_x,extmax_y
    
    def keyPressEvent(self, event):
        entity = self.selected_entities
        if event.key() == 82:
            cx, cy, _, _, _, _ = self.center(entity)
            transform.translate(entity, (cx*(-1), cy*(-1), 0))
            transform.axis_rotate(entity, (0, 0, 1), np.pi/2)  # 90 degree rotation ACW
            transform.translate(entity, (cx, cy, 0))
        elif event.key() == 69:
            cx, cy, _, _, _, _ = self.center(entity)
            transform.translate(entity, (cx*(-1), cy*(-1), 0))
            transform.axis_rotate(entity, (0, 0, 1), (np.pi/2)*-1)  # 90 degree rotation CW
            transform.translate(entity, (cx, cy, 0))
        elif event.key() == 81:
            cx, cy, _, _, _, _ = self.center(entity)
            transform.translate(entity, (cx*(-1), cy*(-1), 0))
            transform.axis_rotate(entity, (0, 0, 1), -0.0174533)  # 1 degree rotation CW
            transform.translate(entity, (cx, cy, 0))
        elif event.key() == 87:
            cx, cy, _, _, _, _ = self.center(entity)
            transform.translate(entity, (cx*(-1), cy*(-1), 0))
            transform.axis_rotate(entity, (0, 0, 1), 0.0174533)  # 1 degree rotation ACW
            transform.translate(entity, (cx, cy, 0))
        elif event.key() == 16777235 or event.key() == 70:
            transform.translate(entity, (0, 1, 0))  # Move up
        elif event.key() == 16777237 or event.key() == 83:
            transform.translate(entity, (0, -1, 0))  # Move down
        elif event.key() == 16777234 or event.key() == 65:
            transform.translate(entity, (-1, 0, 0))  # Move left
        elif event.key() == 16777236 or event.key() == 68:
            transform.translate(entity, (1, 0, 0))  # Move right
        elif event.key() == 16777216:
            self.selected_entity = None
        self.plot_entities()

    def reset_selection(self):
        self.selected_entities = []
        self.plot_entities()

    def load_dxf(self):
        options = QFileDialog.Options()
        self.dxf_path, _ = QFileDialog.getOpenFileName(self, "Open DXF File", "", "DXF Files (*.dxf)", options=options)
        if self.dxf_path:
            self.load_and_plot_dxf()

    def load_and_plot_dxf(self):
        if not self.dxf_path:
            return

        doc = ezdxf.readfile(self.dxf_path)
        self.image_widthwidth,self.image_height,_=doc.header['$EXTMAX']
        msp = doc.modelspace()
        self.entities = msp
        self.plot_entities()
    def plot_text(self, entity):
        """Plot a TEXT or MTEXT entity in the visualization."""
        if entity.dxftype() == 'TEXT':
            text_content = entity.dxf.text
            x, y, _ = entity.dxf.insert
        elif entity.dxftype() == 'MTEXT':
            text_content = entity.text
            x, y, _ = entity.dxf.insert
        print(x,y)
        # Add the text to the plot with some customization
        self.ax.text(int(x), int(y), text_content, color='blue', fontsize=10)
        self.canvas.draw()

    def plot_entities(self):
        xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()
        self.ax.clear()
        for entity in self.entities:
            if entity.dxftype() == 'LINE':
                self.plot_line(entity)
            elif entity.dxftype() == 'ARC':
                self.plot_arc(entity)
            elif entity.dxftype() == 'CIRCLE':
                self.plot_circle(entity)
            elif entity.dxftype() == 'SPLINE':
                self.plot_spline(entity)
            elif entity.dxftype() == 'POLYLINE':
                self.plot_polyline(entity)
            elif entity.dxftype() in ['TEXT', 'MTEXT']:
                self.plot_text(entity)

        self.highlight_selected_entities()
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.ax.set_aspect('equal')
        self.ax.autoscale()
        self.canvas.draw()

    def plot_line(self, entity):
        start = entity.dxf.start
        end = entity.dxf.end
        self.ax.add_line(Line2D([start.x, end.x], [start.y, end.y], color='black'))

    def plot_arc(self, entity):
        center = entity.dxf.center
        radius = entity.dxf.radius
        start_angle = entity.dxf.start_angle
        end_angle = entity.dxf.end_angle
        arc = Arc((center.x, center.y), 2*radius, 2*radius, angle=0, theta1=start_angle, theta2=end_angle, color='black')
        self.ax.add_patch(arc)

    def plot_circle(self, entity):
        center = entity.dxf.center
        radius = entity.dxf.radius
        circle = Circle((center.x, center.y), radius, fill=False, color='black')
        self.ax.add_patch(circle)

    def plot_spline(self, entity):
        points = entity.control_points
        x = [p[0] for p in points]
        y = [p[1] for p in points]
        self.ax.plot(x, y, color='black')
    def plot_polyline(self, entity):
        control_points = np.array([x for x in entity.points()])
        control_points = np.array(control_points)
        x_i, y_i = control_points.T[:2]
        plt.plot(x_i, y_i, color='black')

    def toggle_selection_mode(self):
        self.is_selecting = not self.is_selecting
        if self.is_selecting:
            self.select_button.setText("Cancel Selection")
        else:
            self.select_button.setText("Select Entities")
            self.selected_entities = []
            self.plot_entities()
    def update_dxf_text(self, annotation, new_text):
        """Finds and updates the corresponding DXF text entity based on position."""
        x, y = annotation.get_position()
        for text_entity in self.entities.query("TEXT"):
            if text_entity.dxf.insert == (x, y):
                text_entity.dxf.text = new_text
                break
    def add_text(self, x, y):
        """Prompt user to enter text and display it at the specified location."""
        text, ok = QInputDialog.getText(self, "Enter Text", "Text:")
        if ok and text:
            # Add text annotation to the matplotlib plot
            annotation = self.ax.text(x, y, text, color='blue', fontsize=10, picker=True)
            self.text_annotations.append(annotation)
            self.canvas.draw()

            # Add text to the DXF file as a TEXT entity
            self.entities.add_text(
                text,
                dxfattribs={
                    'insert': (x, y),
                    'height': 10  # Adjust the height as needed
                }
            )

    def on_text_double_click(self, annotation):
        """Open dialog to edit text on double-click."""
        current_text = annotation.get_text()
        new_text, ok = QInputDialog.getText(self, "Edit Text", "Text:", text=current_text)
        if ok:
            annotation.set_text(new_text)
            self.canvas.draw()
            self.update_dxf_text(annotation, new_text)
    def on_mouse_press(self, event):
        if self.is_selecting and event.button == 1:  # Left mouse button
            self.rect_start = (event.xdata, event.ydata)
        if self.is_text_mode and event.button == 1:  # Left-click in Text Mode
            self.add_text(event.xdata, event.ydata)


    def on_mouse_release(self, event):
        if self.is_selecting and event.button == 1:
            self.rect_end = (event.xdata, event.ydata)
            self.select_entities()
            self.rect_start = None
            self.rect_end = None
        if event.dblclick and self.is_text_mode:
            for annotation in self.text_annotations:
                contains, _ = annotation.contains(event)
                if contains:
                    self.on_text_double_click(annotation)
                    break

    def on_mouse_move(self, event):
        if self.is_selecting and self.rect_start:
            self.rect_end = (event.xdata, event.ydata)
            self.plot_entities()
            self.plot_selection_rectangle()
            self.canvas.draw()
    def on_mouse_scroll(self, event):
        # Adjust the zoom based on scroll direction
        zoom_factor = 1.2
        if event.button == 'up':  # Zoom in
            scale = 1 / zoom_factor
        elif event.button == 'down':  # Zoom out
            scale = zoom_factor
        else:
            return

        # Get the current limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()

        # Calculate the new limits
        x_range = (xlim[1] - xlim[0]) * scale
        y_range = (ylim[1] - ylim[0]) * scale

        x_mid = event.xdata if event.xdata else (xlim[0] + xlim[1]) / 2
        y_mid = event.ydata if event.ydata else (ylim[0] + ylim[1]) / 2

        new_xlim = [x_mid - x_range / 2, x_mid + x_range / 2]
        new_ylim = [y_mid - y_range / 2, y_mid + y_range / 2]

        # Set new limits and refresh plot
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.canvas.draw()

    def plot_selection_rectangle(self):
        if self.rect_start and self.rect_end:
            x = min(self.rect_start[0], self.rect_end[0])
            y = min(self.rect_start[1], self.rect_end[1])
            width = abs(self.rect_end[0] - self.rect_start[0])
            height = abs(self.rect_end[1] - self.rect_start[1])
            rect = Rectangle((x, y), width, height, fill=False, edgecolor='red')
            self.ax.add_patch(rect)

    def select_entities(self):
        if not self.rect_start or not self.rect_end:
            return

        x1, y1 = self.rect_start
        x2, y2 = self.rect_end
        x_min, x_max = min(x1, x2), max(x1, x2)
        y_min, y_max = min(y1, y2), max(y1, y2)

        self.selected_entities = self.box_entities(self.entities,[(x_min,y_min),(x_max,y_max)])
        # print((x_min,y_min),(x_max,y_max))
        # print(self.selected_entities)
        self.plot_entities()
    def check_intersection(self,box1, box2):
        (x_min1, y_min1), (x_max1, y_max1) = box1
        (x_min2, y_min2), (x_max2, y_max2) = box2
        return not (x_min1 > x_max2 or x_max1 < x_min2 or y_min1 > y_max2 or y_max1 < y_min2)

    def box_entities(self,msp, selection_box):
        count = []
        for e in msp:
            entity_box = bbox.extents([e])
            
            if entity_box is None:
                continue
            x_min, y_min, z_min = entity_box.extmin
            x_max, y_max, z_max = entity_box.extmax
            entity_2d_box = [(x_min, y_min), (x_max, y_max)]
            if self.check_intersection(selection_box, entity_2d_box):
                count += [e]
        return count

    def entity_in_rectangle(self, entity, x_min, y_min, x_max, y_max):
        if entity.dxftype() == 'LINE':
            return (x_min <= entity.dxf.start.x <= x_max and y_min <= entity.dxf.start.y <= y_max) or \
                   (x_min <= entity.dxf.end.x <= x_max and y_min <= entity.dxf.end.y <= y_max)
        elif entity.dxftype() in ['ARC', 'CIRCLE']:
            center = entity.dxf.center
            return x_min <= center.x <= x_max and y_min <= center.y <= y_max
        elif entity.dxftype() == ['SPLINE', 'POLYLINE']:
            points = entity.get_points()
            print(points)
            return any(x_min <= p[0] <= x_max and y_min <= p[1] <= y_max for p in points)
        return False

    def highlight_selected_entities(self):
        for entity in self.selected_entities:
            if entity.dxftype() == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                self.ax.add_line(Line2D([start.x, end.x], [start.y, end.y], color='red', linewidth=2))
            elif entity.dxftype() == 'ARC':
                center = entity.dxf.center
                radius = entity.dxf.radius
                start_angle = entity.dxf.start_angle
                end_angle = entity.dxf.end_angle
                arc = Arc((center.x, center.y), 2*radius, 2*radius, angle=0, theta1=start_angle, theta2=end_angle, color='red', linewidth=2)
                self.ax.add_patch(arc)
            elif entity.dxftype() == 'CIRCLE':
                center = entity.dxf.center
                radius = entity.dxf.radius
                circle = Circle((center.x, center.y), radius, fill=False, color='red', linewidth=2)
                self.ax.add_patch(circle)
            elif entity.dxftype() == 'SPLINE':
                points = entity.control_points
                x = [p[0] for p in points]
                y = [p[1] for p in points]
                self.ax.plot(x, y, color='red', linewidth=2)
            elif entity.dxftype() == 'POLYLINE':
                control_points = np.array([x for x in entity.points()])
                x_i, y_i = control_points.T[:2]
                plt.plot(x_i, y_i, color='red', linewidth=2)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DXFVisualizer()
    sys.exit(app.exec_())