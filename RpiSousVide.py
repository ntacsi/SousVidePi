# -*- coding: utf-8 -*-

from multiprocessing import Process, Pipe, Queue, current_process
from Queue import Full
import os, time
import RPi.GPIO as GPIO
import PIDController
import Temp1Wire, mcp3208
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, jsonify

global parent_conn, statusQ
global xml_root, template_name, pinHeat, pinGPIOList, tempSensorId, tempSensorPin
global oneWireDir

app = Flask(__name__, template_folder='templates')


# Parameters that are used in the temperature control process
class Param:
    status = {
        "temp": "0",
        "elapsed": "0",
        "mode": "off",
        "cycle_time": 2.0,
        "duty_cycle": 0.0,
        "boil_duty_cycle": 100,
        "set_point": 0.0,
        "boil_manage_temp": 50,
        "num_pnts_smooth": 5,
        "k_param": 45,
        "i_param": 160,
        "d_param": 5
    }


# main web page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        # render main page
        return render_template(template_name, mode=Param.status["mode"], set_point=Param.status["set_point"],
                               duty_cycle=Param.status["duty_cycle"], cycle_time=Param.status["cycle_time"],
                               k_param=Param.status["k_param"], i_param=Param.status["i_param"],
                               d_param=Param.status["d_param"])

    else:  # request.method == 'POST' (first temp sensor / backwards compatibility)
        Param.status["mode"] = request.form["mode"]
        Param.status["set_point"] = float(request.form["setpoint"])
        Param.status["duty_cycle"] = float(request.form["dutycycle"])  # is boil duty cycle if mode == "boil"
        Param.status["cycle_time"] = float(request.form["cycletime"])
        Param.status["boil_manage_temp"] = float(request.form.get("boilManageTemp", Param.status["boil_manage_temp"]))
        Param.status["num_pnts_smooth"] = int(request.form.get("numPntsSmooth", Param.status["num_pnts_smooth"]))
        Param.status["k_param"] = float(request.form["k"])
        Param.status["i_param"] = float(request.form["i"])
        Param.status["d_param"] = float(request.form["d"])

        # send to main temp control process
        # if did not receive variable key value in POST, the Param class default is used
        parent_conn.send(Param.status)

        return 'OK'


# post GPIO
@app.route('/GPIO_Toggle/<GPIO_Num>/<onoff>', methods=['GET'])
def GPIO_Toggle(GPIO_Num=None, onoff=None):

    if len(pinGPIOList) >= int(GPIO_Num):
        out = {"pin": pinGPIOList[int(GPIO_Num)-1], "status": "off"}
        if onoff == "on":
            GPIO.output(pinGPIOList[int(GPIO_Num)-1], ON)
            out["status"] = "on"
            print("GPIO Pin #%s is toggled on" % pinGPIOList[int(GPIO_Num)-1])
        else:  # off
            GPIO.output(pinGPIOList[int(GPIO_Num)-1], OFF)
            print("GPIO Pin #%s is toggled off" % pinGPIOList[int(GPIO_Num)-1])
    else:
        out = {"pin": 0, "status": "off"}

    return jsonify(**out)


@app.route('/getstatus')  # only GET
def getstatus():
    # blocking receive - current status
    Param.status = statusQ.get()
    return jsonify(**Param.status)


# Stand Alone Get Temperature Process
def gettempProc(conn, myTempSensor = None):
    p = current_process()
    print('Starting:', p.name, p.pid)
    if myTempSensor is not None:
        while True:
            t = time.time()
            time.sleep(2)
            num = myTempSensor.readTempC()
            elapsed = "%.2f" % (time.time() - t)
            conn.send([num, elapsed])
    else:
        myADC = mcp3208.mcp3208(tempSensorPin)
        while True:
            t = time.time()
            time.sleep(2)
            num = myADC.temp_get()
            elapsed = "%.2f" % (time.time() - t)
            conn.send([num, elapsed])


# Get time heating element is on and off during a set cycle time
def getonofftime(cycle_time, duty_cycle):
    duty = duty_cycle/100.0
    on_time = cycle_time*duty
    off_time = cycle_time*(1.0-duty)
    return [on_time, off_time]


# Stand Alone Heat Process using GPIO
def heatProcGPIO(cycle_time, duty_cycle, pinNum, conn):
    p = current_process()
    print('Starting:', p.name, p.pid)
    if pinNum > 0:
        GPIO.setup(pinNum, GPIO.OUT)
        while True:
            while conn.poll():  # get last
                cycle_time, duty_cycle = conn.recv()
            conn.send([cycle_time, duty_cycle])
            if duty_cycle == 0:
                GPIO.output(pinNum, OFF)
                time.sleep(cycle_time)
            elif duty_cycle == 100:
                GPIO.output(pinNum, ON)
                time.sleep(cycle_time)
            else:
                on_time, off_time = getonofftime(cycle_time, duty_cycle)
                GPIO.output(pinNum, ON)
                time.sleep(on_time)
                GPIO.output(pinNum, OFF)
                time.sleep(off_time)


def unPackParamInitAndPost(paramStatus):
    mode = paramStatus["mode"]
    cycle_time = paramStatus["cycle_time"]
    duty_cycle = paramStatus["duty_cycle"]
    boil_duty_cycle = paramStatus["boil_duty_cycle"]
    set_point = paramStatus["set_point"]
    boil_manage_temp = paramStatus["boil_manage_temp"]
    num_pnts_smooth = paramStatus["num_pnts_smooth"]
    k_param = paramStatus["k_param"]
    i_param = paramStatus["i_param"]
    d_param = paramStatus["d_param"]

    return mode, cycle_time, duty_cycle, boil_duty_cycle, set_point, boil_manage_temp, num_pnts_smooth, \
        k_param, i_param, d_param


def packParamGet(temp, elapsed, mode, cycle_time, duty_cycle, boil_duty_cycle, set_point,
                 boil_manage_temp, num_pnts_smooth, k_param, i_param, d_param):

    Param.status["temp"] = temp
    Param.status["elapsed"] = elapsed
    Param.status["mode"] = mode
    Param.status["cycle_time"] = cycle_time
    Param.status["duty_cycle"] = duty_cycle
    Param.status["boil_duty_cycle"] = boil_duty_cycle
    Param.status["set_point"] = set_point
    Param.status["boil_manage_temp"] = boil_manage_temp
    Param.status["num_pnts_smooth"] = num_pnts_smooth
    Param.status["k_param"] = k_param
    Param.status["i_param"] = i_param
    Param.status["d_param"] = d_param

    return Param.status


# Main Temperature Control Process
def tempControlProc(myTempSensor=None, pinNum, paramStatus, statusQ, conn):
        mode, cycle_time, duty_cycle, boil_duty_cycle, set_point, boil_manage_temp, num_pnts_smooth, \
            k_param, i_param, d_param = unPackParamInitAndPost(paramStatus)

        p = current_process()
        print('Starting:', p.name, p.pid)

        # Pipe to communicate with "Get Temperature Process"
        parent_conn_temp, child_conn_temp = Pipe()
        # Start Get Temperature Process
        # ptemp = Process(name = "gettempProc", target=gettempProc, args=(child_conn_temp, myTempSensor))
        ptemp = Process(name="gettempProc", target=gettempProc, args=(child_conn_temp,))
        ptemp.daemon = True
        ptemp.start()

        # Pipe to communicate with "Heat Process"
        parent_conn_heat, child_conn_heat = Pipe()
        # Start Heat Process
        pheat = Process(name="heatProcGPIO", target=heatProcGPIO, args=(cycle_time, duty_cycle,
                                                                        pinNum, child_conn_heat))
        pheat.daemon = True
        pheat.start()

        temp_ma_list = []
        manage_boil_trigger = False
        temp_ma = 0.0
        readyPIDcalc = False

        while True:
            readytemp = False
            while parent_conn_temp.poll():  # Poll Get Temperature Process Pipe
                temp, elapsed = parent_conn_temp.recv()  # non blocking receive from Get Temperature Process

                if temp == -99:
                    print "Bad Temp Reading - retry"
                    continue

                temp_str = "%3.2f" % temp
                readytemp = True

            if readytemp:
                if mode == "auto":
                    temp_ma_list.append(temp)

                    # smooth data
                    temp_ma = 0.0  # moving avg init
                    while len(temp_ma_list) > num_pnts_smooth:
                        temp_ma_list.pop(0)  # remove oldest elements in list

                    if len(temp_ma_list) < num_pnts_smooth:
                        for temp_pnt in temp_ma_list:
                            temp_ma += temp_pnt
                        temp_ma /= len(temp_ma_list)
                    else:  # len(temp_ma_list) == num_pnts_smooth
                        for temp_idx in range(num_pnts_smooth):
                            temp_ma += temp_ma_list[temp_idx]
                        temp_ma /= num_pnts_smooth

                    # calculate PID every cycle
                    if readyPIDcalc:
                        pid = PIDController.PIDController(cycle_time, k_param, i_param, d_param)  # init pid
                        duty_cycle = pid.calcPID(temp_ma, set_point, True)
                        # send to heat process every cycle
                        parent_conn_heat.send([cycle_time, duty_cycle])
                        readyPIDcalc = False

                if mode == "boil":
                    if (temp > boil_manage_temp) and manage_boil_trigger:  # do once
                        manage_boil_trigger = False
                        duty_cycle = boil_duty_cycle
                        parent_conn_heat.send([cycle_time, duty_cycle])

                # put current status in queue
                try:
                    paramStatus = packParamGet(temp_str, elapsed, mode, cycle_time, duty_cycle,
                                               boil_duty_cycle, set_point, boil_manage_temp,
                                               num_pnts_smooth, k_param, i_param, d_param)
                    statusQ.put(paramStatus)  # GET request
                except Full:
                    pass

                while statusQ.qsize() >= 2:
                    statusQ.get()  # remove old status

                # print("Current Temp: %3.2f C, Heat Output: %3.1f%%" % (temp, duty_cycle))

                # logdata(temp, duty_cycle)

            while parent_conn_heat.poll():  # Poll Heat Process Pipe
                cycle_time, duty_cycle = parent_conn_heat.recv()  # non blocking receive from Heat Process
                readyPIDcalc = True

            readyPOST = False
            while conn.poll():  # POST settings - Received POST from web browser or Android device
                paramStatus = conn.recv()
                mode, cycle_time, duty_cycle_temp, boil_duty_cycle, set_point, boil_manage_temp, num_pnts_smooth, \
                    k_param, i_param, d_param = unPackParamInitAndPost(paramStatus)

                readyPOST = True
            if readyPOST:
                if mode == "auto":
                    print("auto selected")
                    pid = PIDController.PIDController(cycle_time, k_param, i_param, d_param)  # init pid
                    duty_cycle = pid.calcPID(temp_ma, set_point, True)
                    parent_conn_heat.send([cycle_time, duty_cycle])
                if mode == "boil":
                    print("boil selected")
                    boil_duty_cycle = duty_cycle_temp
                    duty_cycle = 100  # full power to boil manage temperature
                    manage_boil_trigger = True
                    parent_conn_heat.send([cycle_time, duty_cycle])
                if mode == "manual":
                    print("manual selected")
                    duty_cycle = duty_cycle_temp
                    parent_conn_heat.send([cycle_time, duty_cycle])
                if mode == "off":
                    print("off selected")
                    duty_cycle = 0
                    parent_conn_heat.send([cycle_time, duty_cycle])
            time.sleep(.01)


# def logdata(tank, temp, heat):
#     f = open("brewery" + str(tank) + ".csv", "ab")
#     f.write("%3.1f;%3.3f;%3.3f\n" % (getbrewtime(), temp, heat))
#     f.close()


if __name__ == '__main__':
    # Retrieve root element from config.xml for parsing
    tree = ET.parse('config.xml')
    xml_root = tree.getroot()
    template_name = xml_root.find('Template').text.strip()
    root_dir_elem = xml_root.find('RootDir')
    if root_dir_elem is not None:
        os.chdir(root_dir_elem.text.strip())
    else:
        print("No RootDir tag found in config.xml, running from current directory")

    gpioNumberingScheme = xml_root.find('GPIO_pin_numbering_scheme').text.strip()
    if gpioNumberingScheme == "BOARD":
        GPIO.setmode(GPIO.BOARD)
    else:
        GPIO.setmode(GPIO.BCM)

    gpioInverted = xml_root.find('GPIO_Inverted').text.strip()
    if gpioInverted == "0":
        ON = 1
        OFF = 0
    else:
        ON = 0
        OFF = 1

    pinHeat = int(xml_root.find('Heat_Pin').text.strip())

    pinGPIOList = []
    for pin in xml_root.iter('GPIO_Pin'):
        pinGPIOList.append(int(pin.text.strip()))

    for pin in pinGPIOList:
        GPIO.setup(pin, GPIO.OUT)

    statusQ = Queue(2)  # blocking queue
    parent_conn, child_conn = Pipe()

    tempSensorId = xml_root.find('Temp_Sensor_Id').text.strip()
    if not tempSensorId == "":
        myTempSensor = Temp1Wire.Temp1Wire(tempSensorId)
        p = Process(name="tempControlProc", target=tempControlProc,
                    args=(pinHeat, Param.status, statusQ, child_conn, myTempSensor))
        p.start()

    tempSensorPin = xml_root.find('Temp_Sensor_Pin').text.strip()
    if not tempSensorPin == "":
        p = Process(name="tempControlProc", target=tempControlProc,
                    args=(pinHeat, Param.status, statusQ, child_conn))
        p.start()

    app.debug = True
    app.run(use_reloader=False, host='0.0.0.0')
