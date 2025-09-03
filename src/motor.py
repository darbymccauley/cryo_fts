import os
from zaber_motion.ascii import Connection
import astropy.units as u

class MotorController:
    def __init__(self, length_units='mm', velocity_units='mm/s'):
        """
        Instantiate connection to the Zaber mirror motor.
        
        Inputs:
            length_units (str): units to measure lengths in the system (default='mm')
            velcocity_units (str): units to measure velocities in the system (default='mm/s')
        """
        self.LENGTH_UNITS = length_units
        self.VELOCITY_UNITS = velocity_units
        self.port = None
        self.device = None
        self.axis = None
        self.is_homed = False

        ports = [os.path.join('/dev', p) for p in os.listdir('/dev/') if p.startswith('tty.')]
        for port in ports:
            try:
                conn = Connection.open_serial_port(port, direct=True)
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
        """
        Initialize the Zaber motor. Homes the axis if not already homed.
        """
        if not self.device:
            raise RuntimeError('No motor device connected.')
        self.axis = self.device.get_axis(1)
        self.AXIS_MIN, self.AXIS_MAX = self.axis.settings.get('limit.min', self.LENGTH_UNITS), self.axis.settings.get('limit.max', self.LENGTH_UNITS)
        self.MAXSPEED = self.device.settings.get('maxspeed', self.VELOCITY_UNITS)
        self.is_homed = self.axis.is_homed()
        if not self.is_homed:
            self.home_axis()

    def close(self):
        """
        Close connection to the motor.
        """
        if self.port:
            self.port.close()
            self.port = None
            self.device = None
            self.axis = None

    def home_axis(self):
        """
        Home the axis to determine a relative point along the track.
        """
        self._check_axis_status()
        if not self.is_homed:
            self.axis.home()
            self.is_homed = True

    def move_absolute(self, position, length_unit=None):
        """
        Move the motor to an absolute position along the track.
        
        Inputs:
            position (float): where to move the motor to
            length_unit (str): units associated with 'position' (if None, defaults to globally defined units)
        """
        self._check_axis_status()
        unit = length_unit or self.LENGTH_UNITS
        self.axis.move_absolute(position, unit)

    def move_relative(self, position, length_unit=None):
        """
        Move the motor to position relative to the current motor position.
        
        Inputs:
            position (float): how far to move relative to current position
            length_unit (str): units associated with 'position' (if None, defaults to globally defined units)
        """
        self._check_axis_status()
        unit = length_unit or self.LENGTH_UNITS
        self.axis.move_relative(position, unit)

    def _check_axis_status(self):
        """
        Check that the axis has been initialized.
        """
        if not self.axis:
            raise RuntimeError('Axis not initialized.')

    def get_position(self, length_unit=None):
        """
        Get the position of the motor (according to the motor's internal reference.)
        ***Not to be used for accuracy over encoder readings.***
        
        Inputs:
            length_unit (str): units to return position in (if None, defaults to globally defined units)

        Returns: position in specified 'length_units'
        """
        self._check_axis_status()
        unit = length_unit or self.LENGTH_UNITS
        return self.axis.get_position(unit)

    def scan_track(self, velocity=10.0, velocity_unit=None):
        """
        Scan the whole length of the track at a particular velocity. Motor returns to home before beginning scan.

        Inputs:
            velocity (float): velocity of motor as it scans (defaults to max speed)
            velocity_units (str): units associated with 'velocity' (if None, defaults to globally defined units)
        """
        self._check_axis_status()
        self.move_absolute(self.AXIS_MIN)
        self.move_velocity(velocity, velocity_unit)

    def move_velocity(self, velocity=10.0, velocity_unit=None):
        """
        Move the motor at a particular velocity, starting at current position until the end of the track.
        
        Inputs:
            velocity (float): velocity of motor as it scans (defaults to max speed)
            velocity_units (str): units associated with 'velocity' (if None, defaults to globally defined units)
        """
        self._check_axis_status()
        unit = velocity_unit or self.VELOCITY_UNITS
        assert velocity * u.Unit(unit) < (self.MAXSPEED * u.Unit(self.VELOCITY_UNITS)).to(unit), 'Velocity requested larger than motor maxspeed.'
        self.axis.move_velocity(velocity, unit)

    def stop(self):
        """
        Stop current axis processes.
        """
        self._check_axis_status()
        self.axis.stop()