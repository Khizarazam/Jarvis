# Jarvis Voice Assistant

Ye repo do versions rakhta hai:

- **`desktop/`** — Windows PC ke liye Python voice assistant (poori app khud install ho kar background mein chalti hai, wake word, system tray, .exe build sab shamil). Setup ke liye `desktop/README.md` dekhein.
- **`mobile/`** — Phone ke browser mein chalne wala web-app version (voice + typed commands, "Add to Home Screen" se app jaisa install hota hai). Setup ke liye `mobile/README-MOBILE.md` dekhein.

## ⚠️ Secrets ka khayal rakhein
`desktop/config.json` mein `weather_api_key` aur `meta_access_token` ke fields hain — jab in mein apni real keys daalein, tab `desktop/config.json` ko **is repo mein commit na karein** (khaas kar agar repo public hai). Isay `.gitignore` mein already add kar diya gaya hai taake accidentally commit na ho.
