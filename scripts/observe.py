from cryo_fts.motor import MotorController
from cryo_fts.lockin import LockinController
import numpy as np
from datetime import date
import time

def main():
    lockin = LockinController()
    motor = MotorController(length_units='mm')

    try:
        lockin.init()
        time.sleep(3)
        motor.init()
        time.sleep(1)
        motor.home_axis()

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
                time.sleep(0.1)  
                
                current_pos = motor.get_position()
                positions.append(current_pos)
                
                d = [lockin.get_x_y_r_theta() for _ in range(NSAMPS)]  # Collect multiple samples
                data.append(np.mean(np.array(d))) 
                
                print(f'Count: {n + 1}/{NSTEPS} | Position: {current_pos:.2f} mm')
                time.sleep(0.1) 

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
                'MOTOR_POS_mm': positions,
            }
            np.savez('../data/trial-run-diode.npz', **database)
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