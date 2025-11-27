# driver.py
from machine import Pin, PWM


class HBridgeChannel:
    """
    Low-level control of one TB6612 channel (A or B).

    Typical usage:
        - call apply_direction(rpm, invert=...) to set motor direction
          (only the sign of rpm is used here).
        - call set_duty(duty) with a 0..65535 value to set speed.
        - call brake() to stop the motor (implemented as COAST here).
    """

    def __init__(self, in1_pin, in2_pin, pwm_pin, freq: int = 10_000):
        """
        :param in1_pin: GPIO number for IN1.
        :param in2_pin: GPIO number for IN2.
        :param pwm_pin: GPIO number for PWM (PWMA / PWMB).
        :param freq:    PWM frequency in Hz (default 10 kHz).
        """
        self.in1 = Pin(in1_pin, Pin.OUT)
        self.in2 = Pin(in2_pin, Pin.OUT)

        self.pwm = PWM(Pin(pwm_pin))
        self.pwm.freq(freq)
        self.pwm.duty_u16(0)

        # Optional: track last command for debugging / telemetry
        self._last_dir = 0   # +1 forward, -1 reverse, 0 stopped
        self._last_duty = 0  # 0..65535

    def apply_direction(self, rpm: float, invert: bool = False) -> None:
        """
        Set H-bridge direction based on sign of rpm.

        :param rpm:    Signed value; only the sign is used.
        :param invert: If True, logical direction is flipped
                       (helps compensate wiring differences).
        """
        dir_flag = 1 if rpm >= 0 else -1
        if invert:
            dir_flag *= -1

        if dir_flag >= 0:
            self.in1.value(1)
            self.in2.value(0)
        else:
            self.in1.value(0)
            self.in2.value(1)

        self._last_dir = dir_flag

    def set_duty(self, duty: int) -> None:
        """
        Set PWM duty (speed), clamped to the valid 16-bit range.

        :param duty: 0..65535 (0 = off, 65535 = full on).
        """
        duty = max(0, min(duty, 65535))
        self._last_duty = duty
        self.pwm.duty_u16(duty)

    def brake(self) -> None:
        """
        Stop the motor.

        NOTE:
            This implementation COASTS the motor:
            - PWM is set to 0 (EN low → outputs Hi-Z).
            - IN1/IN2 are both high, the H-bridge is off.

        If you want true active braking with TB6612:
            - set duty to 65535
            - set IN1 and IN2 to the same level (both 0 or both 1).
        """
        self.pwm.duty_u16(0)  # EN low → outputs Hi-Z (coast)
        self.in1.value(1)
        self.in2.value(1)
        self._last_duty = 0
        self._last_dir = 0


class TB6612Driver:
    """
    Driver for one TB6612FNG chip: two channels (A & B) plus STBY pin.
    """

    def __init__(
        self,
        in1_a, in2_a, pwm_a,
        in1_b, in2_b, pwm_b,
        standby_pin,
        freq: int = 10_000
    ):
        """
        :param in1_a, in2_a, pwm_a: GPIOs for channel A (IN1, IN2, PWM).
        :param in1_b, in2_b, pwm_b: GPIOs for channel B (IN1, IN2, PWM).
        :param standby_pin:        GPIO for STBY (chip enable, active-high).
        :param freq:               PWM frequency in Hz (for both channels).
        """
        # STBY high → chip enabled
        self.stby = Pin(standby_pin, Pin.OUT)
        self.stby.value(1)

        self.channel_a = HBridgeChannel(in1_a, in2_a, pwm_a, freq)
        self.channel_b = HBridgeChannel(in1_b, in2_b, pwm_b, freq)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_channel(self, channel: str) -> HBridgeChannel:
        """
        Return the HBridgeChannel for 'A' or 'B'.

        Raises:
            ValueError if channel is not 'A' or 'B'.
        """
        if not isinstance(channel, str):
            raise ValueError("channel must be a string 'A' or 'B'")

        ch = channel.upper()
        if ch == 'A':
            return self.channel_a
        if ch == 'B':
            return self.channel_b

        raise ValueError("channel must be 'A' or 'B' (got %r)" % channel)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enable(self) -> None:
        """Bring STBY high to enable the driver outputs."""
        self.stby.value(1)

    def disable(self) -> None:
        """
        Disable driver outputs.

        - Both channels are commanded to coast.
        - STBY is driven low so the TB6612 outputs go Hi-Z.
        """
        self.brake()     # coast both channels
        self.stby.value(0)

    def apply_direction(self, channel: str, rpm: float, invert: bool = False) -> None:
        """
        Set direction for the given channel based on sign of rpm.
        """
        h = self._get_channel(channel)
        h.apply_direction(rpm, invert)

    def set_duty(self, channel: str, duty: int) -> None:
        """
        Set PWM duty (0..65535) for the given channel.
        """
        h = self._get_channel(channel)
        h.set_duty(duty)

    def drive(self, channel: str, command: float, invert: bool = False) -> None:
        """
        Convenience method: drive a channel with a signed command.

        :param channel: 'A' or 'B'.
        :param command: in range [-1.0, 1.0]; sign = direction,
                        magnitude = speed (scaled to 0..65535).
        :param invert:  If True, flips logical direction.
        """
        # Clamp command
        if command > 1.0:
            command = 1.0
        elif command < -1.0:
            command = -1.0

        h = self._get_channel(channel)

        # Direction from sign
        h.apply_direction(command, invert)

        # Duty from magnitude
        duty = int(abs(command) * 65535)
        h.set_duty(duty)

    def brake(self, channel: str = None) -> None:
        """
        Stop the motor(s) by commanding them to coast.

        :param channel:
            - None → brake both channels.
            - 'A'   → brake only channel A.
            - 'B'   → brake only channel B.
        """
        if channel is None:
            self.channel_a.brake()
            self.channel_b.brake()
            return

        h = self._get_channel(channel)
        h.brake()
