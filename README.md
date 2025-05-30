# Optical Velocimetry System

A **low-cost, vision-based flow sensor** for real-time surface velocity and discharge estimation in open channel water bodies such as rivers, canals, and streams. This system leverages optical flow techniques and onboard computing to enable **autonomous, contactless discharge measurement**, especially useful in unstructured or hazardous environments.

---

## Project Overview

This system was developed as a research prototype to address the limitations of conventional flow measurement methods, particularly in sites where physical access is difficult or unsafe. It uses a Raspberry Pi with a camera module to capture surface flow, applies the **Lucas-Kanade optical flow algorithm** to track particle motion, and computes discharge based on real-world calibration.

---

## Features

- **Optical Flow Tracking:** Uses Lucas-Kanade method to track water surface motion.
- **Real-time Velocity & Discharge Calculation**
- **Touchscreen GUI:** Built with `Tkinter`, optimized for Raspberry Pi touchscreen.
- **Onboard Storage:** Saves processed videos and CSV outputs locally.
- **No Internet Required:** Fully standalone device.
- **Portable & Weather-proof Casing:** Acrylic laser-cut enclosure for field use.

---

## Hardware Used

- Raspberry Pi 4B
- Camera Module (IR/Standard)
- 7-inch Capacitive Touchscreen LCD
- Acrylic case (laser cut & custom-fabricated)
- Power Bank (for field deployment)

---

## Repository Structure

```
optical_velocimetry/
├── main.py                # GUI and main app logic
├── vision.py              # Optical flow & velocity estimation logic
├── icon2.png              # GUI icon
├── videos/                # Input: recorded videos
│   └── test_87.mp4
├── results/               # Output: velocity results in CSV format
│   └── Result_velocity_test_87.csv
└── README.md              # Project overview and instructions
```



> Note: A separate folder `Demo_videos/` was excluded due to large file size. It contains rendered videos with flow tracking overlays, available on request.

---

## How It Works

1. **Camera Setup:** Mount above water surface using builtin infrastructure.
2. **Capture Video:** GUI allows 15-second recording at 30 FPS.
3. **Run Optical Flow:** Tracks features frame-to-frame using Lucas-Kanade method.
4. **Compute Velocity:** Converts pixel movement to ft/sec using real-world calibration.
5. **Calculate Discharge:** Uses user-input width & depth to compute cusec values.

---

## Installation & Usage

> This is intended for **Raspberry Pi 4** with a connected 7" LCD screen.

### Prerequisites:

- Python 3.11+
- `opencv-python`
- `numpy`
- `tkinter`

### Install Dependencies:

```bash
pip install opencv-python numpy
```


---

### Run the GUI

```bash
python3 main.py
```

---

## Research & Applications
This project was developed as part of an MS thesis to:
- Reduce reliance on expensive ADCP equipment.
- Improve real-time discharge measurement in flood-prone areas like Namal Lake.
- Validate accuracy through controlled experiments & field data comparisons.

---

## Code Repository
All source code, logic, and configuration files are available in this GitHub repo:  
👉 [https://github.com/LUMS-WIT/Optical-Velocimetry-System](https://github.com/LUMS-WIT/Optical-Velocimetry-System)

---

## Developed By
- **Aqsa Ali**
(MS Student, Lahore University of Management Sciences (LUMS))
- Supervised by **Dr. Talha Manzoor**
- Co-supervised by **Dr. Abu Bakr Muhammad**
