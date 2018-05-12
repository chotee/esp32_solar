#!/usr/bin/python
'''
Ported to ESP32 by Chotee after being copied from
https://github.com/contactless/wb-mqtt-sht1x/blob/master/sht1x.py , rev:318d29e

---
Created on Oct 5, 2012

@author: Luca Nobili

This modules reads Humidity and Temperature from a Sensirion SHT1x sensor. I has been tested
both with an SHT11 and an SHT15.

It is meant to be used in a Raspberry Pi and depends on this module (http://code.google.com/p/raspberry-gpio-python/).

The module raspberry-gpio-python requires root privileges, therefore, to run this module you need to run your script as root.


Example Usage:

>>> from machine import Pin
>>> from sht1x import Sht1x
>>> sht1x = Sht1x(Pin(0), Pin(2))
>>> sht1x.read_temperature_C()
25.22
>>> sht1x.read_humidity()
52.6564216

'''
# import traceback
# import sys
# import time
# import logging
import math

import machine
from machine import Pin
import utime

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

#   Conversion coefficients from SHT15 datasheet
D1 = -39.6  # for 14 Bit @ 3V
D2 =  0.01 # for 14 Bit DEGC

C1 = -2.0468       # for 12 Bit
C2 =  0.0367       # for 12 Bit
C3 = -0.0000015955 # for 12 Bit
T1 =  0.01      # for 14 Bit @ 5V
T2 =  0.00008   # for 14 Bit @ 5V


class SystemError(Exception):
    pass


class GPIO(object):
    LOW  = 0
    HIGH = 1
    IN = Pin.IN
    OUT = Pin.OUT

    @classmethod
    def output(cls, pin, value):
        pin.value(value)

    @classmethod
    def input(cls, pin):
        return pin.value()

    @classmethod
    def setup(cls, pin, mode):
        pin.init(mode)


class logger(object):
    @classmethod
    def debug(cls, msg, *args):
        pass
        # print("DBG: " + (msg % args))

    @classmethod
    def error(cls, msg, *args):
        print("ERR: " + (msg % args))


class Sht1x(object):
    def __init__(self, dataPin, sckPin):
        self.dataPin = dataPin
        self.sckPin = sckPin

#    I deliberately will not implement read_temperature_F because I believe in the
#    in the Metric System (http://en.wikipedia.org/wiki/Metric_system)

    def read_temperature_C(self):
        temperatureCommand = 0b00000011

        self.__sendCommand(temperatureCommand)
        self.__waitForResult()
        rawTemperature = self.__getData16Bit()
        self.__skipCrc()
        # GPIO.cleanup()

        return rawTemperature * D2 + D1


    def read_humidity(self):
#        Get current temperature for humidity correction
        temperature = self.read_temperature_C()
        return self._read_humidity(temperature)

    def _read_humidity(self, temperature):
        humidityCommand = 0b00000101
        self.__sendCommand(humidityCommand)
        self.__waitForResult()
        rawHumidity = self.__getData16Bit()
        self.__skipCrc()
        # GPIO.cleanup()
#        Apply linear conversion to raw value
        linearHumidity = C1 + C2 * rawHumidity + C3 * rawHumidity * rawHumidity
#        Correct humidity value for current temperature
        return round((temperature - 25.0 ) * (T1 + T2 * rawHumidity) + linearHumidity, 1)

    def calculate_dew_point(self, temperature, humidity):
        if temperature > 0:
            tn = 243.12
            m = 17.62
        else:
            tn = 272.62
            m = 22.46
        return tn * (math.log(humidity / 100.0) + (m * temperature) / (tn + temperature)) / (m - math.log(humidity / 100.0) - m * temperature / (tn + temperature))

    def __sendCommand(self, command):
        #Transmission start
        GPIO.setup(self.dataPin, GPIO.OUT)
        GPIO.setup(self.sckPin, GPIO.OUT)

        GPIO.output(self.dataPin, GPIO.HIGH)
        self.__clockTick(GPIO.HIGH)
        GPIO.output(self.dataPin, GPIO.LOW)
        self.__clockTick(GPIO.LOW)
        self.__clockTick(GPIO.HIGH)
        GPIO.output(self.dataPin, GPIO.HIGH)
        self.__clockTick(GPIO.LOW)

        for i in range(8):
            GPIO.output(self.dataPin, command & (1 << 7 - i))
            self.__clockTick(GPIO.HIGH)
            self.__clockTick(GPIO.LOW)


        self.__clockTick(GPIO.HIGH)

        GPIO.setup(self.dataPin, GPIO.IN)

        ack = GPIO.input(self.dataPin)

        logger.debug("ack1: %s", ack)
        if ack != GPIO.LOW:
            logger.error("nack1")

        self.__clockTick(GPIO.LOW)

        ack = GPIO.input(self.dataPin)
        logger.debug("ack2: %s", ack)
        if ack != GPIO.HIGH:
            logger.error("nack2")

    def __clockTick(self, value):
        GPIO.output(self.sckPin, value)
        utime.sleep_us(1)  # 1 micro-second (was 100 nano-seconds)

    def __waitForResult(self):
        GPIO.setup(self.dataPin, GPIO.IN)

        for i in range(100):
#            10 milliseconds
            utime.sleep_ms(10)
            ack = GPIO.input(self.dataPin)
            if ack == GPIO.LOW:
                break
        if ack == GPIO.HIGH:
            raise SystemError

    def __getData16Bit(self):
        GPIO.setup(self.dataPin, GPIO.IN)
        GPIO.setup(self.sckPin, GPIO.OUT)
#        Get the most significant bits
        value = self.__shiftIn(8)
        value *= 256
#        Send the required ack
        GPIO.setup(self.dataPin, GPIO.OUT)
        GPIO.output(self.dataPin, GPIO.HIGH)
        GPIO.output(self.dataPin, GPIO.LOW)
        self.__clockTick(GPIO.HIGH)
        self.__clockTick(GPIO.LOW)
#        Get the least significant bits
        GPIO.setup(self.dataPin, GPIO.IN)
        value |= self.__shiftIn(8)

        return value

    def __shiftIn(self, bitNum):
        value = 0
        for i in range(bitNum):
            self.__clockTick(GPIO.HIGH)
            value = value * 2 + GPIO.input(self.dataPin)
            self.__clockTick(GPIO.LOW)
        return value

    def __skipCrc(self):
#        Skip acknowledge to end trans (no CRC)
        GPIO.setup(self.dataPin, GPIO.OUT)
        GPIO.setup(self.sckPin, GPIO.OUT)
        GPIO.output(self.dataPin, GPIO.HIGH)
        self.__clockTick(GPIO.HIGH)
        self.__clockTick(GPIO.LOW)

    def __connectionReset(self):
        GPIO.setup(self.dataPin, GPIO.OUT)
        GPIO.setup(self.sckPin, GPIO.OUT)
        GPIO.output(self.dataPin, GPIO.HIGH)
        for i in range(10):
            self.__clockTick(GPIO.HIGH)
            self.__clockTick(GPIO.LOW)
