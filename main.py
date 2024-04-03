import sys
import json
from PySide6.QtCore import QThread, Signal, QEvent, QTimer, Qt, QRectF
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
from PySide6.QtGui import QPainter, QBrush, QColor, QFont, QPainterPath, QPen
import subprocess
import signal

# sideload qmk's info.json
with open('info.json', 'r') as file:
    keyboard_layout_data = json.load(file)


class KeyButton(QPushButton):
    def __init__(self, label, parent=None):
        super().__init__(label, parent)
        self.rescale_value = "0"  
        self.fill_color = QColor("#7FE8FF")  

    def set_rescale_value(self, value):
        self.rescale_value = str(value).strip()
        self.update()  

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) 
        
        fill_path = QPainterPath()
        fill_height = (float(self.rescale_value) / 100.0) * self.height()
        fill_rect = self.rect().adjusted(4, self.height() - fill_height + 4, -4, -4)  
        fill_path.addRoundedRect(fill_rect, 10, 10)  
        painter.fillPath(fill_path, self.fill_color)

        
        border_path = QPainterPath()
        border_path.addRoundedRect(self.rect().adjusted(2, 2, -2, -2), 10, 10)  
        pen = QPen(QColor("#6D9098"), 2) 
        painter.setPen(pen)
        painter.drawPath(border_path)

        
        font = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#000000"))  

       
        text = self.text().split('\n')[0]  # Only the label, ignore rescale value
        text_rect = self.rect().adjusted(5, 5, -5, -5)  
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignTop, text)

        font.setPointSize(14)  
        painter.setFont(font)
        painter.setPen(QColor("#000000")) 

        
        rescale_text_rect = QRectF(0, self.height() - fill_height, self.width(), fill_height)
        
        painter.drawText(rescale_text_rect, Qt.AlignCenter, self.rescale_value)

        painter.end()  
    
    def set_fill_color(self, color):
        self.fill_color = QColor(color)
        self.update()

class KeyboardWidget(QWidget):
    def __init__(self, layout):
        super().__init__()
        
        self.total_units = max(key_info['x'] + key_info.get('w', 1) for key_info in layout)
        self.aspect_ratio = self.total_units / 5  # Hardcoedd rows
        self.total_units = max(key_info['x'] + key_info.get('w', 1) for key_info in layout)
        #print(f"Total units: {self.total_units}")  
        self.keys = {tuple(key_info['matrix']): KeyButton(key_info['label']) for key_info in layout}
        self.label_to_matrix = {key_info['label']: tuple(key_info['matrix']) for key_info in layout}

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
        #key press event, not sure what for yet
        pass
        
    def update_key_value(self, row, col, value):
        key = (row, col)
        if key in self.keys:
            button = self.keys[key]
            # Update the rescale value using the new method
            button.set_rescale_value(value)


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

        self.setFocusPolicy(Qt.StrongFocus)  # Allow the window to be focused


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

    def keyPressEvent(self, event):
        # Get the character of the key that was pressed
        char = event.text()

        # Use the character to get the matrix position from the label_to_matrix mapping
        matrix_pos = self.keyboard_widget.label_to_matrix.get(char.lower())

        # If a mapping was found, change the color of the corresponding KeyButton
        if matrix_pos:
            self.change_key_color(*matrix_pos, "#FF7F7F")  # Change color to red
            event.accept()  # Mark the event as handled
        else:
            super().keyPressEvent(event)  # Call the base class handler for other keys

    def keyReleaseEvent(self, event):
        # Get the character of the key that was released
        char = event.text()

        # Use the character to get the matrix position from the label_to_matrix mapping
        matrix_pos = self.keyboard_widget.label_to_matrix.get(char.lower())

        # If a mapping was found, change the color of the corresponding KeyButton back to blue
        if matrix_pos:
            self.change_key_color(*matrix_pos, "#7FE8FF")  # Change color back to blue
            event.accept()  # Mark the event as handled
        else:
            super().keyReleaseEvent(event)  # Call the base class handler for other keys

    def change_key_color(self, row, col, color):
        key_button = self.keyboard_widget.keys.get((row, col))
        if key_button:
            key_button.set_fill_color(color)

    def process_hid_output(self, output):
        if 'Rescale:' in output:
            try:
                if '|' in output:
                    parts = output.split('|')
                else:
                    parts = [output]

                for part in parts:
                    if 'Rescale:' in part:
                        sensor_info = part.strip()
                        coords, rescale_value = sensor_info.split('Rescale:')
                        row, col = coords.replace('(', '').replace(')', '').split(',')
                        row, col = int(row.strip()), int(col.strip()) 
                        rescale_value = rescale_value.strip()

                        # Update the rescale value using the new method
                        self.keyboard_widget.update_key_value(row, col, rescale_value)
                        
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
    timer.timeout.connect(lambda: None)  


    with open('.\\info.json', 'r') as f:
        data = json.load(f)
    keyboard_layout = data['layouts']['LAYOUT']['layout']


    window = MainWindow(keyboard_layout)
    window.resize(1600, 400)  # Initialize to a size with the "_correct_" aspect ratio
    window.show()


    sys.exit(app.exec())