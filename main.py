import sys
import json
from PySide6.QtWidgets import QApplication, QWidget, QPushButton
from PySide6.QtCore import QThread, Signal, QEvent, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
import subprocess
import signal

# sideload qmk's info.json
with open('info.json', 'r') as file:
    keyboard_layout_data = json.load(file)


class KeyboardWidget(QWidget):
    def __init__(self, layout):
        super().__init__()
        
        self.total_units = max(key_info['x'] + key_info.get('w', 1) for key_info in layout)
        self.aspect_ratio = self.total_units / 5  # Hardcoedd rows
        self.total_units = max(key_info['x'] + key_info.get('w', 1) for key_info in layout)
        #print(f"Total units: {self.total_units}")  
        self.keys = {tuple(key_info['matrix']): QPushButton(key_info['label']) for key_info in layout}
        for key, button in self.keys.items():
            button.setParent(self)
            button.clicked.connect(lambda key=key: self.key_pressed(key))
        stylesheet = """
        QPushButton {
            border: 4px solid #6D9098;
            border-radius: 6px;
            background-color: #005466;
            padding: 5px;
        }
        QPushButton:pressed {
            background-color: #91C9D5;
        }
        """

        self.setStyleSheet(stylesheet)
            


    def key_pressed(self, key):
        # Handle key press event, not sure what for yet
        pass

    def update_key_value(self, row, col, value):
        key = (row, col)
        if key in self.keys:
            button = self.keys[key]
            original_text = button.text().split('\n')[0]  
            button.setText(f"{original_text}\n{value}")  
            
            
            font = button.font()
            font.setFamily("Arial")
            font.setPointSize(10)  
            font.setBold(True)
            button.setFont(font)

            button.setStyleSheet("QPushButton {"
                                "border: 4px solid #6D9098;"
                                "border-radius: 6px;"
                                "background-color: #005466;"
                                "padding: 5px;"
                                "color: #91C9D5;"  # Set text color
                                "font-size: 12px;"  
                                "}"
                                "QPushButton:pressed {"
                                "background-color: #a0a0a0;"
                                "}")



    def resizeEvent(self, event):
        unit_width = self.width() / self.total_units
        unit_height = self.height() / 5

        for key_info in keyboard_layout:
            key = tuple(key_info['matrix'])
            x = key_info['x'] * unit_width
            y = key_info['matrix'][0] * unit_height
            width = key_info.get('w', 1) * unit_width
            height = unit_height 
            self.keys[key].setGeometry(x, y, width, height)

        super().resizeEvent(event)


# HID Listen Integration
class HIDListenThread(QThread):
    output_signal = Signal(str)

    def run(self):
        hid_listen_path = r".\\hid_listen.exe"
        with subprocess.Popen(hid_listen_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True) as proc:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                #print("Received HID line:", line.strip())  # Debug #print
                self.output_signal.emit(line.strip())

    def stop(self):
        self.terminate()  

class MainWindow(QWidget):
    def __init__(self, keyboard_layout):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.keyboard_widget = KeyboardWidget(keyboard_layout)
        self.layout.addWidget(self.keyboard_widget)
        
        # Start listening to HID
        self.hid_thread = HIDListenThread()
        self.hid_thread.output_signal.connect(self.process_hid_output)
        self.hid_thread.start()

        # Set the initial size to maintain aspect ratio
        self.aspect_ratio = self.keyboard_widget.aspect_ratio
        self.init_size()
        
        # Install the event filter to intercept resize events
        self.installEventFilter(self)

    def init_size(self):
        initial_width = 800
        initial_height = initial_width / self.aspect_ratio
        self.resize(initial_width, initial_height)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Resize and source is self:
            # Maintain aspect ratio during resize
            new_size = event.size()
            width = new_size.width()
            height = int(width / self.aspect_ratio)
            new_size.setHeight(height)
            self.resize(new_size)
            return True
        return super().eventFilter(source, event)

    def resizeEvent(self, event):
        new_width = event.size().width()
        new_height = int(new_width / self.aspect_ratio)
        
        self.keyboard_widget.setMaximumHeight(new_height)
        self.keyboard_widget.setMinimumHeight(new_height)

        # Call superclss for proper event handling
        super().resizeEvent(event)


    def process_hid_output(self, output):
        if 'Rescale:' in output:
            try:
                parts = output.split('|')
                for part in parts:
                    if 'Rescale:' in part:
                        sensor_info = part.strip()
                        coords, rescale_value = sensor_info.split('Rescale:')
                        coords = coords.strip().strip('(').strip(')').split(',')
                        row, col = map(int, coords)
                        self.keyboard_widget.update_key_value(row, col, rescale_value.strip())
            except Exception as e:
                print(f"Error parsing HID output: {e}")

    def closeEvent(self, event):
        self.hid_thread.stop()
        super().closeEvent(event)


def signal_handler(sig, frame):
    print("Ctrl+C pressed, exiting...")
    QApplication.quit()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    app = QApplication(sys.argv)

    timer = QTimer()
    timer.start(500)  # ms
    timer.timeout.connect(lambda: None)  # Timeout handler does nothing


    with open('.\\info.json', 'r') as f:
        data = json.load(f)
    keyboard_layout = data['layouts']['LAYOUT']['layout']


    window = MainWindow(keyboard_layout)
    window.resize(1600, 400)  # Initialize to a size with the "_correct_" aspect ratio
    window.show()


    sys.exit(app.exec())