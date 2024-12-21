# Garland of WS2811 controlled by ESP8266

## Setup environment
```
sudo usermod -a -G dialout $USER
sudo reboot
```
From project root:
```
python3 -m venv venv
source venv/bin/activate
pip install -r ./requirements.txt
```

## Flash MCU
1. Connect Wemos D1 mini board to PC using USB cable.
2. Upload uPython firmware. See `./ext/uPython_start/readme.md`.
3. Edit `./src/config_example.py` and save it as `config.py`.
4. Run `udevadm info --name /dev/ttyUSB*` to get serial port path. Verify it in the shebang of the `upload-src.sh` script.
5. Run `upload-src.sh` to upload project code to MCU.
