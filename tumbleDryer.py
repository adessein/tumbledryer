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

import argparse
import smbus
import RPi_I2C_driver
from pushsafer import init, Client
import configparser as ConfigParser
import subprocess

import time
from datetime import datetime as dt
from datetime import timedelta as td

import logging, sys
from os import path

import pymysql

from numpy import mean, abs, max

if 'logger' not in locals():
    logfmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    log_filename = path.splitext(__file__)[0] + '.log'
    filelog = logging.FileHandler(log_filename)
    filelog.setLevel(logging.DEBUG)
    filelog.setFormatter(logfmt)
    logger.addHandler(filelog)

    stdlog = logging.StreamHandler(sys.stdout)
    stdlog.setFormatter(logfmt)
    stdlog.setLevel(logging.INFO)
    logger.addHandler(stdlog)

parser = argparse.ArgumentParser()
parser.add_argument('--now', action="store_true", default=False, help='starts immediately')
args = parser.parse_args()

Config = ConfigParser.ConfigParser()
Config.read("tumbleDryer.ini")

pushKey = Config.get('Pushsafer', 'Key')
pushDeviceID = Config.get('Pushsafer', 'DeviceId')

dbHost = Config.get('Database', 'Host')
dbUser = Config.get('Database', 'User')
dbName = Config.get('Database', 'Name')
dbPassword = Config.get('Database', 'Password')

STARTUP_DT = float(Config.get('Thresholds', 'STARTUP_DT'))
STOP_T = float(Config.get('Thresholds', 'STOP_T'))
STOP_DT = float(Config.get('Thresholds', 'STOP_DT'))
STOP_DH = float(Config.get('Thresholds', 'STOP_DH'))
DRY_H = float(Config.get('Thresholds', 'DRY_H'))
DRY_T = float(Config.get('Thresholds', 'DRY_T'))

AVG_N = int(Config.get('Averaging', 'AVG_N'))
DH_TABLE_SIZE = int(Config.get('Averaging', 'DH_TABLE_SIZE'))

PERIOD = float(Config.get('General', 'PERIOD'))
MAX_FATAL = int(Config.get('General', 'MAX_FATAL'))

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

def readConfigFile():
    global pushKey, pushDeviceID, STARTUP_DT, STARTUP_DH, STOP_T, STOP_DT
    global STOP_DH, DRY_H, DRY_T, AVG_N, DH_TABLE_SIZE, PERIOD, MAX_FATAL

    Config.read("tumbleDryer.ini")

    pushKey = Config.get('Pushsafer', 'Key')
    pushDeviceID = Config.get('Pushsafer', 'DeviceId')

    STARTUP_DT = float(Config.get('Thresholds', 'STARTUP_DT'))
    STARTUP_DH = float(Config.get('Thresholds', 'STARTUP_DH'))
    STOP_T = float(Config.get('Thresholds', 'STOP_T'))
    STOP_DT = float(Config.get('Thresholds', 'STOP_DT'))
    STOP_DH = float(Config.get('Thresholds', 'STOP_DH'))
    DRY_H = float(Config.get('Thresholds', 'DRY_H'))
    DRY_T = float(Config.get('Thresholds', 'DRY_T'))

    AVG_N = int(Config.get('Averaging', 'AVG_N'))
    DH_TABLE_SIZE = int(Config.get('Averaging', 'DH_TABLE_SIZE'))

    PERIOD = float(Config.get('General', 'PERIOD'))
    MAX_FATAL = int(Config.get('General', 'MAX_FATAL'))


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
    nows=dt.now().strftime('%H:%M')

    if running and not dry:
        # Generate the time strings nows, rems and etas
        if remainTime :
            h, s = divmod(remainTime, 3600)
            m, s = divmod(s, 60)
            rems="%02d:%02d" % (h, m)
            etas=(dt.now()+td(seconds=remainTime)).strftime('%H:%M')
        else :
            rems="??:??"
            etas="??:??"

        # Generate the 1th line
        l1 = "{:.1f} deg   CLK {:s}".format(T1, nows)
        l2 = "{:.1f} %RH   REM {:s}".format(H1, rems)
        l3 = '{:>20}'.format("ETA "+etas)
        # Generate the 4th line with the progress bar
        a = int(completed / 10.0)
        b = 10-a
        l4 = chr(0xFF)*a + "_"*b + " " + "{:>4}".format("{:.0f}%".format(completed))

    if running and dry :
        l1 = "{:.1f} deg   CLK {:s}".format(T1, nows)
        l2 = "{:20}".format("{:.1f} %RH".format(H1))
        l3 = " CLOTHES ARE DRY    "
        l4 = " STOP THE MACHINE   "

    if not running :
        l1 = "{:.1f} deg   CLK {:s}".format(T1, nows)
        l2 = "{:20}".format("{:.1f} %RH".format(H1))
        l3 = "{:20}".format("")
        l4 = " MACHINE READY      "

    mylcd.lcd_display_string(l1, 1)
    mylcd.lcd_display_string(l2, 2)
    mylcd.lcd_display_string(l3, 3)
    mylcd.lcd_display_string(l4, 4)
    #mylcd.lcd_display_string_pos(chr(7),4,17)
    mylcd.lcd_display_string_pos(chr(0),4,18)
    mylcd.lcd_display_string_pos(chr(wifiSignal()),4,19)

if __name__ == "__main__":
    logger.info("Starting program")
    t0 = time.time()

    # Connects to the database
    db = pymysql.connect(host=dbHost,
                         user=dbUser,
                         password=dbPassword,
                         db=dbName)
    cur = db.cursor()

    # Initite I2C bus
    bus = smbus.SMBus(1)

    # Initiate LCD
    mylcd = RPi_I2C_driver.lcd()
    mylcd.lcd_load_custom_chars(fontdata)
    mylcd.lcd_clear()
    mylcd.backlight(1)
    lcdBacklight = True

    T0 = None
    H0 = None
    Hstart = None

    dHavg = None
    remainTime = None
    completed = 0

    running = False
    dry = False
    notificationFlag = False

    manualTrigger = args.now

    dHtable = []
    dT = None
    dH = None

    fatalCount = 0

    while True:
        try :
            readConfigFile()
            T1, H1 = getTempRH()
            if any((T0, H0)) :
                dT = (T1-T0)
                dH = (H1-H0)

                dHtable.append(dH)
                while len(dHtable) > DH_TABLE_SIZE:
                    dHtable.pop(0)

                if len(dHtable) >= AVG_N:
                    dHavg = mean(dHtable[-AVG_N:])
                else :
                    dHavg = None

                #print("dT = {:.2f} dH = {:.2f}".format(dT,dH))
                if ((dT >= STARTUP_DT) and not running) or manualTrigger:
                    logger.info("Startup conditions detected")
                    manualTrigger = False
                    completed = 0
                    remainTime = None
                    running = True
                    startTime = time.time()

                if running and T1 > DRY_T and H1 < DRY_H:
                    dry = True

                if running and ((dT <= STOP_DT) or (len(dHtable) == DH_TABLE_SIZE and max(abs(dHtable))<STOP_DH) ):
                    logger.info("Stopped state detected")
                    running = False
                    dry = False
            T0 = T1
            H0 = H1

            if running :
                completed = (100.0-H1) / (100.0-DRY_H) * 100.0
                if dHavg:
                    if (dHavg < 0) and (DRY_H < H1):
                        remainTime = (DRY_H-H1) / dHavg * PERIOD
                    else:
                        # if dHaverage > 0 then we do not update the remaining time
                        pass
                else:
                    # There is not enough data to calculate the remainTime
                    remainTime = None

            if running and dry and not notificationFlag:
                logger.info("The clothes are dry: sending notification")
                elapsed_time = time.time() - startTime
                ets = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))

                # Send notification
                init(pushKey)
                pushMsg = "Elapsed time : " + ets + "\n" + \
                          "Now {:.2f} C {:.2f} %RH\n".format(T1, H1) + \
                          "Delta {:.2f} C {:.2f} %RH".format(dT, dH)
                Client("").send_message(message = pushMsg,
                                        title = "Clothes are dry",
                                        device = pushDeviceID,
                                        icon = "62",
                                        sound = "1",
                                        vibration = "2",
                                        url = "",
                                        urltitle = "",
                                        time2live = "0",
                                        picture1 = "",
                                        picture2 = "",
                                        picture3 = "")
                notificationFlag = True

            updateDisplay()

            sql = "INSERT INTO `Logs` (`TimeStamp`, `Temperature`, " + \
                  "`DT`, `Humidity`, `DH`, `DHavg`, `Running`, `Dry`, " + \
                  "`LCDBacklight`, `RemainingSec`, `Completed`) " + \
                  " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            sqlData = (time.strftime('%Y-%m-%d %H:%M:%S'),
                       "{:.2f}".format(T1),
                       None if dT is None else "{:.2f}".format(dT),
                       "{:.2f}".format(H1),
                       None if dH is None else "{:.2f}".format(dH),
                       None if dHavg is None else "{:.2f}".format(dHavg),
                       "1" if running else "0",
                       "1" if dry else "0",
                       "1" if lcdBacklight else "0",
                       None if remainTime is None else "{:.0f}".format(remainTime),
                       "{:.0f}".format(completed))
            cur.execute(sql, sqlData)
            db.commit()

            sleepTime = PERIOD - ((time.time() - t0) % PERIOD)
            time.sleep(sleepTime)

        except Exception as e:
            fatalCount = fatalCount + 1
            logger.fatal(e)
            time.sleep(PERIOD)
            if fatalCount == MAX_FATAL:
                logger.info("The system has crached 5 times : system STOPPED")
                # Close database connection
                db.close()
                # Send notification
                #init(pushKey)
                #pushMsg = "The system has crached 5 times : system STOPPED"
                #Client("").send_message(message = pushMsg,
                #                        title = "FATAL ERROR",
                #                        device = pushDeviceID,
                #                        icon = "1",
                #                        sound = "0",
                #                        vibration = "2",
                #                        url = "",
                #                        urltitle = "",
                #                        time2live = "0",
                #                        picture1 = "",
                #                        picture2 = "",
                #                        picture3 = "")
                sys.exit(-2)
