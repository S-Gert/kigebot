#!/usr/bin/env python3

import rospy
from duckietown.dtros import DTROS, NodeType
from std_msgs.msg import String
from duckietown_msgs.msg import WheelsCmdStamped
from sensor_msgs.msg import Range
import time

speed = WheelsCmdStamped()

class TofPublish(DTROS):
    def __init__(self, node_name):
        super(TofPublish, self).__init__(node_name=node_name, node_type=NodeType.GENERIC)
        self.tofpub = rospy.Publisher('tof_publisher', String, queue_size=10)
        self.tof = rospy.Subscriber('/kigebot/front_center_tof_driver_node/range', Range, self.tof_sensor_callback)
        self.pub = rospy.Publisher('/kigebot/wheels_driver_node/wheels_cmd', WheelsCmdStamped, queue_size=10)
    
        self.distance = 0
        self.range = 0
        self.wall_sequence = 0
        
    def tof_sensor_callback(self,data):
        self.range = data.range
    
    def run(self):
        rate = rospy.Rate(20)
        while not rospy.is_shutdown():
            self.distance_cm = round(self.range*100, 1) #teeb tof sensori kauguse sentimeetriteks ja ümardab
            while self.distance_cm <= 35.0:
                self.distance_cm = round(self.range*100, 1)
                self.tofpub.publish("wall in progress")
                print("Wall in progress")
                speed.vel_right = 0
                speed.vel_left = 0.3
                self.pub.publish(speed)
                self.wall_sequence = 1
                rate.sleep()

            if self.wall_sequence == 1:
                time.sleep(0.15)
                speed.vel_right = 0.6
                speed.vel_left = 0.10
                self.pub.publish(speed)
                time.sleep(1.3)
                speed.vel_right = 0
                speed.vel_left = 0
                self.pub.publish(speed)
                time.sleep(0.1)
                speed.vel_right = 0.2
                speed.vel_left = 0.3
                self.pub.publish(speed)
                time.sleep(0.7)
                self.tofpub.publish("no wall")
                print("Wall done")
                self.wall_sequence = 0
            rate.sleep()

if __name__ == '__main__':
    node = TofPublish(node_name='tof_publisher')
    time.sleep(3) #prevents tof from activating on robot bootup
    node.run()
    rospy.spin()