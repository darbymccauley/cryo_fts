from cryo_fts.motor import MotorController
import time

def main():
    RES = 1     # [mm]
    m = MotorController(unit='mm')
    m.init()
    m.home()
    print(f'Current position: {m.get_pos():.2f} mm')
    NSTEPS = int(m.AXIS_MAX / RES) + 1

    try:
        for n in range(NSTEPS):    
            try:
                pos = n * RES
                m.move_absolute(pos)
                print(f'Current position: {m.get_pos():.2f} mm')
                time.sleep(2)
            except Exception as e:
                print(f'MOTOR FAILURE: {e}')
                continue 
    finally: 
        m.close()


if __name__ == "__main__":
    main()