


# Qt5 GUI for APT — Synaptic/Muon inspired, lightweight
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QTextEdit, QMessageBox, QSplitter, QFrame, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import subprocess

class AptWorker(QThread):
    log_signal = pyqtSignal(str)
    done_signal = pyqtSignal()

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            self.log_signal.emit(line.rstrip())
        proc.wait()
        self.done_signal.emit()

class PackageList(QListWidget):
    def __init__(self):
        super().__init__()
        self.setSelectionMode(QListWidget.MultiSelection)
        self.setAlternatingRowColors(True)
        self.setFrameShape(QFrame.StyledPanel)

    def add_package(self, name, desc):
        item = QListWidgetItem(f"{name}")
        item.setToolTip(desc)
        item.setCheckState(Qt.Unchecked)
        self.addItem(item)

    def get_selected(self):
        return [self.item(i).text() for i in range(self.count()) if self.item(i).checkState() == Qt.Checked]

class AptGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("aptqt-lite")
        self.resize(800, 500)
        self.layout = QVBoxLayout(self)

        # Top bar
        top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search packages...")
        self.search_btn = QPushButton("Search")
        self.install_btn = QPushButton("Install")
        self.remove_btn = QPushButton("Remove")
        self.upgrade_btn = QPushButton("Upgrade all")
        self.update_btn = QPushButton("Update list")
        self.exit_btn = QPushButton("Exit")
        for w in [self.search_input, self.search_btn, self.install_btn, self.remove_btn, self.upgrade_btn, self.update_btn, self.exit_btn]:
            top_bar.addWidget(w)
        self.layout.addLayout(top_bar)

        # Splitter for package list and description/logs
        splitter = QSplitter(Qt.Horizontal)
        self.pkg_list = PackageList()
        splitter.addWidget(self.pkg_list)

        # Right panel: description and logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.desc_label = QLabel("<i>Select a package to see its description...</i>")
        self.desc_label.setWordWrap(True)
        self.logs_box = QTextEdit()
        self.logs_box.setReadOnly(True)
        right_layout.addWidget(self.desc_label)
        right_layout.addWidget(self.logs_box)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 450])
        self.layout.addWidget(splitter)

        # Connect buttons
        self.search_btn.clicked.connect(self.search_packages)
        self.search_input.returnPressed.connect(self.search_packages)
        self.install_btn.clicked.connect(self.install_selected)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.upgrade_btn.clicked.connect(lambda: self.run_apt(["apt", "upgrade", "-y"]))
        self.update_btn.clicked.connect(lambda: self.run_apt(["apt", "update"]))
        self.exit_btn.clicked.connect(self.close)

        self.pkg_list.itemSelectionChanged.connect(self.show_description)

        self.worker = None

    def search_packages(self):
        query = self.search_input.text().strip()
        self.pkg_list.clear()
        if not query:
            return
        proc = subprocess.Popen(["apt-cache", "search", query], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, _ = proc.communicate()
        for line in out.splitlines():
            if line:
                parts = line.split(" - ", 1)
                name = parts[0]
                desc = parts[1] if len(parts) > 1 else ""
                self.pkg_list.add_package(name, desc)
        self.desc_label.setText("<i>Select a package to see its description...</i>")

    def show_description(self):
        items = self.pkg_list.selectedItems()
        if not items:
            self.desc_label.setText("<i>Select a package to see its description...</i>")
            return
        pkg = items[0].text()
        # Try to get package description
        proc = subprocess.Popen(["apt-cache", "show", pkg], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, _ = proc.communicate()
        desc = ""
        for line in out.splitlines():
            if line.startswith("Description-") or line.startswith("Description:"):
                desc = line.split(":", 1)[1].strip()
                break
        if not desc:
            desc = items[0].toolTip()
        self.desc_label.setText(f"<b>{pkg}</b><br>{desc}")

    def install_selected(self):
        pkgs = self.pkg_list.get_selected()
        if not pkgs:
            QMessageBox.warning(self, "No selection", "Select packages to install")
            return
        self.run_apt(["apt", "install", "-y"] + pkgs)

    def remove_selected(self):
        pkgs = self.pkg_list.get_selected()
        if not pkgs:
            QMessageBox.warning(self, "No selection", "Select packages to remove")
            return
        self.run_apt(["apt", "remove", "-y"] + pkgs)

    def run_apt(self, cmd):
        self.logs_box.clear()
        self.worker = AptWorker(cmd)
        self.worker.log_signal.connect(self.logs_box.append)
        self.worker.done_signal.connect(self.on_apt_done)
        self.worker.start()

    def on_apt_done(self):
        self.logs_box.append("<b>Done.</b>")
        QMessageBox.information(self, "APT", "Operation completed.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = AptGui()
    gui.show()
    sys.exit(app.exec_())
