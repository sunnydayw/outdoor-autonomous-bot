current pico only listen to the command sending form pi 5, now lets add information and sending back to the pi. edit robot/Raspberry-Pi-Pico-2/pico_uart_comm.py to add the following information sending to the pi
- left and right wheel target and actual RPM
- Battery level, battery level is readable on ADC2 (GP28)(config.py had the pin define), it is read from a 1:11 divider
- IMU information, in main.py imu is already setup.

ensure update robot/Raspberry-Pi-Pico-2/main.py code for the updated communication 

also create a communcation spec in the same level folder to doucment the communcaiton, so that I can use it to update the receiving end on the pi side later