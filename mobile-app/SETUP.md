# AGNES Mobile App - Setup Guide

This wraps the Django web app into an installable Android APK using Capacitor.

## Prerequisites

1. **Node.js** (v18+): Download from https://nodejs.org/
2. **Android Studio**: Download from https://developer.android.com/studio
   - During install, ensure **Android SDK** and **Android SDK Build-Tools** are selected
   - After install, open Android Studio → SDK Manager → install **Android 13 (API 33)** or newer
3. **Java JDK 17**: Android Studio usually bundles this

## Step-by-Step Setup

### Step 1: Install dependencies

```bash
cd mobile-app
npm install
```

### Step 2: Configure server URL

Edit `capacitor.config.ts` and change the `server.url` to your Django server address:

- **Local testing** (phone + PC on same WiFi):
  ```
  url: 'http://192.168.1.100:8000'  # Your PC's local IP
  ```
  Find your IP: run `ipconfig` in CMD, look for **IPv4 Address** under your WiFi adapter.

  Also start Django with:
  ```bash
  python manage.py runserver 0.0.0.0:8000
  ```

- **Production** (deployed server):
  ```
  url: 'https://your-deployed-domain.com'
  ```
  Also set `cleartext: false` for HTTPS.

### Step 3: Add Android platform

```bash
npx cap add android
```

### Step 4: Sync the project

```bash
npx cap sync android
```

### Step 5: Open in Android Studio

```bash
npx cap open android
```

This opens the Android project in Android Studio.

### Step 6: Build the APK

**Option A - From Android Studio:**
1. Wait for Gradle sync to complete
2. Menu → Build → Build Bundle(s) / APK(s) → Build APK(s)
3. APK will be at: `android/app/build/outputs/apk/debug/app-debug.apk`

**Option B - From command line:**
```bash
cd android
./gradlew assembleDebug
```

### Step 7: Install on phone

Transfer the APK to your Android phone and install it, OR:
- Connect phone via USB with **USB Debugging** enabled
- In Android Studio: click the **Run** button (green triangle)

## App Icon

To set a custom app icon:
1. In Android Studio: right-click `app/src/main/res` → New → Image Asset
2. Select your icon image
3. Click Next → Finish

## Splash Screen

The splash screen uses PNP Blue (#003087) background. To customize:
- Edit `capacitor.config.ts` → `plugins.SplashScreen`
- Add a custom splash image at `android/app/src/main/res/drawable/splash.png`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "ERR_CLEARTEXT_NOT_PERMITTED" | Ensure `cleartext: true` in capacitor.config.ts for HTTP |
| App shows white screen | Check server URL is reachable from phone's browser first |
| "Connection refused" | Ensure Django runs with `0.0.0.0:8000`, not `127.0.0.1:8000` |
| Phone can't reach PC | Both must be on same WiFi network |
| Gradle build fails | Open Android Studio → File → Sync Project with Gradle Files |

## Production Release

For a signed release APK (Play Store):
1. Android Studio → Build → Generate Signed Bundle / APK
2. Create a new keystore (save it securely!)
3. Fill in key details
4. Build → APK will be at `android/app/release/`
