#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

__author__ = "Steve Miller"
__copyright__ = "Copyright (C) Steve Miller"

__credits__ = ["Mike Loebl - https://github.com/mloebl/mqtt-aprs"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Steve Miller"
__email__ = "smiller _at_ kc1awv _dot_ net"
__status__ = "Development"

# Script based on mqtt-owfs-temp written by Kyle Gordon and converted for use with APRS
# Source: https://github.com/kylegordon/mqtt-owfs-temp
# Additional Python 3 development and conversions of Mike Loebl's code by Steve Miller, KC1AWV
# Source: https://github.com/mloebl/mqtt-aprs
# APRS is a registered trademark Bob Bruninga, WB4APR

import os
import sys
import logging
import signal
import socket
import time

import paho.mqtt.client as paho
import configparser

import setproctitle

import aprslib

from datetime import datetime, timedelta

# Read the config file
config = configparser.RawConfigParser()
config.read("/etc/mqtt-aprs/mqtt-aprs.cfg")

# Use configparser to read the settings
DEBUG = config.getboolean("global", "debug")
LOGFILE = config.get("global", "logfile")
MQTT_HOST = config.get("global", "mqtt_host")
MQTT_PORT = config.getint("global", "mqtt_port")
MQTT_TLS = config.getint("global", "mqtt_tls")
MQTT_SUBTOPIC = config.get("global", "mqtt_subtopic")
MQTT_TOPIC = "/raw/" + socket.getfqdn() + "/" + MQTT_SUBTOPIC
MQTT_USERNAME = config.get("global", "mqtt_username")
MQTT_PASSWORD = config.get("global", "mqtt_password")
METRICUNITS = config.get("global", "metricunits")

APRS_CALLSIGN = config.get("global", "aprs_callsign")
APRS_PASSWORD = config.get("global", "aprs_password")
APRS_HOST = config.get("global", "aprs_host")
APRS_PORT = config.get("global", "aprs_port")
APRS_FILTER = config.get("global", "aprs_filter")
APRS_PROCESS = config.get("global", "aprs_process")

APRS_LATITUDE = config.get("global", "aprs_latitude")
APRS_LONGITUDE = config.get("global", "aprs_longitude")

APPNAME = MQTT_SUBTOPIC
PRESENCETOPIC = "clients/" + socket.getfqdn() + "/" + APPNAME +"/state"
setproctitle.setproctitle(APPNAME)
client_id = APPNAME + "_%d" % os.getpid()

mqttc = paho.Client()

LOGFORMAT = '%(asctime)-15s %(message)s'

if DEBUG:
    logging.basicConfig(filename=LOGFILE,
                        level=logging.DEBUG,
                        format=LOGFORMAT)
else:
    logging.basicConfig(filename=LOGFILE,
                        level=logging.INFO,
                        format=LOGFORMAT)

logging.info("Starting " + APPNAME)
logging.info("INFO MODE")
logging.debug("DEBUG MODE")

def celciusConv(fahrenheit):
    return (fahrenheit - 32) * (5/9)
def fahrenheitConv(celsius):
    return ((celsius(9/5)) + 32)

# MQTT Callbacks

def on_publish(mosq, obj, mid):
    logging.debug("MID" + str(mid) + " published.")
    
def on_subscribe(mosq, obj, mid, qos_list):
    logging.debug("Subscribe with mid " + str(mid) + " received.")

def on_unsubscribe(mosq, obj, mid):
    logging.debug("Unsubscribe with mid " + str(mid) + " received.")

def on_connect(self, mosq, obj, result_code):
    logging.debug("on_connect RC: " + str(result_code))
    if result_code == 0:
        logging.info("Connected to %s:%s", MQTT_HOST, MQTT_PORT)
        mqttc.publish(PRESENCETOPIC, "1", retain=True)
        process_connection()
    elif result_code == 1:
        logging.info("Connection refused - unacceptable protocol version")
        cleanup()
    elif result_code == 2:
        logging.info("Connection refused - identifier rejected")
        cleanup()
    elif result_code == 3:
        logging.info("Connection refused - server unavailable")
        logging.info("Retrying in 30 seconds")
        time.sleep(30)
    elif result_code == 4:
        logging.info("Connection refused - bad username or password")
        cleanup()
    elif result_code == 5:
        logging.info("Connection refused - not authorized")
        cleanup()
    else:
        logging.warning("Someting went wrong. RC:" + str(result_code))
        cleanup()

def on_disconnect(mosq, obj, result_code):
    if result_code == 0:
        logging.info("Clean disconnect")
    else:
        logging.info("Unexpected disconnection! Reconnecting in 5 seconds")
        logging.debug("Result code: " + str(result_code))
        time.sleep(5)
    
def on_message(mosq, obj, msg):
    logging.debug("Received: " + msg.payload +
                  " received on topic " + msg.topic +
                  " with QoS " + str(msg.qos))
    process_message(msg)

def on_log(mosq, obj, level, string):
    logging.debug(string)

def cleanup(signum, frame):
    logging.info("Disconnecting from broker")
    mqttc.publish(PRESENCETOPIC, "0", retain=True)
    mqttc.disconnect()
    mqttc.loop_stop()
    logging.info("Exiting on signal %d", signum)
    sys.exit(signum)

def connect():
    logging.info("Connecting to %s:%s", MQTT_HOST, MQTT_PORT)
    if MQTT_USERNAME:
        logging.info("Found username %s", MQTT_USERNAME)
        mqttc.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if MQTT_TLS == 1:
        logging.info("Using TLS for broker connection")
        mqttc.tls_set()
    mqttc.will_set(PRESENCETOPIC, "0", qos=0, retain=True)
    result = mqttc.connect(MQTT_HOST, MQTT_PORT, 10)
    if result != 0:
        logging.info("Connection failed with error code %s. Retrying", result)
        time.sleep(10)
        connect()
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    mqttc.on_publish = on_publish
    mqttc.on_subscribe = on_subscribe
    mqttc.on_unsubscribe = on_unsubscribe
    mqttc.on_message = on_message
    if DEBUG:
        mqttc.on_log = on_log
    mqttc.loop_start()

def process_connection():
    logging.debug("Processing connection")

def process_message(mosq, obj, msg):
    logging.debug("Received: %s", msg.topic)

def find_in_sublists(lst, value):
    for sub_i, sublist in enumerate(lst):
        try:
            return (sub_i, sublist.index(value))
        except ValueError:
            pass
    raise ValueError("%s is not in lists" % value)

def callback(packet):
    logging.debug("Raw packet: %s", packet)
    if APRS_PROCESS == "True":
        aprspacket = aprs._parse(packet)
        
        ssid = aprspacket.get('from', 'None')
        logging.debug("SSID: %s", ssid)
        
        rawpacket = aprspacket.get('raw', None)
        logging.debug("RAW: %s", rawpacket)
        publish_aprstomqtt_ssid(ssid, "raw", rawpacket)

        if 'weather' in aprspacket:
            logging.debug("incoming wx packet from: %s", ssid)
            wx_lat = aprspacket.get('latitude', 0)
            wx_lon = aprspacket.get('longitude', 0)
            wx_hum = aprspacket.get('weather', {}).get('humidity', 0)
            wx_pres = aprspacket.get('weather', {}).get('pressure', 0)
            wx_rain_1h = aprspacket.get('weather', {}).get('rain_1h', 0)
            wx_rain_24h = aprspacket.get('weather', {}).get('rain_24h', 0)
            wx_temp = aprspacket.get('weather', {}).get('temperature', 0)
            wx_wind_d = aprspacket.get('weather', {}).get('wind_direction', 0)
            wx_wind_g = aprspacket.get('weather', {}).get('wind_gust', 0)
            wx_wind_s = aprspacket.get('weather', {}).get('wind_speed', 0)
            wx_report = "{ \"ssid\": \"" + str(ssid) + "\", " \
                          "\"lat\": " + str(wx_lat) + ", " \
                          "\"lon\": " + str(wx_lon) + ", " \
                          "\"humidity\": " + str(wx_hum) + ", " \
                          "\"pressure\": " + str(wx_pres) + ", " \
                          "\"rain_1h\": " + str(wx_rain_1h) + ", " \
                          "\"rain_24h\": " + str(wx_rain_24h) + ", " \
                          "\"temperature\": " + str(wx_temp) + ", " \
                          "\"wind_direction\": " + str(wx_wind_d) + ", " \
                          "\"wind_gust\": " + str(wx_wind_g) + ", " \
                          "\"wind_speed\": " + str(wx_wind_s) + " }"
            logging.debug("weather: %s", wx_report)
            publish_aprstomqtt("weather", wx_report)
        else:
            packet_format = aprspacket.get('format', None)
            if packet_format == 'uncompressed':
                logging.debug("incoming uncompressed packet from: %s", ssid)
                aprs_lat = aprspacket.get('latitude', 0)
                aprs_lon = aprspacket.get('longitude', 0)
                aprs_course = aprspacket.get('course', 0)
                aprs_speed = aprspacket.get('speed', 0)
                aprs_comment = aprspacket.get('comment', 0)
                aprs_pos = "{ \"ssid\": \"" + str(ssid) + "\", " \
                             "\"comment\": \"" + str(aprs_comment) + "\", " \
                             "\"lat\": " + str(aprs_lat) + ", " \
                             "\"lon\": " + str(aprs_lon) + ", " \
                             "\"course\": " + str(aprs_course) + ", " \
                             "\"speed\": " + str(aprs_speed) + " }"
                logging.debug("position: %s", aprs_pos)
                publish_aprstomqtt("position", aprs_pos)
            elif packet_format == 'compressed':
                logging.debug("incoming compressed packet from: %s", ssid)
                aprs_lat = aprspacket.get('latitude', 0)
                aprs_lon = aprspacket.get('longitude', 0)
                aprs_course = aprspacket.get('course', 0)
                aprs_speed = aprspacket.get('speed', 0)
                aprs_comment = aprspacket.get('comment', 0)
                aprs_pos = "{ \"ssid\": \"" + str(ssid) + "\", " \
                             "\"comment\": \"" + str(aprs_comment) + "\", " \
                             "\"lat\": " + str(aprs_lat) + ", " \
                             "\"lon\": " + str(aprs_lon) + ", " \
                             "\"course\": " + str(aprs_course) + ", " \
                             "\"speed\": " + str(aprs_speed) + " }"
                logging.debug("position: %s", aprs_pos)
                publish_aprstomqtt("position", aprs_pos)
            elif packet_format == 'mic-e':
                logging.debug("incoming mic-e packet from: %s", ssid)
                aprs_lat = aprspacket.get('latitude', 0)
                aprs_lon = aprspacket.get('longitude', 0)
                aprs_course = aprspacket.get('course', 0)
                aprs_speed = aprspacket.get('speed', 0)
                aprs_comment = aprspacket.get('comment', 0)
                aprs_pos = "{ \"ssid\": \"" + str(ssid) + "\", " \
                             "\"comment\": \"" + str(aprs_comment) + "\", " \
                             "\"lat\": " + str(aprs_lat) + ", " \
                             "\"lon\": " + str(aprs_lon) + ", " \
                             "\"course\": " + str(aprs_course) + ", " \
                             "\"speed\": " + str(aprs_speed) + " }"
                logging.debug("position: %s", aprs_pos)
                publish_aprstomqtt("position", aprs_pos)
            elif packet_format == 'object':
                logging.debug("incoming object packet from: %s", ssid)
                aprs_lat = aprspacket.get('latitude', 0)
                aprs_lon = aprspacket.get('longitude', 0)
                aprs_course = aprspacket.get('course', 0)
                aprs_speed = aprspacket.get('speed', 0)
                aprs_comment = aprspacket.get('comment', 0)
                aprs_pos = "{ \"ssid\": \"" + str(ssid) + "\", " \
                             "\"comment\": \"" + str(aprs_comment) + "\", " \
                             "\"lat\": " + str(aprs_lat) + ", " \
                             "\"lon\": " + str(aprs_lon) + ", " \
                             "\"course\": " + str(aprs_course) + ", " \
                             "\"speed\": " + str(aprs_speed) + " }"
                logging.debug("object: %s", aprs_pos)
                publish_aprstomqtt("object", aprs_pos)
            elif packet_format == 'message':
                logging.debug("incoming message from: %s", ssid)
                aprs_text = aprspacket.get('message_text', None)
                aprs_message = "{ \"ssid\": \"" + str(ssid) + "\", " \
                                 "\"message\": \"" + str(aprs_text) + "\" }"
                publish_aprstomqtt("message", aprs_message)
    else:
        publish_aprstomqtt_nossid(packet)

def publish_aprstomqtt(inname, invalue):
    topic_path = MQTT_TOPIC + "/" + inname
    logging.debug("Publishing topic: %s with value %s" % (topic_path, invalue))
    mqttc.publish(topic_path, str(invalue).encode('utf-8').strip())

def publish_aprstomqtt_ssid(inssid, inname, invalue):
    topic_path = MQTT_TOPIC + "/" + inssid + "/" + inname
    logging.debug("Publishing topic: %s with value %s" % (topic_path, invalue))
    mqttc.publish(topic_path, str(invalue).encode('utf-8').strip())

def publish_aprstomqtt_nossid(invalue):
    topic_path = MQTT_TOPIC
    logging.debug("Publishing topic: %s with value %s" % (topic_path, invalue))
    mqttc.publish(topic_path, str(invalue).encode('utf-8').strip())

def get_distance(inlat, inlon):
    if APRS_LATITUDE and APRS_LONGITUDE:
        R = 6373.0
        from math import sin, cos, sqrt, atan2, radians
        lat1 = radians(float(APRS_LATITUDE))
        lon1 = radians(float(APRS_LONGITUDE))
        lat2 = radians(float(inlat))
        lon2 = radians(float(inlon))
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c
        if METRICUNITS == "0":
            distance = distance * 0.621371
        return round(distance, 2)

def aprs_connect():
    aprs.set_filter(APRS_FILTER)
    aprs.connect(blocking=True)
    logging.debug("APRS Processing: %s", APRS_PROCESS)
    if APRS_PROCESS == "True":
        aprs.consumer(callback, raw=True)
    else:
        aprs.consumer(callback)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)
try:
    aprs = aprslib.IS(APRS_CALLSIGN,
                      passwd=APRS_PASSWORD,
                      host=APRS_HOST,
                      port=APRS_PORT,
                      skip_login=False)
    connect()
    aprs_connect()

except KeyboardInterrupt:
    logging.info("Interrupted by keypress")
    sys.exit(0)
except aprslib.ConnectionDrop:
    logging.info("Connection to APRS server dropped, trying again in 30 seconds...")
    time.sleep(30)
    aprs_connect
except aprslib.ConnectionError:
    logging.info("Connection to APRS server failed, trying again in 30 seconds...")
    time.sleep(30)
    aprs_connect