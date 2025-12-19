#!/usr/bin/env python3
"""
Simple FrSky XSR-SIM mapping viewer for macOS using pygame.

- Reads the first joystick detected (your XSR-SIM).
- Shows all axes as CH1, CH2, ... with values in [-1.00, 1.00].
- Shows all buttons as SW1, SW2, ... with 0/1 state.

Usage:
    python3 xsr_simple_diag_mac.py
"""

import time
import sys

import pygame


def clear_screen():
    # ANSI clear + home cursor (works in Terminal / iTerm)
    print("\x1b[2J\x1b[H", end="")


def main():
    # Initialize pygame and joystick subsystem
    pygame.init()
    pygame.joystick.init()

    joystick_count = pygame.joystick.get_count()
    if joystick_count == 0:
        print("No joystick detected.")
        print("Make sure the FrSky XSR-SIM dongle is plugged in,")
        print("then run this script again.")
        sys.exit(1)

    # For now, just use the first joystick
    js = pygame.joystick.Joystick(0)
    js.init()

    name = js.get_name()
    num_axes = js.get_numaxes()
    num_buttons = js.get_numbuttons()

    print(f"Using joystick: {name}")
    print(f"Axes   : {num_axes}")
    print(f"Buttons: {num_buttons}")
    print("Reading input... Press Ctrl+C to exit.")
    time.sleep(1.0)

    try:
        while True:
            # Pump event queue so pygame updates joystick state
            pygame.event.pump()

            # Read all axes
            axes = [js.get_axis(i) for i in range(num_axes)]
            # Read all buttons
            buttons = [js.get_button(i) for i in range(num_buttons)]

            # Render
            clear_screen()
            print("=== FrSky XSR-SIM Mapping Viewer (macOS/pygame) ===")
            print(f"Joystick: {name}")
            print(f"Axes   : {num_axes}")
            print(f"Buttons: {num_buttons}")
            print()
            print("Move ONE control at a time and see which CH / SW changes.")
            print("Use this to map sticks/switches to channels.")
            print()

            if num_axes > 0:
                print("Analog Channels (sticks / pots):")
                print("  {:<4} {:>8}".format("CH", "value"))
                print("  " + "-" * 20)
                for i, val in enumerate(axes):
                    ch_name = f"CH{i + 1}"
                    # val is already approx in [-1.0, 1.0]
                    print("  {:<4} {:>8.2f}".format(ch_name, val))
            else:
                print("No axes reported.")
            print()

            if num_buttons > 0:
                print("Buttons / Switches:")
                print("  {:<4} {:>6}".format("SW", "state"))
                print("  " + "-" * 16)
                for i, state in enumerate(buttons):
                    sw_name = f"SW{i + 1}"
                    print("  {:<4} {:>6}".format(sw_name, state))
            else:
                print("No buttons reported.")

            print()
            print("Press Ctrl+C to quit.")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        js.quit()
        pygame.joystick.quit()
        pygame.quit()


if __name__ == "__main__":
    main()
