#!/usr/bin/env python3

import rospy
from std_msgs.msg import String
import numpy as np
from smbus2 import SMBus
import my_publisher_node as mpn

class PidClass():
    def __init__(self):
        self.bus = SMBus(1)
        self.sens_middle = 4.5
        self.delta_time = 1/20
        self.integral = 0

    def pid_run(self, last_error, last_correction):
        while not rospy.is_shutdown():
            read = self.bus.read_byte_data(62,17)
            read = bin(read)[2:].zfill(8)
            
            Kp = float(rospy.get_param("/p", 0.100))
            Ki = float(rospy.get_param("/i", 0.001))
            Kd = float(rospy.get_param("/d", 0.017))
            
            line_sens = []
            
            for indx, nr in enumerate(read):
                if nr == "1":
                    line_sens.append(indx + 1)
                    
            if len(line_sens) > 0:
                error = self.sens_middle - np.average(line_sens)
            else:
                error = 0
            
            self.integral = self.integral + (error + last_error)*self.delta_time/2
            self.integral = min(max(self.integral, -2), 2)
            derivative = (error - last_error)/self.delta_time
            correction = Kp * error + Ki * self.integral + Kd * derivative
            
            if correction < -1 or correction > 1:
                correction = last_correction
            else:
                last_error = error
                last_correction = correction
            
            return line_sens, correction, last_correction, last_error