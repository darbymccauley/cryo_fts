from toptica.lasersdk.dlcpro.v2_2_0 import DLCpro, NetworkConnection
from encoder import EncoderController
from motor import MotorController
import astropy.units as u
import threading
import time 
import pandas as pd
from datetime import datetime
import numpy as np

RES = 0.244140625 * u.um

class TopticaController: 
    def __init__(self, ip_address = ''): #insert ip address
        self.ip_address = ip_address
        self.dlc = None
        self.motor = MotorController()
        self.encoder = EncoderController()
        self.RESOLUTION = RES.to(self.motor.LENGTH_UNITS)
        self.OFFSET = None
        self._scan_thread = None
        self._stop_scan = threading.Event()
        self.data_store = []
        self._save_filename = None

    def init(self):
        self.dlc = DLCpro(NetworkConnection(self.ip_address))
        print(f"Connected to Toptica at {self.ip_address}")

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

    def close(self):
        self.stop_scan()
        self.encoder.close()
        self.motor.close()
        self.dlc.close()

    def emission_on(self):
        self.dlc.laser_operation.emission.set(True)
        print("Emission on")

    def emission_off(self):
        self.dlc.laser_operation.emission.set(False)
        print("Emission off")
    
    def set_frequency(self, freq_ghz):
        self.dlc.frequency.frequency_set.set(freq_ghz)
    
    def get_frequency(self):
        return self.dlc.frequency.frequency_act.get()
    
    def setup_lockin(self, freq_hz, int_time_ms, amp_gain, phase_deg):
        self.dlc.lockin.frequency.set(freq_hz)
        self.dlc.lockin.integration_time.set(int_time_ms)
        self.dlc.lockin.amplifier_gain.set(amp_gain)
        self.dlc.lockin.phase.set(phase_deg)

    def get_photocurrent(self):
        return self.dlc.lockin.lock_in_value.get()
    
    def reset_lockin(self):
        self.dlc.lockin.lock_in_reset()

    def move_absolute(self, position, length_unit=None, async_move=False):
        if async_move:
            t = threading.Thread(target=self.motor.move_absolute, args=(position, length_unit), daemon=True)
            t.start()
        else:
            self.motor.move_absolute(position, length_unit)
    
    def scan_and_collect(self, freq_ghz, velocity, velocity_unit = None, sample_rate = 10, lockin_freq_hz = 5000, lockin_int_time_ms = 100, amplifier_gain = 1e6, save_to_csv = None):
        """start a scan and save results to csv"""
        if self._scan_thread and self._scan_thread.is_alive():
            raise RuntimeError('Scan already in progress.')
        self._stop_scan.clear()
        self.data_store = []
        if save_to_csv is None: #automatically save data with timestamped name if name not given
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_to_csv = f"C:/Users/vnh2/Desktop/FTS/cryo_fts_data/scan_data{timestamp}.csv" # XXX dont like the hard-coding
        self._save_filename = save_to_csv

        self._scan_thread = threading.Thread(target=self._scan_worker, args=(freq_ghz, velocity, velocity_unit, sample_rate, lockin_freq_hz, lockin_int_time_ms, amplifier_gain), daemon=True)
        self._scan_thread.start()

    def stop_scan(self):
        """stop scan and save data to csv"""
        self._stop_scan.set()
        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join()
        if self.data_store:
            df = pd.DataFrame(self.data_store)
            df.to_csv(self._save_filename, index=False)
            print(f"Saved scan data to {self._save_filename}")

    def _scan_worker(self, freq_ghz, velocity, velocity_unit, sample_rate, lockin_freq_hz, lockin_int_time_ms, amplifier_gain):
        try:
            #self.emission_on()
            #time.sleep(1)

            self.set_frequency(freq_ghz)
            time.sleep(5) #give photomixers time to stabilize

            self.setup_lockin(freq_hz= lockin_freq_hz, int_time_ms= lockin_int_time_ms, amp_gain= amplifier_gain, phase_deg=0)

            self.encoder.start_transmission()
            self.motor.move_velocity(velocity, velocity_unit)
            period = 1 / sample_rate

            last_pos = None
            stationary_count = 0 
            STATIONARY_THRESHOLD = 5
            
            with open(self._save_filename, 'w') as f:
                f.write("timestamp,position_mm,frequency_ghz,photocurrent_na\n")
                
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

                    #toptica lockin
                    self.reset_lockin()
                    time.sleep(lockin_int_time_ms/ 1000)
                    photocurrent, valid = self.get_photocurrent()
                    freq_act = self.get_frequency()

                    record = ({
                        'timestamp': t_enc,
                        'position_mm': pos,
                        'freq_ghz': freq_act,
                        'photocurrent_na': photocurrent})
                    self.data_store.append(record)
                    f.write(f"{t_enc},{pos},{freq_act},{photocurrent}\n")
                    f.flush()
                    time.sleep(period)
        finally:
            self.motor.stop()
            self.encoder.stop_transmission()
            #self.emission_off()