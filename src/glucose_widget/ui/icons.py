from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from glucose_widget.models import GlucoseZone

ZONE_COLORS = {
    GlucoseZone.LOW: "#D32F2F",
    GlucoseZone.IN_RANGE: "#238636",
    GlucoseZone.HIGH: "#B77900",
}
NEUTRAL_COLOR = "#5F6368"


def tray_icon(zone: GlucoseZone | None = None) -> QIcon:
    color = QColor(ZONE_COLORS.get(zone, NEUTRAL_COLOR))
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    path = QPainterPath(QPointF(32, 5))
    path.cubicTo(QPointF(25, 17), QPointF(13, 28), QPointF(13, 42))
    path.cubicTo(QPointF(13, 54), QPointF(21, 61), QPointF(32, 61))
    path.cubicTo(QPointF(43, 61), QPointF(51, 54), QPointF(51, 42))
    path.cubicTo(QPointF(51, 28), QPointF(39, 17), QPointF(32, 5))
    painter.fillPath(path, color)

    pen = QPen(QColor("#FFFFFF"))
    pen.setWidth(5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawLine(QPointF(23, 43), QPointF(29, 49))
    painter.drawLine(QPointF(29, 49), QPointF(42, 34))
    painter.end()
    return QIcon(pixmap)
