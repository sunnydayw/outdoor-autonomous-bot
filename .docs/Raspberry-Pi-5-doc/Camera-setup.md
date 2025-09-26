sudo apt update
sudo apt install -y \
  libcamera-tools libcamera-v4l2 python3-libcamera v4l-utils \
  python3-opencv \
  gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav libcamera-ipa
sudo usermod -aG video $USER
# log out/in or reboot to pick up the group change

- libcamera-tools → gives you the basic CLI tools (like cam, not libcamera-hello)
- libcamera-v4l2 → provides the V4L2 compatibility layer (/dev/video* devices)
- python3-libcamera → Python bindings
- v4l-utils → handy tools (v4l2-ctl) to query devices/formats
- python3-opencv → OpenCV support for capture/processing
- gstreamer1.0-* → if you want to build pipelines/streaming


K210 AI视觉相机在线资料
https://doc.embedfire.com/k210/quick_start/zh/latest/index.html
K210 CanMV开发文档
https://www.kendryte.com/canmv/main/canmv/index.html