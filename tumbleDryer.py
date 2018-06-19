# -*- coding: utf-8 -*-
"""
tumblerDryer
Arnaud DESSEIN
https://bitbucket.org/adessein/tumbledryer


Licence : GPL v3

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import smbus
import RPi_I2C_driver
from pushsafer import init, Client
import configparser as ConfigParser
import subprocess

import time
from datetime import datetime as dt
from datetime import timedelta as td

Config = ConfigParser.ConfigParser()
Config.read("tumbleDryer.ini")

pushKey = Config.get('Pushsafer', 'Key')
pushDeviceID = Config.get('Pushsafer', 'DeviceId')

STARTUP_DT = 2
STARTUP_DH = 5

STOP_T = 30
STOP_DT = -5

DRY_H = 30
DRY_T = 40

PERIOD = 2.0 # period in seconds

fontdata = [
        # Char 0 - Antena
        [ 0x0E, 0x11, 0x15, 0x0E, 0x04, 0x04, 0x04, 0x04],
        # Char 1 - No signal (cross)
        [ 0x00, 0x00, 0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11],
        # Char 2 - Level 1 
        [ 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10],
        # Char 3 - Level 2
        [ 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x18],
        # Char 4 - Level 3
        [ 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x0C, 0x1C],
        # Char 5 - Level 4
        [ 0x00, 0x00, 0x00, 0x00, 0x02, 0x06, 0x0E, 0x1E],
        # Char 6 - Level 5
        [ 0x00, 0x00, 0x00, 0x01, 0x03, 0x07, 0x0F, 0x1F],
        # Char 7 - Disk
        [ 0x00, 0x00, 0x00, 0x1E, 0x13, 0x11, 0x11, 0x1F ],
]

def getTempRH(): 
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
    humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
          
    return(cTemp, humidity)

def wifiSignal():
    # Get the wifi signal strength
    cmd = "iwconfig wlan0 | grep 'Quality='| cut -d= -f2 | awk '{split($1,A,\"/\"); print A[1]}'"
    proc = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE, universal_newlines=True)
    out, err = proc.communicate()
    if out :
        signal = round(int(out.strip())/70*4) + 2
    else :
    # if there is no connection then use signal char 1 (cross)
        signal = 1
    return(signal)

def updateDisplay():
    if running and not dry:
        # Generate the time strings nows, rems and etas
        nows=dt.now().strftime('%H:%M')
        h, s = divmod(remainTime, 3600)
        m, s = divmod(s, 60)
        rems="%02d:%02d" % (h, m)
        etas=(dt.now()+td(seconds=remainTime)).strftime('%H:%M')
    
        # Generate the 1th line
        l1 = "{:.1f} deg - CLK {:s}".format(T1, nows)
        l2 = "{:.1f} %RH - REM {:s}".format(H1, rems)
        l3 = "           ETA "+etas
        # Generate the 4th line with the progress bar
        a = int(completed / 10)
        b = 10-a
        l4 = chr(0xFF)*a + "_"*b + " " + str(completed) + "%"

    if running and dry :
        nows=dt.now().strftime('%H:%M')
        l1 = "{:.1f} deg - CLK {:s}".format(T1, nows)
        l2 = "{:.1f} %RH - REM --:--"
        l3 = "           ETA --:--"
        l4 = "STOP THE MACHINE"

    mylcd.lcd_display_string(l1, 1)
    mylcd.lcd_display_string(l2, 2)
    mylcd.lcd_display_string(l3, 3)
    mylcd.lcd_display_string(l4, 4)
    #mylcd.lcd_display_string_pos(chr(7),4,17)
    mylcd.lcd_display_string_pos(chr(0),4,18)
    mylcd.lcd_display_string_pos(chr(wifiSignal()),4,19)
    
if __name__ == "__main__":
    print("{:s}\tStarting program".format(time.strftime("%Y-%m-%d %H:%M:%S")))    
    t0 = time.time()
    
    # Initite I2C bus
    bus = smbus.SMBus(1)
    
    # Initiate LCD
    mylcd = RPi_I2C_driver.lcd()
    mylcd.lcd_load_custom_chars(fontdata)
    mylcd.lcd_clear()
    mylcd.backlight(0)

    T0 = None
    H0 = None
    Hstart = None
    
    running = False
    dry = False
    notificationFlag = False
    
    while True:
        T1, H1 = getTempRH()
        if any((T0, H0)) :
            dT = (T1-T0)
            dH = (H1-H0)            
            #if (dT >= STARTUP_DT) and (dH >= STARTUP_DH):
            if (dT >= STARTUP_DT) :
                # Start condition
                Hstart = H1
                running = True
                logName = time.strftime("%Y-%m-%d_%H-%M-%S")
                startTime = time.time()
                mylcd.backlight(1)
                print("START")
            if (T1 >= STOP_T) and (dT <= STOP_DT):
                # Stop condition
                # add a condition on steady state if I did not catch the transition                
                running = False
                mylcd.lcd_clear()
                mylcd.backlight(0)
                print("STOP")
            if T1 > DRY_T and H1 < DRY_H :
                dry = True
        T0 = T1
        H0 = H1  
                
        if running :
            completed = (DRY_H-H1) / (DRY_H-Hstart) * 100.0
            remainTime = (DRY_H-H1) / dH * PERIOD
            updateDisplay()
            msg = "{:s}\t{:.2f}\t{:.2f}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"),T1,H1)
            with open(logName+".log","a+") as f:
                f.write(msg)
        
        
        if running and dry and not notificationFlag:            
            elapsed_time = time.time() - startTime
            ets = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            
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
            notificationFlag = True
            
          
        time.sleep(PERIOD - ((time.time() - t0) % PERIOD))
		
        
