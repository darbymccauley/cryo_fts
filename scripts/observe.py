from cryo_fts.motor import MotorController
from cryo_fts.lockin import LockInController
import numpy as np
from datetime import date
import time

def main():
    lockin = LockInController()
    motor = MotorController(unit='mm')

    try:
        lockin.init()
        time.sleep(3)
        motor.init()
        time.sleep(1)
        motor.home()

        RES = 0.5  # [mm]
        NSTEPS = int(motor.AXIS_MAX / RES) + 1
        print(f'Total steps in run: {NSTEPS}')
        NSAMPS = 50

        data = []
        positions = []

        for n in range(NSTEPS):
            pos = n * RES
            try:
                motor.move_absolute(pos)
                current_pos = motor.get_pos()
                positions.append(current_pos)
                time.sleep(0.5)
                # lockin.autogain()
                d = lockin.record(N=NSAMPS)
                data.append(d)
                print(f'Count: {n + 1}/{NSTEPS} | Position: {current_pos:.2f} mm')
                time.sleep(0.5)
            except Exception as e:
                print(f'FAILURE OCCURRED at step {n}: {e}')
                continue

        if data:
            data = np.vstack(data)
            database = {
                'Date': date.today().strftime("%Y-%m-%d"),
                'RES_mm': RES,
                'NINT': NSAMPS,
                'NSTEPS': NSTEPS,
                'X_V': data[:, 0],
                'Y_V': data[:, 1],
                'R_V': data[:, 2],
                'THETA_deg': data[:, 3],
                # 'REF_FREQ_Hz': data[:, 4],
                'MOTOR_POS_mm': positions,
            }
            np.savez('data/gunn_diode_test_05.npz', **database)
            print('Data saved.')
        else:
            print('No data collected.')

    except KeyboardInterrupt:
        print('KeyboardInterrupt detected. Closing devices.')

    finally:
        lockin.close()
        motor.close()
        print('Devices closed.')

if __name__ == "__main__":
    main()