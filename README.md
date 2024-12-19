# Outdoor Autonomous Bot

This project is a differential drive robot platform designed for autonomous outdoor navigation. It started as a lawn mowing idea but has expanded to include street cleaning, trash collection, and park maintenance, all with the goal of creating cleaner, greener spaces.

## Motivation

I’ve always loved robotics and the idea of using technology to free people from repetitive chores like mowing lawns. After moving back to NYC, I was disappointed by the amount of trash on the streets and in parks, especially during my runs. Seeing litter and debris overshadow the beauty of nature and public spaces made me realize how much a clean environment can affect our mental health.

While the ultimate solution is to encourage people not to litter in the first place, I wanted to start with something I could control. This robot is my way of making an impact—helping park rangers and others keep our shared spaces clean and enjoyable for everyone.

## Roadmap

1. **Build a Mobile Robot Base**
    - Select key components such as the compute unit, motors, battery, and controller.
    - Design and assemble a differential drive platform for basic mobility.
    - Test basic movement and control to ensure the robot can move reliably.
    - Optimize PID control loops for precise movement and turning.

2. **Solve Navigation Challenges**
    - Design and implement path planning and localization (e.g., LIDAR, GPS, or camera-based SLAM).
    - Test autonomous navigation in outdoor environments, addressing challenges like terrain variability and GPS signal loss.

3. **Integrate Lawn Mowing Design**
    - Design and build a robust lawn mowing mechanism.
    - Fine-tune path planning for lawn mowing-specific patterns.
    - Test the lawn mowing functionality in controlled environments and evaluate its performance on different types of grass.

4. **Develop Computer Vision for Trash Identification**
    - Train object detection models to identify various litter types (e.g., bottle caps, cans, wrappers).
    - Optimize for outdoor conditions, including lighting changes, cluttered environments, and seasonal variations.
    - Validate the vision system with field data and iteratively improve detection accuracy.

5. **Design and Integrate a Robot Arm**
    - Develop a robotic arm capable of picking up and sorting litter.
    - Implement gripping mechanisms for handling different trash shapes and materials.
    - Add sorting capabilities for separating recyclable and non-recyclable waste.

6. **Combine All Systems**
    - Integrate navigation, vision, mowing (if applicable), and litter handling into a cohesive system.
    - Test the robot's full functionality in real-world environments like parks or urban streets.
    - Iterate on the design to improve reliability and efficiency.
