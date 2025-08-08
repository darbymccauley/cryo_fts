import os
import serial
import time
import threading

class EncoderController:
    def __init__(self, baudrate=9600, timeout=0.1):
        self.port = None
        self.device = None
        self.connection = None
        self.transmitting = False
        self.current_position = None
        self._reading_thread = None
        self._stop_thread = threading.Event()

        # Try to connect to the encoder
        ports = [os.path.join('/dev', p) for p in os.listdir('/dev/') if p.startswith('tty.')]
        for port in ports:
            try:
                conn = serial.Serial(port, baudrate=baudrate, timeout=timeout)
                try:
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
                    conn.close()
            except serial.SerialException:
                continue
        if not self.device:
            raise RuntimeError('Cannot connect to encoder.')

    def init(self):
        """Initialize the encoder."""
        cmds = ['B26\r']
        for cmd in cmds:
            self.write(cmd, read=True)

    def close(self):
        """Stop transmission and close connection."""
        if self.transmitting:
            self.stop_transmission()
        if self.connection and self.connection.is_open:
            self.connection.close()
        print('Connection closed.')

    def _clear_buffer(self):
        """Empty any pending bytes from the buffer."""
        while self.connection.in_waiting:
            self.connection.read(self.connection.in_waiting)
            time.sleep(0.01)

    def write(self, cmd, read=False, timeout=2.0):
        """Send a command to the encoder."""
        if isinstance(cmd, str):
            cmd = cmd.encode('ascii')
        self._clear_buffer()
        self.connection.write(cmd)
        if read:
            return self.read(timeout=timeout)

    def read(self, timeout=2.0):
        """Read from the encoder."""
        if self.transmitting:
            raise RuntimeError('Stop transmission before reading.')
        self.connection.timeout = timeout
        resp = self.connection.readline()
        if not resp:
            raise TimeoutError('No response from encoder.')
        return resp.decode('utf-8', errors='ignore').strip()

    def start_transmission(self):
        """Enable continuous transmission and start background reader."""
        if self.transmitting:
            return
        self.write('1')  # Start continuous transmission
        self.transmitting = True
        self._stop_thread.clear()
        self._reading_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reading_thread.start()
        print('Continuous transmission started.')

    def stop_transmission(self):
        """Disable continuous transmission and stop background reader."""
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
        dat_len = 9
        while not self._stop_thread.is_set():
            try:
                data = self.connection.read(dat_len)
                if len(data) == dat_len:
                    try:
                        self.current_position = int(data.decode('ascii'))
                    except ValueError:
                        continue
            except Exception as e:
                print(f'Read loop error: {e}')
            
    def get_count(self):
        """Get the current count in either mode."""
        if self.transmitting:
            return self.current_position
        else:
            resp = self.write('?', read=True)
            try:
                return int(resp)
            except ValueError:
                raise RuntimeError(f'Invalid response: {resp}')