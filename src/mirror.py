from cryo_fts.encoder import EncoderController
from cryo_fts.motor import MotorController
import astropy.units as u

class MirrorController:
    def __init__(self):
        self.encoder = EncoderController()
        self.motor = MotorController()
        self.RESOLUTION = (0.244140625 * u.um).to(self.motor.LENGTH_UNITS)
        self.OFFSET = None

    def init(self):
        self.encoder.init()
        self.motor.init()
        self.find_offset()
        return True
    
    def find_offset(self):
        self.motor.move_absolute(0)
        cnt0 = self.encoder.get_count()
        self.OFFSET = cnt0

    def get_position(self):
        cnt = self.encoder.get_count()
        pos = (cnt - self.OFFSET) * self.RESOLUTION
        return pos
    
