"""Render assets/icon.png (1024px) with Qt so packaging needs no design files."""
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPixmap

app = QGuiApplication(sys.argv)
size = 1024
pm = QPixmap(size, size); pm.fill(Qt.transparent)
p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
p.setBrush(QColor("#1f7a4d")); p.setPen(Qt.NoPen)
m = size * 0.09
p.drawRoundedRect(m, m, size - 2 * m, size - 2 * m, size * 0.2, size * 0.2)
f = QFont(); f.setBold(True); f.setPixelSize(int(size * 0.55)); p.setFont(f); p.setPen(QColor("white"))
p.drawText(pm.rect(), Qt.AlignCenter, "Z")
p.end()
pm.save("assets/icon.png")
print("assets/icon.png")
