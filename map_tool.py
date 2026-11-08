from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsWkbTypes, QgsPointXY, QgsGeometry, QgsFeature, QgsVectorLayer, QgsProject
from qgis.gui import QgsMapTool, QgsRubberBand

from .i18n import tr


class LiveBufferMapTool(QgsMapTool):
    """Kortværktøj: venstreklik tilføjer punkter til en linje, med en live
    buffer-forhåndsvisning omkring linjen. Højreklik afslutter linjen,
    beregner den endelige buffer og skriver den som polygon til et lag."""

    def __init__(self, canvas, iface, get_buffer_size, get_autoselect):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.get_buffer_size = get_buffer_size
        self.get_autoselect = get_autoselect

        self.points = []
        self.output_layer = None  # memory-lag oprettet on-demand, genbruges mellem tegninger

        self.line_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.line_band.setColor(QColor(0, 90, 200, 220))
        self.line_band.setWidth(2)

        self.buffer_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.buffer_band.setColor(QColor(0, 150, 230, 60))
        self.buffer_band.setStrokeColor(QColor(0, 120, 220, 180))
        self.buffer_band.setWidth(1)

    # --- QgsMapTool livscyklus -------------------------------------------------

    def activate(self):
        super().activate()
        self.canvas.setCursor(Qt.CursorShape.CrossCursor)
        self._reset_geometry()
        self.iface.mainWindow().statusBar().showMessage(tr("status_draw"))

    def deactivate(self):
        self._reset_geometry()
        self.iface.mainWindow().statusBar().clearMessage()
        super().deactivate()

    def _reset_geometry(self):
        self.points = []
        self.line_band.reset(QgsWkbTypes.LineGeometry)
        self.buffer_band.reset(QgsWkbTypes.PolygonGeometry)

    # --- Museinteraktion ---------------------------------------------------

    def canvasPressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pt = self.toMapCoordinates(event.pos())
            self.points.append(QgsPointXY(pt))
            self._update_line_band()
        elif event.button() == Qt.MouseButton.RightButton:
            self._finish_line()

    def canvasMoveEvent(self, event):
        if not self.points:
            return
        pt = QgsPointXY(self.toMapCoordinates(event.pos()))
        self._update_line_band(extra_point=pt)
        self._update_buffer_preview(extra_point=pt)

    # --- Geometri-opbygning --------------------------------------------------

    def _current_polyline(self, extra_point=None):
        pts = list(self.points)
        if extra_point is not None:
            pts.append(extra_point)
        return pts

    def _update_line_band(self, extra_point=None):
        pts = self._current_polyline(extra_point)
        self.line_band.reset(QgsWkbTypes.LineGeometry)
        if len(pts) == 1:
            self.line_band.setToGeometry(QgsGeometry.fromPointXY(pts[0]), None)
        elif len(pts) >= 2:
            self.line_band.setToGeometry(QgsGeometry.fromPolylineXY(pts), None)

    def _update_buffer_preview(self, extra_point=None):
        pts = self._current_polyline(extra_point)
        self.buffer_band.reset(QgsWkbTypes.PolygonGeometry)
        if len(pts) < 2:
            return
        geom = QgsGeometry.fromPolylineXY(pts)
        buffered = geom.buffer(self.get_buffer_size(), 12)
        if buffered and not buffered.isEmpty():
            self.buffer_band.setToGeometry(buffered, None)

    # --- Afslutning af linje / skriv resultat ---------------------------------

    def _finish_line(self):
        if len(self.points) < 2:
            self._reset_geometry()
            self.iface.mainWindow().statusBar().showMessage(tr("status_too_few"))
            return

        geom = QgsGeometry.fromPolylineXY(self.points)
        buffered = geom.buffer(self.get_buffer_size(), 12)

        if buffered is None or buffered.isEmpty():
            self._reset_geometry()
            return

        layer = self._get_or_create_output_layer()
        fid = self._add_feature(layer, buffered)

        if fid is not None and self.get_autoselect():
            layer.selectByIds([fid])

        layer.triggerRepaint()
        self._reset_geometry()
        self.iface.mainWindow().statusBar().showMessage(tr("status_draw"))

    def _get_or_create_output_layer(self):
        """Brug det aktive lag hvis det er et egnet polygonlag, ellers
        genbrug (eller opret) et memory-lag til buffer-resultaterne."""
        active = self.iface.activeLayer()
        if (
            isinstance(active, QgsVectorLayer)
            and active.isValid()
            and QgsWkbTypes.geometryType(active.wkbType()) == QgsWkbTypes.PolygonGeometry
        ):
            return active

        if self.output_layer is not None:
            try:
                still_present = QgsProject.instance().mapLayer(self.output_layer.id()) is not None
            except RuntimeError:
                still_present = False
            if still_present:
                return self.output_layer
            self.output_layer = None

        crs = self.canvas.mapSettings().destinationCrs()
        layer = QgsVectorLayer(f"Polygon?crs={crs.authid()}", "LiveBuffer", "memory")
        QgsProject.instance().addMapLayer(layer)
        self.output_layer = layer
        return layer

    def _add_feature(self, layer, geometry):
        feature = QgsFeature(layer.fields())
        feature.setGeometry(geometry)

        was_editing = layer.isEditable()
        if not was_editing and not layer.startEditing():
            self.iface.messageBar().pushWarning("LiveBuffer", tr("edit_failed", layer.name()))
            return None

        ok = layer.addFeature(feature)
        if not ok:
            if not was_editing:
                layer.commitChanges()
            return None

        fid = feature.id()

        if not was_editing:
            # addFeature() only assigns a temporary (negative) id while the
            # edit buffer is open. commitChanges() replaces it with the
            # provider's real id, but doesn't update our local `feature`
            # object with it — so capture the real id via the signal that
            # fires during commit, instead of trusting the stale temp id.
            committed_ids = []

            def _on_committed(_layer_id, features):
                committed_ids.extend(f.id() for f in features)

            layer.committedFeaturesAdded.connect(_on_committed)
            try:
                layer.commitChanges()
            finally:
                layer.committedFeaturesAdded.disconnect(_on_committed)

            if committed_ids:
                fid = committed_ids[-1]

        layer.updateExtents()
        return fid
