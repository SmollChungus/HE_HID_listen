Small python GUI for custom hall-effect keyboards. It takes a QMK info.json, listens to QMK console hall-effect sensor data over HID via the hid_listen executable.

Listening to hid in format:
```| ($row, $col) Rescale: $value |```

Dependencies

Python3
PySide6

```pip install PySide6```

Credits:

https://github.com/PaulStoffregen/hid_listen for the hid_listen binaries 