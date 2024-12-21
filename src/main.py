'Driver for garland of WS2811'

import utime
import urandom
import machine
import neopixel

import config as cfg
import utils

if cfg.MQTT_ENABLED:
    from mqtt import HALight

ALWAYS_ON = False  # override scheduler for debug purposes

MAX_BRIGHTNESS = 255
MAX_BLINK_SPEED = min(255, cfg.STRING_LENGTH // 10)
MIN_BLINK_SPEED = max(1, cfg.STRING_LENGTH // 100)
STAR_ADD_INTERVAL = max(1, (300 - cfg.STRING_LENGTH) // 4)


class NeoPixel(neopixel.NeoPixel):

    def update(self, index, color, overall_brightness):
        offset = index * self.bpp
        for n in range(3):
            col = color & 0xFF
            color >>= 8
            self.buf[offset + self.ORDER[n]] = int(round(col / 255 * overall_brightness))


class Star:

    class Pattern:
        IDLE = 0
        RAISE = 1
        FADE = 2
        BLINK = 3

    def __init__(self, np, index):
        self.np = np
        self.index = index
        self.pattern = self.Pattern.IDLE
        self.blinkDelta = 0
        self.br = 0  # [0, MAX_BRIGHTNESS]
        self.color = 0  # RGB

    def _update(self):
        overall_brightness = (self.br / MAX_BRIGHTNESS)**2 * MAX_BRIGHTNESS  # self.br
        self.np.update(self.index, self.color, overall_brightness)

    def act(self, pattern, speed):
        self.randomizeColor()
        self.pattern = pattern
        if pattern == self.Pattern.BLINK:
            self.blinkDelta = speed
        self.br = 0
        self._update()

    def tick(self):
        request_update = False
        if self.pattern != self.Pattern.IDLE:
            if self.pattern == self.Pattern.RAISE and self.br < MAX_BRIGHTNESS:
                self.br = min(MAX_BRIGHTNESS, self.br + 1)
                request_update = True
            elif self.pattern == self.Pattern.FADE and self.br > 0:
                self.br = max(0, self.br - 1)
                request_update = True
            elif self.pattern == self.Pattern.BLINK:
                self.br += self.blinkDelta
                if self.br >= MAX_BRIGHTNESS:
                    self.blinkDelta *= -1
                    self.br = min(MAX_BRIGHTNESS, self.br)
                elif self.br <= 0:
                    self.pattern = self.Pattern.IDLE
                    self.br = 0
                request_update = True
        if request_update:
            self._update()
        return request_update

    def randomizeColor(self):
        self.color = 0
        offset = utils.randInt(0, 2) * 8
        self.color |= MAX_BRIGHTNESS << offset
        increment = 8 if urandom.getrandbits(1) else -8
        offset += increment
        self.color |= utils.randInt(0, MAX_BRIGHTNESS) << (offset % 24)
        offset += increment
        self.color |= utils.randInt(0, MAX_BRIGHTNESS / 4) << (offset % 24)


def add_star(stars):
    while True:
        idx = utils.randInt(0, len(stars) - 1)
        star = stars[idx]
        if star.pattern == Star.Pattern.IDLE:
            break
    speed = utils.randInt(MIN_BLINK_SPEED, MAX_BLINK_SPEED)
    star.act(Star.Pattern.BLINK, speed)


def main():
    print('start')
    machine.freq(160000000)

    pin = machine.Pin(cfg.PIN_DO, machine.Pin.OUT)
    np = NeoPixel(pin, cfg.STRING_LENGTH)
    np.ORDER = (0, 1, 2, 3)
    np.write()  # turn off all leds

    if cfg.MQTT_ENABLED:
        hal = HALight(cfg.MQTT_SERVER, cfg.MQTT_USER, cfg.MQTT_PASSWORD)

    stars = [Star(np, i) for i in range(cfg.STRING_LENGTH)]
    working_now = False
    prev_hour = None
    tick = 0

    while True:
        # scheduler
        hour = utime.localtime()[3]
        if hour != prev_hour:
            if hour == 12 or prev_hour is None:
                utils.sync_time()
            prev_hour = hour

        working_now = ALWAYS_ON or (7 <= hour < 9 or hour >= 16 or 0 <= hour < 1)
        if cfg.MQTT_ENABLED:
            hal.on = working_now

        if working_now and not tick % STAR_ADD_INTERVAL:
            add_star(stars)

        update_request = False
        for star in stars:
            if star.tick():
                update_request = True

        if working_now or update_request:
            np.write()
            if not tick % 100:
                print('wrk', tick // 100)
        else:
            utils.sleep_s(1)  # IDLE
            print('idle')

        if cfg.MQTT_ENABLED:
            hal.check_msg()

        utils.watchdog.feed()
        tick += 1


try:
    main()
except Exception:
    print('Exception! Restarting...')
    machine.reset()