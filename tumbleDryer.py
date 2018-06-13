import smbus
import time, sys
from pushsafer import init, Client
import configparser as ConfigParser

Config = ConfigParser.ConfigParser()
Config.read("tumbleDryer.ini")

pushKey = Config.get('Pushsafer', 'Key')
pushDeviceID = Config.get('Pushsafer', 'DeviceId')

STARTUP_DT = 4
STARTUP_DH = 5

STOP_T = 30
STOP_DT = -5

DRY_H = 30
DRY_T = 40


def getData(): 
    # SHT31 address, 0x44(68)
    bus.write_i2c_block_data(0x44, 0x2C, [0x06])
       
    time.sleep(0.5)
        
    # SHT31 address, 0x44(68)
    # Read data back from 0x00(00), 6 bytes
    # Temp MSB, Temp LSB, Temp CRC, Humididty MSB, Humidity LSB, Humidity CRC
    data = bus.read_i2c_block_data(0x44, 0x00, 6)
         
    # Convert the data
    temp = data[0] * 256 + data[1]
    cTemp = -45 + (175 * temp / 65535.0)
    fTemp = -49 + (315 * temp / 65535.0)
    humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
          
    return(cTemp, humidity)
    
if __name__ == "__main__":
    print("{:s}\tStarting program".format(time.strftime("%Y-%m-%d %H:%M:%S")))
    t0 = time.time()
    
    # Get I2C bus
    bus = smbus.SMBus(1)
    T0 = None
    H0 = None
    
    running = False
    dry = False
    
    while True:
        T1, H1 = getData()
        if any((T0, H0)) :
            dT = (T1-T0)
            dH = (H1-H0)            

            if (dT >= STARTUP_DT) and (dH >= STARTUP_DH):
                # Start condition
                running = True
                logName = time.strftime("%Y-%m-%d_%H-%M-%S")
                startTime = time.time()
                print("START")
            if (T1 >= STOP_T) and (dT <= STOP_DT):
                # Stop condition
                # add a condition on steady state if I did not catch the transition
                print("STOP")
                running = False
            if T1 > DRY_T and H1 < DRY_H :
                dry = True
                
        if running :
            msg = "{:s}\t{:.2f}\t{:.2f}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"),T1,H1)
            with open(logName+".log","a+") as f:
                f.write(msg)
        
        if running and dry :
            elapsed_time = time.time() - startTime
            ets = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            # Stop the machine        
            running = False
            
            # Send notification
            init(pushKey)
            pushMsg = "Elapsed time : " + ets + "\n"+ \
                      "Now {:.2f} C {:.2f} %%RH".format(T1, H1) + \
                      "Delta {:.2f} C {:.2f} %%RH".format(dT, dH)
            Client("").send_message(message = pushMsg,
                                    title = "Clothes are dry",
                                    device = pushDeviceID,
                                    icon = "1",
                                    sound = "0",
                                    vibration = "2",
                                    url = "",
                                    urltitle = "",
                                    time2live = "0",
                                    picture1 = "",
                                    picture2 = "",
                                    picture3 = "")
            
        T0 = T1
        H0 = H1            
        time.sleep(60.0 - ((time.time() - t0) % 60.0))
		
        
