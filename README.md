# mqtt-aprs

## This is a fork of Mike Loebl's code found at https://github.com/mloebl/mqtt-aprs

Connects to the specified APRS-IS server, and posts the APRS output to MQTT.  Can parse parameters, or dump the raw JSON from aprslib.  It's currently for receive only from APRS-IS and sending to an MQTT server.

This script uses 
- `aprslib`, https://github.com/rossengeorgiev/aprs-python, to do the heavy APRS lifting
- `paho-mqtt`, https://www.eclipse.org/paho/index.php?page=clients/python/index.php for handling MQTT connect and pub / sub

### PREREQUISITES

- aprslib (pip3 install aprslib)
- paho-mqtt (pip3 install paho-mqtt)

### USE


```bash
git clone https://github.com/kc1awv/mqtt-aprs.git

cd mqtt-aprs

sudo cp mqtt-aprs.cfg.example /etc/mqtt-aprs/mqtt-aprs.cfg
```

**Important:** Edit /etc/mqtt-aprs/mqtt-aprs.cfg to suit

Then, simply `python3 mqtt-aprs.py` and use an MQTT client to subscribe to the topics!

### AVAILABLE TOPICS BY DEFAULT

`/raw/(HOSTNAME)/ssid/raw`

Example: `VE2TFZ-D>APDG03,TCPIP*,qAC,VE2TFZ-DS:!4522.92ND07329.55W&/A=000000440 MMDVM Voice 438.80000MHz +0.0000MHz, APRS for DMRGateway`

`/raw/(HOSTNAME)/aprs/position`

Example:
```
{ "ssid": "W2TKR-9", 
  "comment": "Mobile", 
  "lat": 41.8575, 
  "lon": -69.9875, 
  "course": 193, 
  "speed": 55.56 }
```

`/raw/(HOSTNAME)/aprs/weather`

Example: 
```
{ "ssid": "T10BNorth", 
  "lat": 43.83833333333333, 
  "lon": -71.7035, 
  "humidity": 86, 
  "pressure": 1005.2, 
  "rain_1h": 0.0, 
  "rain_24h": 8.128, 
  "temperature": 20.555555555555554, 
  "wind_direction": 0, 
  "wind_gust": 0.0, 
  "wind_speed": 0 }
```

`/raw/(HOSTNAME)/aprs/message`

Example: 
```
{ "ssid": "N2MH-15", 
  "message": "220000z,Heat,NJC013-CTZ005>012-NJZ002-004-006-103>106-NYZ067>071" }
```

### WHY

Uh, why not? It's fun, and you could even do things like this:
![node-red worldmap](mqtt-aprs.png)

APRS is a registered trademark Bob Bruninga, WB4APR

Originally forked by Mike Loebl from original https://github.com/kylegordon/mqtt-owfs-temp, and customised for use with APRS

[mqtt-aprs](https://github.com/mloebl/mqtt-aprs) forked, modified and tested against Python 3 by Steve Miller
