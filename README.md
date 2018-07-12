# TumbleDryer
Python program running on a Raspberry Pi Zero on which are connected a temperature/humidity sensor and a LCD display.
This project turns a basic tumble dryer into an automatic dryer capable of stoping when the clothes are dry and send a push notification on your phone.

## Motivation
My machine was woprking with a simple timer, without any display, but apparently with a temperature sensor (as far as I could see).
Nevertheless, is was probably defect or not working as it should because my clothes could easily turn very warm and even shrink if I let the machine run too long.

I have thus decided to start this project: open the dryer, install a temperature and humidity sensor in the exhaust pipe, install a Raspberry Pi Zero W, make a hole in the front panel, install a LCD screen and code !

## What does this program do ?

* The program constantly monitors the temperature and the humidity (every 10 seconds, configurable) and updates the LCD display.
* It looks for start-up, stops and dry conditions.
* When the machine is running, it calculates the estimated remaining time.
* When the dry condition is met (configurable via an INI file), the program sends a push notfication.

## What will the next features / improvements be ?

* I would like to connect the system to the start button, the door switch, the electrical motor and the heating elements so the program can actually drive the machine fully.
* The start and stop would correspond to the user pressing the start button or opening the door (not changes in temperature and humidity that are difficult to calibrate).

## Installation guide

### Hardware

#### Order parts
Part | Est. price | Link
-----| ---------- | ----
Raspberry pi Zero W + case (optional) | 20 € | https://www.ebay.com/sch/i.html?_nkw=Raspberry%20Pi%20Zero%20W
LCD screen 40x4 | 5€ | https://www.banggood.com/IIC-I2C-2004-204-20-x-4-Character-LCD-Display-Module-Blue-p-908616.html
Temperature and humidity sensor SHT-30 | 3€ | https://www.ebay.com/sch/i.html?_nkw=SHT30%20breakout

#### Installation in the dryder
![installback](http://ordoki.ddns.net:8081/IMG_20180619_174023.jpg)
![installsensor](http://ordoki.ddns.net:8081/IMG_20180618_192630.jpg)

### Software

#### Setup an SSH server on the Raspberry Pi

#### Install required Python packages

#### Create a account to receive push notifications

#### Install MySQL

#### Clone this repository

#### Create a deamon using supervisor


