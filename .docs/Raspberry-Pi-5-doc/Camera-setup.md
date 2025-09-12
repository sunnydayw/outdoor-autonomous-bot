sudo apt update
sudo apt install -y \
  libcamera-tools libcamera-v4l2 python3-libcamera v4l-utils \
  python3-opencv \
  gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav
sudo usermod -aG video $USER
# log out/in or reboot to pick up the group change


K210 AI视觉相机在线资料
https://doc.embedfire.com/k210/quick_start/zh/latest/index.html
K210 CanMV开发文档
https://www.kendryte.com/canmv/main/canmv/index.html