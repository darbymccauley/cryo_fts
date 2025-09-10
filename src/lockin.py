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
        
        self.write(f'++addr {self.gpib_address}')
        self.write('++auto 1')
        self.write('eos 3')
        self.write('++eoi 1')
        self.write('++mode 1')
        self.write('OUTX 1')
        
    def init(self):
        """Initialize the lock-in amplifier."""
        print("Lock-in ID:", self.write('*IDN?', read=True))
        self.write('*CLS')

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
        freq = self.write(f'FREQ {freq}')

    def get_amp(self):
        """amp in V"""
        amp = self.write('SLVL?', read = True)
        return float(amp)
    
    def set_amp(self, amp):
        """amp in V"""
        amp = self.write(f'SLVL {amp}')

    def get_timeconstant(self):
        """time constant setting as defined in manual"""
        tc = self.write('OFLT?', read =True)
        return float(tc)
    
    def set_timeconstant(self, tc):
        """time constant setting as defined in manual"""
        tc = self.write(f'OFLT {tc}')
