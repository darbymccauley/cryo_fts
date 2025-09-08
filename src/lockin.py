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
        
        def write(self, cmd):
            """Send a command to the lockin."""
            if not cmd.startswith('++'):
                cmd = '++' + cmd
            self.connection.write((cmd + '\r\n').encode('ascii'))
            time.sleep(0.05)

        self.write(f'++addr {self.gpib_address}')
        self.write('++auto 1')
        self.write('eos 3')
        self.write('++eoi 1')
        self.write('++mode 1')
        self.write('OUTX 1')