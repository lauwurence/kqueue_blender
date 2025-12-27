################################################################################
##

import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc

class QProgressBar(qtw.QProgressBar):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self.animation = None

    def setValueAnimated(self, value, duration=1000):

        if self.animation:
            self.animation.stop()

        if not value:
            self.setValue(value)
            return

        self.animation = qtc.QPropertyAnimation(self, b"value")
        self.animation.setDuration(duration)
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(value)
        self.animation.setEasingCurve(qtc.QEasingCurve.OutCubic)
        self.animation.start()
