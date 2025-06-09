import time

class sensor:
    def __init__(self, pi, gpio):
        self.pi = pi
        self.gpio = gpio

        self._new_data = False
        self._temperature = 0.0
        self._humidity = 0.0

        self._cb = self.pi.callback(self.gpio, pigpio.EITHER_EDGE, self._cbf)

        self._high_tick = 0
        self._bits = []
        self._timeout = 0.2  # 초 단위

    def _cbf(self, gpio, level, tick):
        diff = pigpio.tickDiff(self._high_tick, tick)
        if level == 1:
            self._high_tick = tick
        elif level == 0:
            if diff > 10:  # noise 제거용
                self._bits.append(diff)

    def trigger(self):
        self._bits = []
        self.pi.set_mode(self.gpio, pigpio.OUTPUT)
        self.pi.write(self.gpio, 0)
        time.sleep(0.018)
        self.pi.write(self.gpio, 1)
        self.pi.set_mode(self.gpio, pigpio.INPUT)

        start = time.time()
        while len(self._bits) < 40 and (time.time() - start) < self._timeout:
            time.sleep(0.001)

        if len(self._bits) < 40:
            raise RuntimeError("DHT22 데이터 수신 실패")

        # 비트 파싱
        bits = []
        for b in self._bits[:40]:
            bits.append(1 if b > 50 else 0)

        # 바이트로 변환
        bytes_ = []
        for i in range(5):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | bits[i * 8 + j]
            bytes_.append(byte)

        checksum = (bytes_[0] + bytes_[1] + bytes_[2] + bytes_[3]) & 0xFF
        if bytes_[4] != checksum:
            raise RuntimeError("DHT22 체크섬 오류")

        self._humidity = ((bytes_[0] << 8) + bytes_[1]) * 0.1
        t_raw = ((bytes_[2] & 0x7F) << 8) + bytes_[3]
        self._temperature = t_raw * 0.1
        if bytes_[2] & 0x80:
            self._temperature = -self._temperature

        self._new_data = True

    def temperature(self):
        return self._temperature

    def humidity(self):
        return self._humidity

    def cancel(self):
        if self._cb is not None:
            self._cb.cancel()
            self._cb = None
