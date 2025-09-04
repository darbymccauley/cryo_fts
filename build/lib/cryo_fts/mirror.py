from . import encoder, motor
import astropy.units as u
import threading
import time 

RES = 0.244140625 * u.um

class MirrorController:
    def __init__(self):
        self.encoder = encoder.EncoderController()
        self.motor = motor.MotorController()
        self.RESOLUTION = RES.to(self.motor.LENGTH_UNITS)
        self.OFFSET = None
        self._scan_thread = None
        self._stop_scan = threading.Event()

    def init(self):
        self.encoder.init()
        self.motor.init()
        self.find_offset()
        # self.encoder.start_transmission()
        return True
    
    def find_offset(self):
        self.motor.move_absolute(0)
        cnt0 = self.encoder.get_count()
        self.OFFSET = cnt0

    def get_position(self):
        cnt = self.encoder.get_count()
        pos = (cnt - self.OFFSET) * self.RESOLUTION
        return pos
    
    def close(self):
        self.encoder.close()
        self.motor.close()

    def move_absolute(self, position, length_unit=None, async_move=False):
        if async_move:
            t = threading.Thread(target=self.motor.move_absolute, args=(position, length_unit), daemon=True)
            t.start()
        else:
            self.motor.move_absolute(position, length_unit)

    def move_relative(self, position, length_unit=None, async_move=False):
        if async_move:
            t = threading.Thread(target=self.motor.move_relative, args=(position, length_unit), daemon=True)
            t.start()
        else:
            self.motor.move_relative(position, length_unit)

    def scan_and_collect(self, velocity, data_callback, velocity_unit=None):
        if self._scan_thread and self._scan_thread.is_alive():
            raise RuntimeError('Scan already in progress.')
        self._stop_scan.clear()
        self._scan_thread = threading.Thread(target=self._scan_worker, args=(velocity, data_callback, velocity_unit), daemon=True)
        self._scan_thread.start()

    def stop_scan(self):
        self._stop_scan.set()

    def _scan_worker(self, velocity, data_callback, velocity_unit):
        # Gonna need some reworking because I will need to include lockin somewhere in here
        try:
            self.encoder.start_transmission()
            self.motor.move_velocity(velocity, velocity_unit)
            while not self._stop_scan.is_set():
                latest = self.encoder.get_latest()
                if latest:
                    ts, cnt = latest
                    # pos = (cnt - self.OFFSET) * self.RESOLUTION
                    data_callback(ts, cnt)
        finally:
            self.motor.stop()
            self.encoder.stop_transmission()


    
