import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.agnes.hotspot',
  appName: 'AGNES',
  webDir: 'www',

  // Point to your deployed Django server
  server: {
    // IMPORTANT: Change this to your actual deployed server URL
    // For local development: 'http://192.168.x.x:8000' (use your PC's local IP, NOT localhost)
    // For production: 'https://your-domain.com'
    url: 'http://192.168.1.71:8000',

    // Allow navigation to the Django server
    allowNavigation: ['*'],

    // Clear text traffic (HTTP) - needed for local development
    // Set to false in production with HTTPS
    cleartext: true,
  },

  // Android-specific configuration
  android: {
    // Allow mixed content (HTTP images on HTTPS pages)
    allowMixedContent: true,

    // Enable WebView debugging (disable in production)
    webContentsDebuggingEnabled: true,

    // Splash screen background color (PNP Blue)
    backgroundColor: '#003087',
  },

  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#003087',
      showSpinner: true,
      spinnerColor: '#FFFFFF',
      androidSplashResourceName: 'splash',
      androidScaleType: 'CENTER_CROP',
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#003087',
    },
  },
};

export default config;
