import os
import serial
import time
import threading
import queue
import numpy as np
import serial.tools.list_ports

class LockinController:
    def __init__(self, gpib_address=8, baudrate=115200, timeout=1.0):
        """
        Instantiate connection to SR865A lock-in amplifier via Prologix GPIB-USB controller.
        """
        self.gpib_address = gpib_address
        self.timeout = timeout
        self.port = None
        self.device = None
        self.connection = None
        self.transmitting = False
        self.data_queue = queue.Queue()
        self._reading_thread = None
        self._stop_thread = threading.Event()

        #find and connect to Prologix controller
        ports = [p.device for p in serial.tools.list_ports.comports()]

        for port in ports:
            try:
                conn = serial.Serial(port, baudrate=baudrate, timeout=timeout)
                conn.reset_input_buffer()
                conn.reset_output_buffer()

                conn.write(b'++ver\r\n')
                time.sleep(0.1)
                response = conn.read(100).decode('utf-8', errors='ignore').strip()

                if 'Prologix' in response:
                    self.connection = conn
                    self.port = port
                    self.device = response
                    print(f'Established connection to {self.device} on {self.port}')
                    break
                else:
                    conn.close()
            except Exception:
                continue
        if not self.connection:
            raise RuntimeError('Cannot connect to lockin.')
        
    def init(self):
        """Initialize the lock-in amplifier."""
        self.write(f'++addr {self.gpib_address}')
        self.write('++auto 1')
        self.write('eos 3')
        self.write('++eoi 1')
        self.write('++mode 1')
        self.write('OUTX 1')
        print("Lock-in ID:", self.write('*IDN?', read=True))
        self.write('*CLS')
        self.write('RSRC EXT')

    def close(self):
        """Close connection."""
        if self.transmitting:
            self.stop_transmission()
        if self.connection and self.connection.is_open:
            self.connection.close()
        print('Lock-in connection closed.')

    def _clear_buffer(self):
        """Clear buffer."""
        while self.connection.in_waiting:
            self.connection.read(self.connection.in_waiting)
            time.sleep(0.01)

    def write(self, cmd, read=False, timeout=2.0):
        """Send a command to the lock-in."""
        if isinstance(cmd, str):
            cmd = cmd.encode('ascii')
        self._clear_buffer()
        self.connection.write(cmd + b'\r\n')
        if read:
            return self.read(timeout=timeout)

    def read(self, timeout=2.0):
        """Read from the lockin."""
        self.connection.timeout = timeout
        rsp = self.connection.readline()
        if not rsp:
            raise TimeoutError('No response from lockin.')
        return rsp.decode('utf-8', errors='ignore').strip()
    
    def get_x_y_r_theta(self):
        """x, y, and r in V. theta in degrees."""
        xyrtheta = self.write('SNAPD?', read = True)
        x, y, r, theta = xyrtheta.split(',')
        return float(x), float (y), float(r), float(theta)
    
    def get_freq(self):
        """freq in Hz"""
        freq = self.write('FREQ?', read=True)
        return float(freq)
    
    def set_freq(self, freq): #for some reason, ths doesn't seem to work- not sure why
        """freq in Hz"""
        self.write(f'FREQ {freq}')

    def get_amp(self):
        """amp in V"""
        amp = self.write('SLVL?', read = True)
        return float(amp)
    
    def set_amp(self, amp):
        """amp in V"""
        self.write(f'SLVL {amp}')

    def get_timeconstant(self):
        """time constant setting as defined in manual"""
        tc = self.write('OFLT?', read =True)
        return float(tc)
    
    def set_timeconstant(self, tc):
        """time constant setting as defined in manual"""
        self.write(f'OFLT {tc}')

    def get_sens(self):
        """sensitivity setting as defined in the manual"""
        sens = self.write('SCAL?', read = True)
        return float(sens)
    
    def set_sens(self, sens):
        """sensitivity setting as defined in the manual"""
        self.write(f'SCAL {sens}')

    def start_transmission(self, sample_rate = 10):
        """
        Enable continuous transmission and start background reader.
        """
        if self.transmitting:
            return
        self.transmitting = True
        self._stop_thread.clear()
        self._reading_thread = threading.Thread(target=self._read_loop, args=(sample_rate,), daemon=True)
        self._reading_thread.start()
        print('Continuous transmission started.')

    def stop_transmission(self):
        """
        Disable continuous transmission and stop background reader.
        """
        if not self.transmitting:
            return
        self._stop_thread.set()
        if self._reading_thread:
            self._reading_thread.join(timeout=1.0)
        self.transmitting = False
        self._clear_buffer()
        print('Continuous transmission stopped.') 

    def _read_loop(self, sample_rate):
        """
        Background reader for lockin data.
        """
        period = 1.0/sample_rate
        while not self._stop_thread.is_set():
            try:
                #get x, y, r, and theta data
                x, y, r, theta = self.get_x_y_r_theta()
                timestamp = time.time()
                self.data_queue.put({
                    'timestamp': timestamp,
                    'x': x,
                    'y': y,
                    'r': r,
                    'theta': theta})
                time.sleep(period)
            except Exception as e:
                print(f'Read loop error: {e}') 
    
    def get_closest_time(self, target_time):
        """get the lock-in reading closest to target time"""
        all_data = self.get_all()
        if not all_data:
            return None
        else:
            closest = min(all_data, key= lambda d: abs(d['timestamp'] - target_time))
            return closest
    
    def get_latest(self):
        """Get the latest (x, y, r, theta) from the queue."""
        latest = None
        try:
            while True:
                latest = self.data_queue.get_nowait()
        except queue.Empty:
            pass
        return latest

    def get_all(self):
        data = []
        try:
            while True:
                data.append(self.data_queue.get_nowait())
        except queue.Empty:
            pass
        return data