# STELLAR OUTREACH — Mobile App

A cosmic companion — daily astrological briefings, space station management, and celestial discovery.

Built with React Native (iOS/Android) + Python backend.

---

## Project Structure

```
stellar-outreach/
├── mobile/          ← React Native app (open ios/ in Xcode)
├── src/             ← Python API backend (port 8080)
├── start-backend.sh ← Start the backend server
└── requirements.txt ← Python dependencies
```

---

## Quick Start

### 1. Start the Backend

```bash
bash start-backend.sh
```

Leave this terminal running. The mobile app connects to `http://localhost:8080`.

### 2. Install Mobile Dependencies

```bash
cd mobile
npm install
cd ios && pod install && cd ..
```

### 3. Run on iOS Simulator

```bash
cd mobile
npx react-native run-ios
```

### 4. Run on Physical iPhone → See the Xcode guide below

---

## Full Xcode Guide — Running on Your iPhone

### Prerequisites

| Tool | How to get it |
|---|---|
| Xcode | Mac App Store (free) |
| Apple ID | appleid.apple.com (free account works) |
| Node.js 22+ | nodejs.org or `brew install node` |
| CocoaPods | `sudo gem install cocoapods` |
| Python 3.11+ | python.org or `brew install python` |

---

### Step 1 — Install dependencies

Open Terminal, navigate to this folder, then run:

```bash
# Python backend dependencies
pip3 install -r requirements.txt

# React Native JavaScript dependencies
cd mobile && npm install

# iOS native dependencies (CocoaPods)
cd ios && pod install && cd ..
```

> `pod install` can take 3–5 minutes the first time.

---

### Step 2 — Open the project in Xcode

**IMPORTANT:** Always open the `.xcworkspace` file, NOT `.xcodeproj`.

```bash
open mobile/ios/StellarOutreach.xcworkspace
```

Or in Finder: navigate to `mobile/ios/` and double-click `StellarOutreach.xcworkspace`.

---

### Step 3 — Set up code signing

1. In Xcode, click **StellarOutreach** in the left panel (the top-level project icon)
2. Select the **StellarOutreach** target (under TARGETS)
3. Click the **Signing & Capabilities** tab
4. Check **Automatically manage signing**
5. Under **Team**, click the dropdown and select **Add an Account...**
6. Sign in with your Apple ID
7. After signing in, select your personal team (e.g. "Your Name (Personal Team)")
8. Change the **Bundle Identifier** to something unique:
   - Example: `com.yourname.stellaroutreach`
   - It must be unique — Apple rejects duplicates

---

### Step 4 — Connect your iPhone

1. Plug your iPhone into your Mac via USB cable
2. Unlock your iPhone and tap **Trust** when it asks "Trust This Computer?"
3. In Xcode, at the top of the window, click the device selector (next to the play button)
4. Your iPhone should appear in the list — select it

---

### Step 5 — Trust the developer certificate on your iPhone

The first time you run an app from a personal account, iOS will block it until you trust the certificate:

1. On your iPhone: **Settings → General → VPN & Device Management**
2. Under "Developer App", tap your Apple ID email
3. Tap **Trust "[Your Apple ID]"**
4. Tap **Trust** on the confirmation dialog

---

### Step 6 — Start the backend server

Open a separate Terminal window and run:

```bash
bash start-backend.sh
```

Keep this running. Without it, the app will show offline mode.

---

### Step 7 — Build and run

1. In Xcode, click the **▶ Play button** (top left) or press `Cmd+R`
2. Xcode will build the app (first build takes 2–4 minutes)
3. The app will install and launch automatically on your iPhone

---

### Troubleshooting

**"No signing certificate" error**
→ Go to Signing & Capabilities, make sure your Apple ID is added and team is selected.

**"Device is not connected" or iPhone not showing**
→ Unplug and replug the cable. Make sure you tapped Trust on the phone.

**Build fails with "pod not found" errors**
→ Run `cd mobile/ios && pod install` again, then clean build: Xcode → Product → Clean Build Folder (`Shift+Cmd+K`), then run again.

**App opens but shows "OFFLINE — Cached data"**
→ Make sure `bash start-backend.sh` is running in a terminal on the same Mac.

**"Untrusted Developer" on iPhone**
→ Go to Settings → General → VPN & Device Management → trust your Apple ID.

**Metro bundler not starting**
→ In a terminal: `cd mobile && npx react-native start`

---

## Android

```bash
cd mobile
npx react-native run-android
```

Requires Android Studio with a connected device or emulator.

---

## API Endpoints

The Python backend runs on `http://localhost:8080` and exposes `/api/stellar/*` endpoints for all app features: briefings, station management, missions, social, profile, and analytics.
