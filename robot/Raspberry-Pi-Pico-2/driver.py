# driver.py
from machine import Pin, PWM

class HBridgeChannel:
    """
    Low‐level control of one TB6612 channel (A or B).
    """
    def __init__(self, in1_pin, in2_pin, pwm_pin, freq=10000):
        self.in1 = Pin(in1_pin, Pin.OUT)
        self.in2 = Pin(in2_pin, Pin.OUT)
        self.pwm = PWM(Pin(pwm_pin))
        self.pwm.freq(freq)
        self.pwm.duty_u16(0)

    def apply_direction(self, rpm: float, invert: bool = False):
        dir_flag = 1 if rpm >= 0 else -1
        if invert:
            dir_flag *= -1

        if dir_flag >= 0:
            self.in1.value(1)
            self.in2.value(0)
        else:
            self.in1.value(0)
            self.in2.value(1)

    def set_duty(self, duty: int):
        duty = max(0, min(duty, 65535))
        self.pwm.duty_u16(duty)

    def brake(self):
        # fast‐brake: both high, PWM off
        self.pwm.duty_u16(0)
        self.in1.value(1)
        self.in2.value(1)


class TB6612Driver:
    """
    Wraps two HBridgeChannel instances (A & B) plus STBY pin.
    """
    def __init__(
        self,
        in1_a, in2_a, pwm_a,
        in1_b, in2_b, pwm_b,
        standby_pin,
        freq=10000
    ):
        # enable pin
        self.stby = Pin(standby_pin, Pin.OUT)
        self.stby.value(1)

        self.channel_a = HBridgeChannel(in1_a, in2_a, pwm_a, freq)
        self.channel_b = HBridgeChannel(in1_b, in2_b, pwm_b, freq)

    def enable(self):
        self.stby.value(1)

    def disable(self):
        self.channel_a.brake()
        self.channel_b.brake()
        self.stby.value(0)

    def apply_direction(self, channel: str, rpm: float, invert: bool = False):
        """
        channel: 'A' or 'B'
        """
        if channel.upper() == 'A':
            self.channel_a.apply_direction(rpm, invert)
        else:
            self.channel_b.apply_direction(rpm, invert)

    def set_duty(self, channel: str, duty: int):
        if channel.upper() == 'A':
            self.channel_a.set_duty(duty)
        else:
            self.channel_b.set_duty(duty)

    def brake(self, channel: str = None):
        """
        If channel is None → brake both; else only that channel.
        """
        if channel is None or channel.upper() == 'A':
            self.channel_a.brake()
        if channel is None or channel.upper() == 'B':
            self.channel_b.brake()
