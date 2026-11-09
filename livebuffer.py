import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDoubleSpinBox, QCheckBox, QLabel

try:
    from qgis.PyQt.QtWidgets import QAction
except ImportError:  # Qt6 / QGIS 4
    from qgis.PyQt.QtGui import QAction

from .i18n import tr
from .map_tool import LiveBufferMapTool


class LiveBufferPlugin:
    """Opretter toolbar-UI'et (ikon, buffer-spinbox, autoselect-checkbox) og
    binder det til det custom kortværktøj i map_tool.py."""

    def __init__(self, iface):
        self.iface = iface

        self.toolbar = None
        self.action = None
        self.buffer_spin = None
        self.autoselect_check = None
        self.map_tool = None

    def initGui(self):
        self.toolbar = self.iface.addToolBar("LiveBuffer")
        self.toolbar.setObjectName("LiveBufferToolbar")

        self.action = QAction(
            QIcon(os.path.join(os.path.dirname(__file__), "icon.png")), tr("action_text"), self.iface.mainWindow()
        )
        self.action.setCheckable(True)
        self.action.setStatusTip(tr("action_status_tip"))
        self.toolbar.addAction(self.action)

        self.toolbar.addWidget(QLabel(tr("buffer_label")))

        self.buffer_spin = QDoubleSpinBox()
        self.buffer_spin.setDecimals(2)
        self.buffer_spin.setRange(0.01, 1000000.0)
        self.buffer_spin.setSingleStep(1.0)
        self.buffer_spin.setValue(10.0)
        self.buffer_spin.setToolTip(tr("buffer_tip"))
        self.toolbar.addWidget(self.buffer_spin)

        self.autoselect_check = QCheckBox(tr("autoselect"))
        self.autoselect_check.setToolTip(tr("autoselect_tip"))
        self.toolbar.addWidget(self.autoselect_check)

        self.map_tool = LiveBufferMapTool(
            self.iface.mapCanvas(),
            self.iface,
            get_buffer_size=lambda: self.buffer_spin.value(),
            get_autoselect=lambda: self.autoselect_check.isChecked(),
        )
        # setAction sørger for at ikonet automatisk vises som "trykket"
        # når værktøjet er aktivt, og slippes når man skifter til et andet.
        self.map_tool.setAction(self.action)

        self.action.triggered.connect(self._activate_tool)

    def _activate_tool(self, checked):
        if checked:
            self.iface.mapCanvas().setMapTool(self.map_tool)
        else:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)

    def unload(self):
        if self.map_tool is not None and self.iface.mapCanvas().mapTool() is self.map_tool:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)

        if self.toolbar is not None:
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None
