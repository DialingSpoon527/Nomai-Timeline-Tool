import sys
import os
import json
import math
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem,
    QFileDialog, QAction, QMessageBox, QDialog, QVBoxLayout, QTextEdit, QInputDialog
)
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPen, QPainter, QColor, QFontMetrics, QPolygonF

CONFIG_FILE = 'layout.json'

class NodeItem(QGraphicsEllipseItem):
    def __init__(self, file_path, x=0, y=0, w=200, h=50):
        super().__init__(0, 0, w, h)
        self.setZValue(1)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self._dragging = False
        self.file_path = file_path
        self.setBrush(Qt.lightGray)
        name = os.path.splitext(os.path.basename(file_path))[0]
        self.text = QGraphicsTextItem(name, self)
        self.text.setDefaultTextColor(Qt.black)
        self.text.setScale(1.2)
        self.update_text_position()
        self.setPos(x, y)

    def update_text_position(self):
        fm = QFontMetrics(self.text.font())
        w = self.rect().width() / self.text.scale()
        h = self.rect().height() / self.text.scale()
        tw = fm.horizontalAdvance(self.text.toPlainText())
        th = fm.height()
        self.text.setPos((w - tw)/2, (h - th)/2)

    def hoverEnterEvent(self, event):
        self.scene().hovered_node = self
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if getattr(self.scene(), 'hovered_node', None) is self:
            self.scene().hovered_node = None
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._dragging = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self._dragging:
            self.scene().start_edge(self)
        elif event.button() == Qt.RightButton:
            self.open_file()
        super().mouseReleaseEvent(event)

    def open_file(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(None, "Error", f"Could not open file: {e}")
            return
        dlg = QDialog()
        dlg.setWindowTitle(os.path.basename(self.file_path))
        layout = QVBoxLayout(dlg)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(content)
        layout.addWidget(text_edit)
        dlg.resize(600, 400)
        dlg.exec_()

class EdgeItem(QGraphicsLineItem):
    def __init__(self, start_item, end_item, color=Qt.white):
        super().__init__()
        self.setZValue(0)
        self.start_item = start_item
        self.end_item = end_item
        self.setPen(QPen(color, 5))
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.arrow = QGraphicsPolygonFItem(self)
        self.update_position()

    def update_position(self):
        p1 = self.start_item.sceneBoundingRect().center()
        p2 = self.end_item.sceneBoundingRect().center()
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())
        # arrowhead at midpoint
        line = self.line()
        dx = line.dx()
        dy = line.dy()
        angle = math.atan2(dy, dx)
        size = 30
        mid = line.pointAt(0.5)
        tip = QPointF(mid.x(), mid.y())
        left = QPointF(tip.x() - size * math.cos(angle - math.pi/6), tip.y() - size * math.sin(angle - math.pi/6))
        right = QPointF(tip.x() - size * math.cos(angle + math.pi/6), tip.y() - size * math.sin(angle + math.pi/6))
        poly = QPolygonF([tip, left, right])
        self.arrow.setPolygon(poly)
        self.arrow.setBrush(self.pen().color())

    def hoverEnterEvent(self, event):
        self.scene().hovered_edge = self
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if getattr(self.scene(), 'hovered_edge', None) is self:
            self.scene().hovered_edge = None
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_item, self.end_item = self.end_item, self.start_item
            self.update_position()
            event.accept()
        else:
            super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        scene = self.scene()
        if self in scene.edges:
            scene.removeItem(self.arrow)
            scene.removeItem(self)
            scene.edges.remove(self)
        event.accept()

class QGraphicsPolygonFItem(QGraphicsItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._poly = QPolygonF()
        self._brush = None
    def setPolygon(self, poly):
        self._poly = poly
        self.update()
    def polygon(self):
        return self._poly
    def setBrush(self, brush):
        self._brush = brush
    def boundingRect(self):
        return self._poly.boundingRect()
    def paint(self, painter, option, widget):
        painter.setBrush(self._brush)
        painter.drawPolygon(self._poly)

class GraphScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.edges = []
        self.edge_start = None
        self.temp_line = None
        self.hovered_node = None
        self.hovered_edge = None

    def add_node(self, file_path, x=0, y=0):
        node = NodeItem(file_path, x, y)
        self.nodes.append(node)
        self.addItem(node)

    def start_edge(self, node):
        if self.edge_start is None:
            self.edge_start = node
        else:
            source = self.edge_start
            target = node
            if target is not source:
                exists = any(e.start_item is source and e.end_item is target for e in self.edges)
                if not exists:
                    edge = EdgeItem(source, target)
                    self.edges.append(edge)
                    self.addItem(edge)
            self.edge_start = None
            if self.temp_line:
                self.removeItem(self.temp_line)
                self.temp_line = None

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.edge_start:
            p1 = self.edge_start.sceneBoundingRect().center()
            p2 = event.scenePos()
            if not self.temp_line:
                self.temp_line = QGraphicsLineItem()
                self.temp_line.setZValue(0)
                self.temp_line.setPen(QPen(Qt.white, 5, Qt.DashLine))
                self.addItem(self.temp_line)
            self.temp_line.setLine(p1.x(), p1.y(), p2.x(), p2.y())

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        for edge in self.edges:
            edge.update_position()

    def save(self):
        # save relative paths and edge colors
        base = os.getcwd()
        data = {
            'nodes': [
                {'file': os.path.relpath(n.file_path, base), 'x': n.pos().x(), 'y': n.pos().y(), 'color': n.brush().color().rgba()}
                for n in self.nodes
            ],
            'edges': [
                {'start': self.nodes.index(e.start_item), 'end': self.nodes.index(e.end_item), 'color': e.pen().color().rgba()}
                for e in self.edges
            ]
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load(self):
        if not os.path.exists(CONFIG_FILE):
            return
        base = os.getcwd()
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in self.items(): self.removeItem(item)
        self.nodes.clear(); self.edges.clear()
        for n in data.get('nodes', []):
            path = os.path.join(base, n['file'])
            node = NodeItem(path, n['x'], n['y'])
            node.setBrush(QColor.fromRgba(n.get('color', Qt.lightGray)))
            node.update_text_position()
            self.nodes.append(node)
            self.addItem(node)
        for e in data.get('edges', []):
            s, t = self.nodes[e['start']], self.nodes[e['end']]
            edge = EdgeItem(s, t, QColor.fromRgba(e.get('color', Qt.white)))
            self.edges.append(edge)
            self.addItem(edge)

class GraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setFocusPolicy(Qt.StrongFocus)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.ShiftModifier:
            self.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        factor = 1.2 if event.angleDelta().y() > 0 else 1/1.2
        self.scale(factor, factor)

    def keyPressEvent(self, event):
        if self.scene().hovered_edge and event.key() in (Qt.Key_1, Qt.Key_2, Qt.Key_3):
            cmap = {Qt.Key_1: Qt.white, Qt.Key_2: QColor(50, 50, 150), Qt.Key_3: QColor(0, 100, 0)}
            col = cmap[event.key()]
            edge = self.scene().hovered_edge
            edge.setPen(QPen(col, 5))
            edge.arrow.setBrush(col)
            return
        if Qt.Key_0 <= event.key() <= Qt.Key_9 and self.scene().hovered_node:
            nmap = {
                Qt.Key_1: QColor(228, 208, 0), Qt.Key_2: QColor(228, 210, 160),
                Qt.Key_3: QColor('orange'), Qt.Key_4: QColor(0, 128, 0),
                Qt.Key_5: QColor(132, 100, 204), Qt.Key_6: QColor(128, 128, 0),
                Qt.Key_7: QColor(0, 139, 139), Qt.Key_8: Qt.white,
                Qt.Key_9: QColor(103, 216, 230), Qt.Key_0: Qt.lightGray
            }
            self.scene().hovered_node.setBrush(nmap[event.key()])
            return
        super().keyPressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_folder = None
        self.scene = GraphScene()
        self.view = GraphicsView(self.scene)
        self.scene.setBackgroundBrush(Qt.black)
        self.setCentralWidget(self.view)
        self.setWindowTitle("File Layout Tool")
        self.resize(800, 600)

        toolbar = self.addToolBar("Toolbar")
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.scene.save)
        toolbar.addAction(save_action)
        open_action = QAction("Open Folder", self)
        open_action.triggered.connect(self.open_folder)
        toolbar.addAction(open_action)
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_node)
        toolbar.addAction(new_action)

        self.scene.load()

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with .txt Files")
        if folder:
            self.current_folder = folder
            for fname in os.listdir(folder):
                if fname.lower().endswith('.txt'):
                    path = os.path.join(folder, fname)
                    if not any(n.file_path == path for n in self.scene.nodes):
                        self.scene.add_node(path, 0, 0)

    def new_node(self):
        if not self.current_folder:
            QMessageBox.warning(self, "No Folder", "Please open a folder first.")
            return
        text, ok = QInputDialog.getText(self, "New File", "Enter file name:")
        if ok and text:
            if not text.lower().endswith('.txt'):
                text += '.txt'
            path = os.path.join(self.current_folder, text)
            with open(path, 'w', encoding='utf-8'):
                pass
            self.scene.add_node(path, 0, 0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
