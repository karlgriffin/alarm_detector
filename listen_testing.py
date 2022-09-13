#!/usr/bin/python
import RPi.GPIO as GPIO
import time
import smtplib
import shutil
import os
import sys
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import socket
# local python file
import config as cf

class AlertSystem(object):
    
    def __init__(self):
        self.sample_audio_sleep = cf.variables["sample_audio_sleep"]
        self.required = cf.variables["required"]
        self.cycle = cf.variables["cycle"]
        self.max_temp = cf.variables["max_temp"]
        self.after_alert_sleep_time = cf.variables["after_alert_sleep_time"]
        self.daily_email_time = cf.variables["daily_email_time"]
        self.temp = 0
        self.count = 0
        self.reset = 0
        self.hostname = ""
        self.ip_address = ""
        
    def get_network_details(self):
        self.hostname  = socket.gethostname()
        self.ip_address = socket.gethostbyname(self.hostname)
        # print("IP address: {}".format(self.ip_address))
        
    def datetime_stamp(self):
        return(str(datetime.now()))
    
    def time_stamp(self):
        dt= datetime.now()
        time = dt.strftime("%H:%M")
        return(time)
    
    def daily_email(self):
        if self.time_stamp() == self.daily_email_time:
            self.confirmation_email()
            # print("Sent daily email, sleeping..")
            time.sleep(60)
                
    def confirmation_email(self):
        # print("Sending Email")
        time = self.datetime_stamp()
        fromaddr = cf.email_settings["fromaddr"]
        toaddr = cf.email_settings["toaddr"]
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = "Listening script running"
        body = "Time: {}\nIP: {}\nVariables: {}\nRPI: {}\nDisk: {}\nTemp: {}".format(
            time, self.ip_address, cf.variables, cf.rpi, self.disk_space_available(), self.temp
            )
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(cf.email_settings["server"])
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(cf.email_settings["fromaddr"], cf.email_settings["password"])
        text = msg.as_string()
        # print(text)
        server.sendmail(fromaddr, toaddr, text)
       
    def email(self):
        # print("Alert! - Sending Email")
        time = self.datetime_stamp()
        fromaddr = cf.email_settings["fromaddr"]
        toaddr = cf.email_settings["toaddr"]
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = "** HOME NOISE ALERT **"
        body = "{}\n[{}] instance(s) of noise within {} seconds has been detected".format(
            time, self.required, self.cycle)
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(cf.email_settings["server"])
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(cf.email_settings["fromaddr"], cf.email_settings["password"])
        text = msg.as_string()
        # print(text)
        server.sendmail(fromaddr, toaddr, text)
        
    def disk_space_available(self):
        total, used, free = shutil.disk_usage("/")
        total_space = (total // (2**30))
        used_space = (used // (2**30))
        free_space = (free // (2**30))
        return "[{}]/{}GB used, [{}]GB free".format(used_space, total_space, free_space)
        
    def callback(self, channel):
        if GPIO.input(channel):
            # print("Sound Detected")
            self.count += 1 
        else:
            # print("Sound Detected")
            self.count += 1
            
    def check_temp(self):
        temp = os.popen("vcgencmd measure_temp").readline()
        temp = temp.replace("'C", "")
        temp = temp.replace("temp=","")
        self.temp = float(temp)
        if float(temp) >= self.max_temp:
                # print("{} > {} - Heat Alert".format(self.temp, self.max_temp))
                sys.exit()
                
    def reset_values(self):
        # print("reseting values")
        self.count = 0
        self.reset = 0
        
    def listening(self):
        if self.count < self.required:
            pass
            # print(
            #     "cycle:[{}]/{} temp:[{}]/{} detected:[{}]/{})".format(
            #         self.reset, self.cycle, self.temp,
            #         self.max_temp, self.count, self.required)
            #     )
        elif self.count >= self.required:
            self.email()
            # print("Sleeping for {} seconds".format(self.after_alert_sleep_time))
            time.sleep(self.after_alert_sleep_time)
            self.reset_values()
            
    def check_cycle_position(self):
            if self.reset >= self.cycle:
                self.reset_values()
            else:
                self.reset += 1
    
    def startup_check(self):
        self.check_temp()
        print("Time: {}".format(self.datetime_stamp()))
        print("Disk: {}".format(self.disk_space_available()))
        print("Temp: {}".format(self.temp))
        print("RPI: {}".format(cf.rpi))
        print("Variables: {}".format(cf.variables))
        print("Email Settings: {}\n".format(cf.email_settings))
    
    def main(self):
        self.startup_check()
        self.get_network_details()
        self.confirmation_email()
        #GPIO SETUP
        channel = cf.rpi["channel"]
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(channel, GPIO.IN)
        GPIO.add_event_detect(channel, GPIO.BOTH, bouncetime=cf.rpi["bouncetime"])  # let us know when the pin goes HIGH or LOW
        GPIO.add_event_callback(channel, self.callback)  # assign function to GPIO PIN, Run function on change
        while True:
            self.daily_email()
            self.check_temp()
            self.listening()
            time.sleep(self.sample_audio_sleep)
            self.check_cycle_position()
            
AlertSystem().main()
