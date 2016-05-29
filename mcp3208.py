import spidev
import math

class mcp3208:
    def __init__(self, tempSensorPin):
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = 120000
        self.tempSensorPin = tempSensorPin


    def readadc(self):
    # read SPI data from MCP3208 chip, 8 possible adc's (0 thru 7)
        if self.tempSensorPin > 7 or self.tempSensorPin < 0:
            return -1
        r = spi.xfer2([1, 8 + self.tempSensorPin << 4, 0])
        adcout = ((r[1] & 3) << 8) + r[2]
        return adcout


    #thermistor reading function
    def temp_get(self):
        value = self.readadc() #read the adc
        volts = (value * 3.3) / 1024 #calculate the voltage
        ohms = ((1/volts)*3300)-1000 #calculate the ohms of the thermististor

        lnohm = math.log1p(ohms) #take ln(ohms)

        #a, b, & c values from http://www.thermistor.com/calculators.php
        #using curve R (-6.2%/C @ 25C) Mil Ratio X
        a =  0.002197222470870
        b =  0.000161097632222
        c =  0.000000125008328

        #Steinhart Hart Equation
        # T = 1/(a + b[ln(ohm)] + c[ln(ohm)]^3)

        t1 = (b*lnohm) # b[ln(ohm)]

        c2 = c*lnohm # c[ln(ohm)]

        t2 = math.pow(c2,3) # c[ln(ohm)]^3

        temp = 1/(a + t1 + t2) #calcualte temperature

        tempc = temp - 273.15 - 4 #K to C
        # the -4 is error correction for bad python math

        return tempc
