import os
from zaber_motion.ascii import Connection

class MotorController:
    def __init__(self, length_units='mm', velocity_units='mm/s'):
        self.LENGTH_UNITS = length_units
        self.VELOCITY_UNITS = velocity_units
        self.port = None
        self.device = None
        self.axis = None
        self.is_homed = False

        ports = [os.path.join('/dev', port) for port in os.listdir('/dev/') if port.startswith('tty.')]
        for port in ports:
            try:
                conn = Connection.open_serial_port(port)
                dev_list = conn.detect_devices()
                if not dev_list:
                    conn.close()
                    continue
                self.port = conn
                self.device = dev_list[0]
                print(f'Established connection to {self.device} on {self.port}')
                break
            except Exception:
                continue
        if not self.device:
            raise RuntimeError('Cannot connect to motor.')

    def init(self):
        if not self.device:
            raise RuntimeError('No motor device connected.')
        self.axis = self.device.get_axis(1)
        self.AXIS_MIN, self.AXIS_MAX = self.axis.settings.get('limit.min', self.LENGTH_UNITS), self.axis.settings.get('limit.max', self.LENGTH_UNITS)
        self.is_homed = self.axis.is_homed()
        if not self.is_homed:
            self.home_axis()
        return True

    def close(self):
        if self.port:
            self.port.close()
            self.port = None
            self.device = None
            self.axis = None

    def home_axis(self):
        self._check_axis_status()
        if not self.is_homed:
            self.axis.home()
            self.is_homed = True

    def move_absolute(self, position, length_unit=None):
        self._check_axis_status()
        unit = length_unit or self.LENGTH_UNITS
        self.axis.move_absolute(position, unit)

    def move_relative(self, position, length_unit=None):
        self._check_axis_status()
        unit = length_unit or self.LENGTH_UNITS
        self.axis.move_relative(position, unit)

    def _check_axis_status(self):
        if not self.axis:
            raise RuntimeError('Axis not initialized.')

    def get_position(self, length_unit=None):
        """
        Not to be used for accuracy over encoder."""
        self._check_axis_status()
        unit = length_unit or self.LENGTH_UNITS
        return self.axis.get_position(unit)

    def scan_track(self, velocity=0.0, velocity_unit=None):
        self._check_axis_status()
        self.move_absolute(self.AXIS_MIN)
        unit = velocity_unit or self.VELOCITY_UNITS
        self.axis.move_velocity(velocity, unit)

    def move_velocity(self, velocity=0.0, velocity_unit=None):
        self._check_axis_status()
        unit = velocity_unit or self.VELOCITY_UNITS
        self.axis.move_velocity(velocity, unit)

    def stop(self):
        self._check_axis_status()
        self.axis.stop()
    
