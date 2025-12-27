################################################################################
## QComboBox

import PyQt5.QtWidgets as qtw

class QComboBox(qtw.QComboBox):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_delegate()

    def setup_delegate(self):
        item_delegate = qtw.QStyledItemDelegate()
        self.setItemDelegate(item_delegate)
