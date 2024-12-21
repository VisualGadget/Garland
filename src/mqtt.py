import json
import umqtt.simple
import ubinascii
import network
import ustruct as struct
import utime

STATES = ('OFF', 'ON')


class MQTTClientBugFix(umqtt.simple.MQTTClient):

    def __init__(self, client_id, server, user, password):
        super().__init__(client_id, server, user=user, password=password)
        self.socket_blocked_mode = True

    def socket_set_blocked_mode(self, block):
        if self.socket_blocked_mode != block:
            self.sock.setblocking(block)
            self.socket_blocked_mode = block

    # the idea of workaround is to lower blocking/non-blocking switching number
    def wait_msg(self):
        self.socket_set_blocked_mode(False)
        res = self.sock.read(1)
        if res is None:
            return None  # potentially leave socket in non-blocking mode so after wait_msg any other method with read() could fail
        if res == b"":
            raise OSError(-1)

        self.socket_set_blocked_mode(True)

        # following code is unchanged
        if res == b"\xd0":  # PINGRESP
            sz = self.sock.read(1)[0]
            assert sz == 0
            return None
        op = res[0]
        if op & 0xF0 != 0x30:
            return op
        sz = self._recv_len()
        topic_len = self.sock.read(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]
        topic = self.sock.read(topic_len)
        sz -= topic_len + 2
        if op & 6:
            pid = self.sock.read(2)
            pid = pid[0] << 8 | pid[1]
            sz -= 2
        msg = self.sock.read(sz)
        self.cb(topic, msg)
        if op & 6 == 2:
            pkt = bytearray(b"\x40\x02\0\0")
            struct.pack_into("!H", pkt, 2, pid)
            self.sock.write(pkt)
        elif op & 6 == 4:
            assert 0


class HALight:
    '''
    Home Assistant MQTT Light device
    '''
    def __init__(self, server, user, password):
        # chip_id = ubinascii.hexlify(machine.unique_id()).decode()
        mac = ubinascii.hexlify(network.WLAN().config('mac')).decode()
        self.device_id = 'ESP_Garland_' + mac[-4:]
        self._on = False
        topic_base = 'new_year/light/' + self.device_id
        self.config = {
            'name': 'Garland',
            'unique_id': 'Garland_' + mac[-4:],
            'command_topic': topic_base + '/set',
            'state_topic': topic_base + '/state',
            'schema': 'json'
        }
        self._mqtt = MQTTClientBugFix('Garland', server, user=user, password=password)  # umqtt.simple.MQTTClient
        self._mqtt.set_callback(self._inbox)
        self.connect()

    def connect(self):
        self._mqtt.connect()
        self._mqtt.subscribe(self.config['command_topic'])
        # self.mqtt.subscribe(topic_base + '/#')

        ha_discovery_topic = 'homeassistant/light/' + self.device_id + '/config'
        self._mqtt.publish(ha_discovery_topic, json.dumps(self.config))
        self._send_update()

    def check_msg(self):
        # return self._mqtt.wait_msg()
        i = 0
        while True:
            try:
                if i > 0:
                    print(f'Restoring connection. Attempt #{i}')
                    self.connect()
                return self._mqtt.wait_msg()
            except OSError as e:  # ECONNABORTED
                utime.sleep(i)
                i += 1

    def _inbox(self, topic, msg):
        topic = topic.decode()
        if topic == self.config['command_topic']:
            data = json.loads(msg)
            self.on = data['state'] == STATES[True]
            self._send_update()

    def _send_update(self):
        msg = {'state': STATES[self._on]}
        self._mqtt.publish(self.config['state_topic'], json.dumps(msg))

    @property
    def on(self):
        return self._on

    @on.setter
    def on(self, state):
        if state != self._on:
            self._on = state
            self._send_update()
