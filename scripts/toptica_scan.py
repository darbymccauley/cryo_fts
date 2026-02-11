import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from laser import TopticaController
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--frequency', help = 'Emission Frequency (GHz)', default= 100)
parser.add_argument('--velocity', help='Magnitude of scan velocity', default=None)
parser.add_argument('--units', help='Units of scan velocity', default=None)
parser.add_argument('--sample_rate', help = 'Sampling rate (Hz)', default = 10)
parser.add_argument('--amplifier_gain', help = 'Amplifier Gain (V/A)', default = 1e6)
parser.add_argument('--lockin_freq', help='Toptica Lockin modulation frequency (Hz)',default=5000.0)
parser.add_argument('--lockin_int_time', help='Toptica Lockin integration time (ms)', default=100.0)
parser.add_argument('--csv_file', help='Where to save collected data', default = None)

args = parser.parse_args()

toptica = TopticaController()
toptica.init()
print("Moving to start position")
toptica.move_absolute(0, 'mm')

print(f"Scanning at velocity = {args.velocity} {args.units}, frequency {args.frequency} GHz")
toptica.scan_and_collect(
    freq_ghz=args.frequency,
    velocity=args.velocity,
    velocity_unit=args.units,
    sample_rate=args.sample_rate,
    lockin_freq_hz=args.lockin_freq,
    lockin_int_time_ms=args.lockin_int_time,
    amplifier_gain=args.amplifier_gain,
    save_to_csv=args.csv_file
)

while toptica._scan_thread and toptica._scan_thread.is_alive():
    toptica._scan_thread.join(timeout=0.5)

toptica.stop_scan()
toptica.close()
print("Scan done")