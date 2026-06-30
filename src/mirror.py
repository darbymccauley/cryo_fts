from .encoder import EncoderController
from .motor import MotorController
# from .lockin import LockinController
import astropy.units as u
import threading
import time 
import pandas as pd
from datetime import datetime

RES = 0.244140625 * u.um

class MirrorController:
    def __init__(self):
        # self.lockin = LockinController(gpib_address=8)
        self.encoder = EncoderController()
        self.motor = MotorController()
        self.RESOLUTION = RES.to(self.motor.LENGTH_UNITS)
        self.OFFSET = None
        self._scan_thread = None
        self._stop_scan = threading.Event()
        self.data_store = []
        self._save_filename = None

    def init(self):
        # self.lockin.init()
        self.encoder.init()
        self.motor.init()
        self.find_offset()
        self.encoder.start_transmission()
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
        # self.lockin.close()

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

    def scan_and_collect(self, velocity, velocity_unit=None, poll_interval=0.001, save_to_csv=None):
        """start a scan and save results to csv"""
        if self._scan_thread and self._scan_thread.is_alive():
            raise RuntimeError('Scan already in progress.')
        self._stop_scan.clear()
        self.data_store = []
        if save_to_csv is None: #automatically save data with timestamped name if name not given
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_to_csv = f"C:/Users/vnh2/Desktop/FTS/cryo_fts_data/scan_data{timestamp}.csv" # XXX dont like the hard-coding
        self._save_filename = save_to_csv

        self._scan_thread = threading.Thread(target=self._scan_worker, args=(velocity, velocity_unit, poll_interval), daemon=True)
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

    def _scan_worker(self, velocity, velocity_unit, poll_interval=None):
        try:
            if poll_interval is None:
                poll_interval = self.encoder.TRANSMISSION_RATE
            self.encoder.start_transmission()
            self.motor.move_velocity(velocity, velocity_unit)
            # lockin_rate = max(int(sample_rate * 2), 20)
            # self.lockin.start_transmission(sample_rate=lockin_rate)
            # period = 1 / sample_rate

            last_pos = None
            stationary_start = None
            STATIONARY_TIMEOUT = 0.5
            STATIONARY_TOLERANCE = self.encoder.ENC_RES * 1.5
            
            with open(self._save_filename, 'w') as f:
                f.write("timestamp,position_mm\n") #,x,y,r,theta\n")
                while not self._stop_scan.is_set():
                    samples = self.encoder.get_all()
                    if not samples:
                        time.sleep(poll_interval)
                        continue

                    should_stop = False
                    for t_enc, cnt in samples:
                        pos = (cnt - self.OFFSET) * self.RESOLUTION
                        pos_value = pos.value

                        if pos_value >= self.motor.AXIS_MAX * 0.98: #if scan reaches the end, stop
                            should_stop = True
                        
                        if last_pos is not None: #if encoder stops moving for a while, stop
                            pos_diff = abs(pos_value - last_pos)
                            if pos_diff <= STATIONARY_TOLERANCE:
                                if stationary_start is None:
                                    stationary_start = t_enc
                                elif t_enc - stationary_start >= STATIONARY_TIMEOUT:
                                    should_stop = True
                            else:
                                stationary_start = None
                        last_pos = pos_value

                        record = ({
                            'timestamp': t_enc,
                            'position_mm': pos_value,
                            # 'x': x,
                            # 'y': y,
                            # 'r': r,
                            # 'theta': theta
                            })
                        self.data_store.append(record)
                        f.write(f"{t_enc},{pos_value}\n") #,{x},{y},{r},{theta}\n")

                        if should_stop:
                            break

                    f.flush()
                    if should_stop:
                        break
                    time.sleep(poll_interval)
        finally:
            self.motor.stop()
            self.encoder.stop_transmission()
            # self.lockin.stop_transmission()