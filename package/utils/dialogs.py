from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from package.models.device_model import DeviceModel


class CustomIPDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.device_model = DeviceModel()
        self.setWindowTitle("Add Custom IP Address")
        self.setGeometry(100, 100, 300, 150)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Enter IP Address:"))

        self.input_field = QLineEdit()
        layout.addWidget(self.input_field)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.handle_save)
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def handle_save(self):
        ip = self.input_field.text().strip()
        if not ip:
            QMessageBox.warning(self, "Input Error", "Please enter a valid IP address.")
            return
        self.device_model.add_device("Biometric Device", ip, "ZKTeco")
        self.accept()
