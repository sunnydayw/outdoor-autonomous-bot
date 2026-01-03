.ai/commands/research_codebase.md

I want you to research about the communication spec between pi and pico. I want you to document the current code structure, high level architure to help me update and improve the code. I also want a detailed docucmentation use as the spec for communication.
in the folder pi3-rover-1, we have code for sending drive command to the pico and receiving telemerty information from the pico
the file robot/Raspberry-Pi-Pico-2/pico_uart_comm.py lays out for how pico sending and receiving data from pi over uart
there is a draft document of robot/Raspberry-Pi-Pico-2/communication_spec.md, but the information accuarcy need to be verify.