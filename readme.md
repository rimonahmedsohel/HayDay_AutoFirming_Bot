<div align="center">
  <h1>🌾 HFB — Hay Day Auto-Farming Bot</h1>
  <p><strong>A fully autonomous, intelligent farming assistant for Hay Day</strong></p>
  
  [![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://python.org)
  [![OpenCV](https://img.shields.io/badge/OpenCV-Template%20Matching-green.svg)](https://opencv.org)
  [![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
</div>

<br />

HFB is a robust, production-ready Windows application that fully automates the agricultural lifecycle in Hay Day. It utilizes advanced computer vision (OpenCV scale-invariant template matching) and low-level device interaction (ADB + minitouch) via MuMu Player to seamlessly plant, harvest, and sell crops infinitely.

---

## ✨ Features

- **🎮 All-in-One Standalone Application**: Built into a single `.exe` file with a sleek dark-themed GUI. No Python installation, ADB setup, or command-line experience required.
- **🔄 Infinite Master Loop**: Autonomously cycles through Planting ➔ Harvesting ➔ Selling.
- **🏗️ Resilient Error Handling & Crash Recovery**: If the game crashes, gets stuck, or the cycle fails 3 times, the bot automatically handles ADB restarts, re-launches the game, dismisses daily popups, and realigns the camera via a custom pinch-to-zoom injection.
- **💰 Smart Selling & "Silo Full" Handling**: When the silo hits maximum capacity, the bot instantly diverts to the Roadside Shop, sells inventory, occasionally clicks ads, and safely waits before resuming the harvest.
- **🧭 Dynamic Vision System**: Uses scale-invariant template matching to locate exact UI elements dynamically. The camera can move, but the bot will find what it needs.
- **⚡ Background Execution**: The core processing and ADB commands run entirely in the background without stealing your mouse or launching annoying terminal windows.

## 🚀 Quick Start (For Users)

The easiest way to use the bot is to download the standalone `.exe` release.

### Prerequisites
1. **MuMu Player**: You must use MuMu Player (Android Emulator) to run Hay Day.
2. **Resolution & Settings**: 
   - Ensure the emulator resolution provides a clear view of the farm. 
   - The bot connects to the default MuMu port: `127.0.0.1:7555`.
3. **In-Game Setup**: Wait until your crops are empty and you are ready to plant Wheat.

### Running the App
1. Download `HFB.exe` from the [Releases](#) page.
2. Double-click `HFB.exe` to launch the GUI.
3. Verify your Hay Day game is open and running in MuMu Player.
4. Click **▶ Start Bot**. The live log panel will display the connection status and progress.
5. Click **■ Stop Bot** at any time to instantly lock the logic and halt the bot safely.

---

## 💻 Building from Source (For Developers)

If you'd like to modify the logic, adjust the timings, or build the executable yourself:

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/HayDay_AutoFirming_Bot.git
cd HayDay_AutoFirming_Bot
```

### 2. Install Dependencies
Ensure you have Python 3.9+ installed.
```bash
pip install opencv-python numpy pyinstaller
```

### 3. Build the Executable
The repository includes a automated `build.bat` and `hfb.spec` configuration that bundles Python, OpenCV, the `minitouch` binary, and ADB platform-tools into a single windowless executable.

Just run:
```bash
build.bat
```
*(Or manually run `python -m PyInstaller hfb.spec --noconfirm`)*

The generated file will be located at `dist/HFB.exe`.

---

## 🧠 Core Architecture

The system is highly modularized, utilizing several intelligent subsystems:

- **`hfb_app.py`**: The main Tkinter application wrapper that controls the thread lifecycle, hooks `sys.stdout` for live UI logging, and manages ADB connections.
- **`start.py`**: The "Master Loop." Orchestrates the timings, states, and the 3-strike failure mechanism.
- **`planting.py`**: Locates empty fields using `cv2.matchTemplate`, intelligently clicks the last available field to auto-pan the camera, and uses raw `motionevent` drags to plant seeds in a localized zigzag pattern.
- **`harvesting.py`**: Detects fully grown wheat, locates the sickle menu dynamically, and performs the sweep. Also handles "Silo Full" interrupt detection.
- **`sellingCrops.py`**: Manages the roadside shop. Remembers slot coordinates dynamically to avoid relying purely on image recognition to collect money later.
- **`crash_handler.py`**: Monitors Android `mCurrentFocus` via ADB `dumpsys`. Re-launches the `com.supercell.hayday` intent on failure.
- **`zoom.py`**: Due to ADB `input swipe` limitations with multi-touch, this script pushes and executes `minitouch` natively on the Android side over a TCP socket to execute a true hardware-level pinch-to-zoom gesture during crash recovery.

---

## 🤝 Contributing

Pull requests are actively welcomed! Whether it's adding support for other crops, optimizing the OpenCV thresholds, or improving the macro speed:

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

<div align="center">
  <sub>Built with ❤️ by the community. Educational purposes only.</sub>
</div>
