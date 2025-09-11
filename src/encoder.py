import os
import serial
import time
import threading
import queue

class EncoderController:
    def __init__(self, baudrate=9600, timeout=0.1):
        """
        Instantiate connection to the RLS LA11 encoder via an RLS E201-9S USB encoder interface.

        Inputs:
            baudrate (int): number of changes per second to the signal during transmission (default=9600)
            timeout (float): time [s] to wait for response before raising a time-out error (default=0.1)
        """
        self.port = None
        self.device = None
        self.connection = None
        self.transmitting = False
        self.current_position = None
        self.data_queue = queue.Queue()
        self._reading_thread = None
        self._stop_thread = threading.Event()
        self.POS_LEN = 9 # bit-length of position data

        ports = [p.device for p in serial.tools.list_ports.comports()]
        for port in ports:
            try:
                conn = serial.Serial(port, baudrate=baudrate, timeout=timeout)
                conn.write(b'v')
                rsp = conn.readall().decode('utf-8', errors='ignore').strip()
                if rsp:
                    self.device = rsp
                    self.port = port
                    self.connection = conn
                    print(f'Established connection to {self.device} on {self.port}')
                    break
                else:
                    conn.close()
            except Exception:
                continue
        if not self.device:
            raise RuntimeError('Cannot connect to encoder.')

    def init(self):
        """
        Initialize the encoder.
        """
        cmds = [
            'B26\r' # ensure bit-length is 26
            ]
        for cmd in cmds:
            self.write(cmd, read=True)

    def close(self):
        """
        Stop transmission and close connection.
        """
        if self.transmitting:
            self.stop_transmission()
        if self.connection and self.connection.is_open:
            self.connection.close()
        print('Encoder connection closed.')

    def _clear_buffer(self):
        """
        Empty any pending bytes from the buffer.
        """
        while self.connection.in_waiting:
            self.connection.read(self.connection.in_waiting)
            time.sleep(0.01)

    def write(self, cmd, read=False, timeout=2.0):
        """
        Send a command to the encoder.

        Inputs:
            cmd (str) : command to send to the encoder
            read (bool): read response from the encoder after sending command (default=False)
            timeout (float): time [s] to wait for read response before raising a time-out error (default=2.0)
        """
        if isinstance(cmd, str):
            cmd = cmd.encode('ascii')
        self._clear_buffer()
        self.connection.write(cmd)
        if read:
            return self.read(timeout=timeout)

    def read(self, timeout=2.0):
        """
        Read from the encoder.
        
        Inputs: 
            timeout (float): time [s] to wait for read response before raising a time-out error (default=2.0)
        """
        if self.transmitting:
            raise RuntimeError('Stop transmission before reading.')
        self.connection.timeout = timeout
        rsp = self.connection.readline()
        if not rsp:
            raise TimeoutError('No response from encoder.')
        return rsp.decode('utf-8', errors='ignore').strip()

    def start_transmission(self):
        """
        Enable continuous transmission and start background reader.
        """
        if self.transmitting:
            return
        self.write('1')  # Start continuous transmission
        self.transmitting = True
        self._stop_thread.clear()
        self._reading_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reading_thread.start()
        print('Continuous transmission started.')

    def stop_transmission(self):
        """
        Disable continuous transmission and stop background reader.
        """
        if not self.transmitting:
            return
        self.write('0')
        time.sleep(0.05)
        self._stop_thread.set()
        if self._reading_thread:
            self._reading_thread.join(timeout=1.0)
        self.transmitting = False
        self._clear_buffer()
        print('Continuous transmission stopped.')

    def _read_loop(self):
        """
        Background reader for position and time data.
        """
        dat_len = self.POS_LEN
        while not self._stop_thread.is_set():
            try:
                data = self.connection.read(dat_len)
                if len(data) == dat_len:
                    try:
                        pos = int(data.decode('ascii'))
                        self.current_position = pos
                        self.data_queue.put((time.time(), pos)) # store position with timestamp
                    except ValueError:
                        continue
            except Exception as e:
                print(f'Read loop error: {e}')
            
    def get_count(self):
        """
        Get the current count in either transmission mode.
        """
        if self.transmitting:
            return self.current_position
        else:
            rsp = self.write('?', read=True)
            try:
                return int(rsp)
            except ValueError:
                raise RuntimeError(f'Invalid response: {rsp}')
            
    def get_latest(self):
        """
        Get the latest (timestamp, position) from the queue.
        """
        try:
            while True:
                ts, pos = self.data_queue.get_nowait()
        except queue.Empty:
            pass
        return (ts, pos) if 'ts' in locals() else None