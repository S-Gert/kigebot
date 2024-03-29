#!/usr/bin/env python3

import os
import numpy as np
import rospy
import smbus2
from duckietown.dtros import DTROS, NodeType
from std_msgs.msg import String
from smbus2 import SMBus
from duckietown_msgs.msg import WheelsCmdStamped, WheelEncoderStamped
from sensor_msgs.msg import Range
import time

speed = WheelsCmdStamped()

class MyPublisherNode(DTROS):
    def __init__(self, node_name):
        
        super(MyPublisherNode, self).__init__(node_name=node_name, node_type=NodeType.GENERIC)
        
        self.pub = rospy.Publisher('/kigebot/wheels_driver_node/wheels_cmd', WheelsCmdStamped, queue_size=10)
        self.tof = rospy.Subscriber('/kigebot/front_center_tof_driver_node/range', Range, self.callback)
        self.rwheel = rospy.Subscriber('/kigebot/right_wheel_encoder_node/tick', WheelEncoderStamped ,self.rightwheel)
        self.lwheel = rospy.Subscriber('/kigebot/left_wheel_encoder_node/tick', WheelEncoderStamped, self.leftwheel)
        self.seqLeft = rospy.Subscriber('/kigebot/left_wheel_encoder_node/tick', WheelEncoderStamped, self.time_leftwheel)
        self.seqRight = rospy.Subscriber('/kigebot/right_wheel_encoder_node/tick', WheelEncoderStamped ,self.time_rightwheel)
        
        self.bus = SMBus(1)
        self.range = 1
        self.right = 0
        self.left = 0
        self.timeL = 0
        self.timeR = 0
        
        self.ticks_left = 0
        self.prev_tick_left = 0
        self.ticks_right = 0
        self.prev_tick_right = 0
        self.rotation_wheel_left = 0
        self.rotation_wheel_right = 0
        self.delta_ticks_left = 0
        self.delta_ticks_right = 0
        self.baseline_wheel2wheel = 0.1 #rataste keskel vahe, meetrites
        
        self.delta_time = 0
        self.last_error = 0
        self.integral = 0
        self.prev_integral = 0
        self.previous_left = 0
        self.previous_right = 0
        
        self.sein = 0
    
    def callback(self, data):
        self.range = data.range
    
    def rightwheel(self, data):
        self.right = data.data
    
    def leftwheel(self, data):
        self.left = data.data
    
    def time_leftwheel(self, data):
        self.timeL = data.header.seq
    
    def time_rightwheel(self, data):
        self.timeR = data.header.seq

    def seina_manoover(self):
        pass
    
    def on_shutdown(self):
        speed.vel_left = 0
        speed.vel_right = 0
        self.pub.publish(speed)
        time.sleep(0.5)
        self.bus.close()
        rospy.on_shutdown()
        
    def run(self):
        rate = rospy.Rate(20)
        while not rospy.is_shutdown():
            read = self.bus.read_byte_data(62,17)
            read = bin(read)[2:].zfill(8)
            print(read)
            
            temp = self.bus.read_byte_data(62, 17)
            
            N_tot = 135                                                                             # total number of ticks per revolution
            R = 0.065                                                                               # insert value measured by ruler, in *meters*
            Kp = rospy.get_param("/p")
            Ki = rospy.get_param("/i")
            Kd = rospy.get_param("/d")
            
            alpha = 2 * np.pi / N_tot                                                               # wheel rotation per tick in radians. The angular resolution of our encoders is: {np.rad2deg(alpha)} degrees)
            
            self.ticks_right = self.right
            self.ticks_left = self.left
            
            self.delta_ticks_left = self.ticks_left-self.prev_tick_left                             # delta ticks of left wheel
            self.delta_ticks_right = self.ticks_right-self.prev_tick_right                          # delta ticks of right wheel
            self.rotation_wheel_left = alpha * self.delta_ticks_left                                # total rotation of left wheel
            self.rotation_wheel_right = alpha * self.delta_ticks_right                              # total rotation of right wheel
            #print(f"The left wheel rotated: ", np.rad2deg(self.rotation_wheel_left), "degrees")
            #print(f"The right wheel rotated: ", np.rad2deg(self.rotation_wheel_right), "degrees")
            
            d_left = R * self.rotation_wheel_left
            d_right = R * self.rotation_wheel_right  
            #print(f"The left wheel travelled: {d_left} meters")
            #print(f"The right wheel travelled: {d_right} meters")
            # How much has the robot rotated?
            
            kaugus_cm = round(self.range*100, 1)
            #print("kaugus on: ",kaugus_cm, "Cm")

            Delta_Theta = (d_right-d_left)/self.baseline_wheel2wheel # expressed in radians
            #print(f"The robot has rotated: {np.rad2deg(Delta_Theta)} degrees")
            
            self.prev_tick_left = self.ticks_left
            self.prev_tick_right = self.ticks_right
            #print("Left wheel time: ", self.timeL)
            #print("Right wheel time: ", self.timeR)
            
            ##############
            
            #wtravel = round(((d_left + d_right)*100)/2, 1)
            #print("The robot has travelled", wtravel, "Cm")
            
            #SEINSEISNEISNEISNIENSINEISNIEIENISIENIE
            
            while kaugus_cm <=10:
                kaugus_cm = round(self.range*100, 1)
                speed.vel_right = 0
                speed.vel_left = 0.06
                self.pub.publish(speed)
                self.sein = 1
                
            if self.sein == 1:
                speed.vel_right = 0.45
                speed.vel_left = 0.3
                self.pub.publish(speed)
                time.sleep(2.5)
                self.sein = 0
                
            # PID KONTROLLER
                
            max_kiirus = 0.6        
            näidik = []
            for indx, nr in enumerate(read):
                if nr == "1":
                    näidik.append(indx + 1)
            error = 4.5 - np.average(näidik)
            integral = self.prev_integral + error*self.delta_time
            integral = max(min(integral,2), -2)
            derivative = (error - self.last_error)/self.delta_time
            correction = Kp * error + Ki * integral + Kd * derivative
            speed.vel_left = max_kiirus - correction
            speed.vel_right = max_kiirus + correction
            self.previous_left = speed.vel_left
            self.previous_right = speed.vel_right
            if len(näidik) == 0:
                speed.vel_left = self.previous_left
                speed.vel_right = self.previous_right
            speed.vel_left = max(0.02, min(speed.vel_left, max_kiirus))
            speed.vel_right = max(0.02, min(speed.vel_right, max_kiirus))
            self.pub.publish(speed)
            self.last_error = error
            rate.sleep()
            
            print("---| P =", Kp, "|---| I =", Ki, "|---| D =", Kd, "|---")    
                
if __name__ == '__main__':
    node = MyPublisherNode(node_name='my_publisher_node')
    node.run()
    rospy.spin()
