################################################################################
## QPushButton

import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg
from PyQt5.QtCore import Qt

class DisabledIconEngine(qtg.QIconEngine):

    def __init__(self, base_icon, opacity):
        super().__init__()
        self.base_icon = base_icon
        self.opacity = opacity

    def clone(self):
        return DisabledIconEngine(self.base_icon, self.opacity)

    def paint(self, painter, rect, mode, state):

        if self.base_icon.isNull():
            return

        painter.save()
        painter.setOpacity(self.opacity)
        self.base_icon.paint(painter, rect, Qt.AlignCenter, mode, state)
        painter.restore()

    def pixmap(self, size, mode, state):

        if self.base_icon.isNull():
            return qtg.QPixmap()

        base_pixmap = self.base_icon.pixmap(size, mode, state)
        if base_pixmap.isNull():
            return qtg.QPixmap()

        result = qtg.QPixmap(size)
        result.fill(Qt.transparent)

        painter = qtg.QPainter(result)
        painter.setOpacity(self.opacity)
        painter.drawPixmap(0, 0, base_pixmap)
        painter.end()

        return result

class QPushButton(qtw.QPushButton):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._normal_icon = qtg.QIcon()
        self.disabled_opacity = 0.3

    def setIcon(self, icon):
        self._normal_icon = icon
        self._update_icon()

    def _update_icon(self):

        if self.isEnabled():
            super().setIcon(self._normal_icon)

        else:
            if not self._normal_icon.isNull():
                disabled_engine = DisabledIconEngine(self._normal_icon, self.disabled_opacity)
                disabled_icon = qtg.QIcon(disabled_engine)
                super().setIcon(disabled_icon)

            else:
                super().setIcon(qtg.QIcon())

    def changeEvent(self, event):

        if event.type() == event.EnabledChange:
            self._update_icon()

        super().changeEvent(event)

    def setDisabledIconOpacity(self, opacity):
        self.disabled_opacity = opacity

        if not self.isEnabled():
            self._update_icon()
