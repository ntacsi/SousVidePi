from subprocess import Popen, PIPE


class Temp1Wire:
    def __init__(self, tempSensorId):
        self.tempSensorId = tempSensorId
        self.oneWireDir = "/sys/bus/w1/devices/"
        print(("Constructing 1W sensor %s" % (tempSensorId)))

    def readTempC(self):
        pipe = Popen(["cat", self.oneWireDir + self.tempSensorId + "/w1_slave"], stdout=PIPE)
        result = pipe.communicate()[0]

		try:
			if result.split('\n')[0].split(' ')[11] == "YES":
				temp_C = float(result.split("=")[-1]) / 1000  # temp in Celcius
			else:
				temp_C = -99  # bad temp reading
        except:
            print("Failed to read temperature from file")

        return temp_C
