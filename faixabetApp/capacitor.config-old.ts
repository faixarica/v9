import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.faixabet.app',
  appName: 'FaixaBet',
  webDir: 'www',
  bundledWebRuntime: false,
  server: {
    url: 'https://faixabet9.streamlit.app',
    cleartext: false
  }
};

export default config;
