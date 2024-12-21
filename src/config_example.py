# Edit configuration and rename this file to config.py

# Wi-Fi
WIFI_SSID = 'wifi name'
WIFI_PASSWORD = 'wifi password'

# Garland
STRING_LENGTH = 50 * 2  # number of leds in garland string

# Clock
NTP_SERVER = '3.ru.pool.ntp.org'
TIMEZONE = 5  # GMT+TIMEZONE

# Scheduler
ALWAYS_ON = False  # scheduler override
# intervals in 24h format (start_hour, stop_hour)
WORKING_HOURS = [(0, 1), (7, 9), (16, 24)]  # 7:00-9:00, 16:00-1:00
# WORKING_HOURS = [(9, 18)]  # 9:00-18:00

# Hardware
PIN_DO = 2  # WS2811 signal pin
WDT_ENABLE = True

# MQTT
MQTT_ENABLED = False
MQTT_SERVER = '192.168.1.3'
MQTT_USER = 'mqtt user'
MQTT_PASSWORD = 'mqtt password'
