# import encoder, motor, lockin
from encoder import EncoderController
from motor import MotorController
from lockin import LockinController
import astropy.units as u
import threading
import time 
import pandas as pd
from datetime import datetime

RES = 0.244140625 * u.um

class MirrorController:
    def __init__(self):
        self.lockin = LockinController(gpib_address=8)
        self.encoder = EncoderController()
        self.motor = MotorController()
        self.RESOLUTION = RES.to(self.motor.LENGTH_UNITS)
        self.OFFSET = None
        self._scan_thread = None
        self._stop_scan = threading.Event()
        self.data_store = []
        self._save_filename = None

    def init(self):
        self.lockin.init()
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
        self.stop_scan()
        self.encoder.close()
        self.motor.close()
        self.lockin.close()

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

    def scan_and_collect(self, velocity, velocity_unit=None, sample_rate=10, save_to_csv=None):
        """start a scan and save results to csv"""
        if self._scan_thread and self._scan_thread.is_alive():
            raise RuntimeError('Scan already in progress.')
        self._stop_scan.clear()
        self.data_store = []
        if save_to_csv is None: #automatically save data with timestamped name if name not given
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_to_csv = f"data/scan_data/{timestamp}.csv" # XXX dont like the hard-coding
        self._save_filename = save_to_csv

        self._scan_thread = threading.Thread(target=self._scan_worker, args=(velocity, velocity_unit, sample_rate), daemon=True)
        self._scan_thread.start()

    def stop_scan(self):
        """stop scan and save data to csv"""
        self._stop_scan.set()
        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join()
        if self.data_store:
            df = pd.DataFrame(self.data_store)
            if 'position' in df.columns:
                df['position_mm'] = df['position'].apply(lambda p: p.to(u.mm).value if p is not None else None)
            df.to_csv(self._save_filename, index=False)
            print(f"Saved scan data to {self._save_filename}")

    def _scan_worker(self, velocity, velocity_unit, sample_rate):
        try:
            self.encoder.start_transmission()
            self.motor.move_velocity(velocity, velocity_unit)
            lockin_rate = max(int(sample_rate * 2), 20)
            self.lockin.start_transmission(sample_rate=lockin_rate)
            period = 1 / sample_rate

            last_pos = None
            stationary_count = 0 
            STATIONARY_THRESHOLD = 5
            
            with open(self._save_filename, 'w') as f:
                f.write("timestamp,position_mm,x,y,r,theta\n")
                
                iteration = 0
                while not self._stop_scan.is_set():
                    iteration += 1
                    
                    enc_latest = self.encoder.get_latest()
                    t_enc = None
                    pos = None
                    
                    if enc_latest:
                        t_enc, cnt = enc_latest
                        pos = (cnt - self.OFFSET) * self.RESOLUTION
                        pos_value = pos.value

                        if pos_value >= self.motor.AXIS_MAX * 0.98: #if scan reaches the end, stop
                            break
                        
                        if last_pos is not None: #if encoder stops moving for a while, stop
                            pos_diff = abs(pos_value - last_pos)
                            if pos_diff < 0.001:
                                stationary_count += 1
                                if stationary_count >= STATIONARY_THRESHOLD:
                                    break
                            else:
                                stationary_count = 0                       
                        last_pos = pos_value
                        pos = pos_value
                    else:
                        pos = None

                    #lockin
                    lockin_data = self.lockin.get_closest_time(t_enc)

                    if lockin_data:
                        x = lockin_data['x']
                        y = lockin_data['y']
                        r = lockin_data['r']
                        theta = lockin_data['theta']
                    else:
                        x = y = r = theta = None

                    record = ({
                        'timestamp': t_enc,
                        'position_mm': pos,
                        'x': x,
                        'y': y,
                        'r': r,
                        'theta': theta})
                    self.data_store.append(record)
                    f.write(f"{t_enc},{pos},{x},{y},{r},{theta}\n")
                    f.flush()
                    time.sleep(period)
        finally:
            self.motor.stop()
            self.encoder.stop_transmission()
            self.lockin.stop_transmission()