# Battery ADC Fixed-Window Filter Implementation Plan

## Overview

Smooth Pico battery voltage readings by applying a fixed-window moving average before sending telemetry, reducing dashboard jitter without changing the UART protocol or Pi-side code.

## Current State Analysis

Battery voltage is read directly from the ADC and converted to volts during telemetry send in `robot/Raspberry-Pi-Pico-2/main.py:200`, then passed to `send_telemetry()` unchanged (`robot/Raspberry-Pi-Pico-2/main.py:214`). The voltage scaling uses `VREF` and `DIVIDER_RATIO` from `robot/Raspberry-Pi-Pico-2/config.py:76`. There is no existing battery-specific filter state in the Pico loop.

## Desired End State

Battery voltage telemetry is based on a fixed-window moving average of recent ADC readings, with the window size configured in `config.py`. The telemetry payload format and Pi-side behavior remain unchanged. The dashboard battery reading appears stable over a larger sample window.

### Key Discoveries:
- Telemetry is sent every 100 ms and includes battery voltage as the 5th float (`robot/Raspberry-Pi-Pico-2/main.py:192`, `robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:55`).
- Battery voltage is currently computed from a single ADC sample (`robot/Raspberry-Pi-Pico-2/main.py:200`).
- Battery ADC configuration is defined in `robot/Raspberry-Pi-Pico-2/config.py:76`.

## What We're NOT Doing

- No changes to the telemetry payload format or UART framing.
- No Pi-side changes in the dashboard or UART bridge.
- No changes to ADC hardware configuration or voltage divider parameters.

## Implementation Approach

Introduce a fixed-size moving average buffer on the Pico. Each telemetry cycle, read the ADC, update the running sum, compute the average, and convert to voltage using the existing scaling. Make the window size configurable in `config.py` with a larger default (e.g., 20 samples) to prioritize stability.

## Phase 1: Add Battery ADC Moving Average

### Overview
Add configuration for the averaging window and apply the filter in the telemetry loop.

### Changes Required:

#### 1. Battery Filter Config
**File**: `robot/Raspberry-Pi-Pico-2/config.py`
**Changes**: Add a `BATTERY_AVG_WINDOW` constant with a larger default window (e.g., 20 samples).

```python
BATTERY_AVG_WINDOW = 20  # number of ADC samples to average for battery voltage
```

#### 2. Telemetry Loop Filter State
**File**: `robot/Raspberry-Pi-Pico-2/main.py`
**Changes**: Initialize a fixed-size buffer and running sum for ADC samples. On each telemetry tick, update the buffer, compute the average, and use it for `battery_voltage`.

```python
# Battery ADC filter state
BATTERY_AVG_WINDOW = config.BATTERY_AVG_WINDOW
battery_samples = [0] * BATTERY_AVG_WINDOW
battery_sum = 0
battery_index = 0
battery_count = 0
```

```python
# Battery voltage
adc_val = battery_adc.read_u16()
if battery_count < BATTERY_AVG_WINDOW:
    battery_count += 1
    battery_samples[battery_index] = adc_val
    battery_sum += adc_val
else:
    battery_sum -= battery_samples[battery_index]
    battery_samples[battery_index] = adc_val
    battery_sum += adc_val

battery_index = (battery_index + 1) % BATTERY_AVG_WINDOW
adc_avg = battery_sum / battery_count
battery_voltage = (adc_avg / 65535.0) * config.VREF * (1.0 / config.DIVIDER_RATIO)
```

### Success Criteria:

#### Automated Verification:
- [x] `robot/Raspberry-Pi-Pico-2/config.py` defines `BATTERY_AVG_WINDOW`.
- [x] `robot/Raspberry-Pi-Pico-2/main.py` uses a fixed-window moving average before sending telemetry.

#### Manual Verification:
- [ ] With Pico telemetry running, the battery voltage on the dashboard appears stable with less rapid bouncing than before.
- [ ] Changing `BATTERY_AVG_WINDOW` to a smaller value makes the battery display respond faster, confirming the filter is active.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:
- Not applicable for Pico runtime in this repo.

### Integration Tests:
- Not applicable; telemetry protocol remains unchanged.

### Manual Testing Steps:
1. Deploy updated Pico firmware and open the dashboard battery display.
2. Observe battery voltage stability compared to prior behavior.
3. Adjust `BATTERY_AVG_WINDOW` to a smaller value (e.g., 5) and confirm the display responds more quickly.

## Performance Considerations

The moving average adds small constant memory and arithmetic overhead per telemetry tick (10 Hz), which is acceptable for the Pico loop.

## Migration Notes

None. This change only affects the Pico-side battery telemetry value.

## References

- Original ticket: `.ai/thoughts/tickets/eng-0003.md`
- Pico telemetry loop: `robot/Raspberry-Pi-Pico-2/main.py:192`
- Battery ADC configuration: `robot/Raspberry-Pi-Pico-2/config.py:76`
