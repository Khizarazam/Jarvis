# Jarvis Voice Assistant (Windows)

Ye ek real desktop program hai jo aapke Windows PC pe **install** hoga aur voice command sun kar tasks perform karega. Browser wali file se ye alag hai — ye seedha aapke PC pe chalta hai.

## Abhi ye tasks kar sakta hai
- **App khol na** — "open chrome", "open notepad", "open calculator", "open whatsapp", "open word", "open excel", "open paint", "open file explorer", "open task manager", "open control panel", "open command prompt", "open edge", "open firefox", "open spotify" — aur agar app `config.json` me list nahi bhi hai, ye phir bhi "open <naam>" try karega (Windows ka generic `start` command use kar ke)
- **App band karna (naya)** — "close chrome", "close notepad"
- **Weather check karna** — "what's the weather", "weather in Karachi"
- **WhatsApp message bhejna** — "message ali tell him I'm on my way" (contact `contacts.json` me pehle se save honi chahiye)
- **Facebook/Meta ads schedule karna** — "schedule example ad tomorrow 5 pm to 9 pm" (neeche is ka poora setup likha hai)
- **Time/date batana** — "what's the time", "what's the date"
- **Web search karna** — "search best mobile phones 2026"
- **Website seedha kholna (naya)** — "open website youtube", "go to gmail.com"
- **Volume control (naya)** — "volume up", "volume down", "mute"
- **PC lock/shutdown/restart/sleep (naya)** — "lock the screen", "shut down", "restart", "sleep", "cancel shutdown"
- **Screenshot lena (naya)** — "take a screenshot" (`screenshots` folder me save hoti hai)
- **Battery / CPU / RAM status (naya)** — "battery status", "cpu status"
- **Wi-Fi password batana (naya)** — "what's the wifi password", "wifi password batao" — jis Wi-Fi se PC connect hai, uska saved password bata deta hai (Windows apne `netsh` command se pehle se save kiya hua password nikalta hai — koi hacking nahi, wahi jo Control Panel se manually bhi dekha ja sakta hai). **Zaroori:** password dekhne ke liye Jarvis ko **Administrator** ke tor par run karna padega (Jarvis.exe pe right-click > "Run as administrator"), warna Windows password chupa dega.
- **Urdu mein baat karna aur cheezein yaad rakhna** — dekhein neeche "Urdu + Memory" section
- **Band karna** — "exit" ya "goodbye" ya "stop listening"

Har command ab apne error se poori app ko crash nahi karega — agar koi ek cheez fail ho (jaise internet na ho, ya app na mile), Jarvis bata dega aur agli command sunta rahega.

## Ab VS Code/manual run ki zaroorat nahi (naya!)

Pehle har baar `run_gui.bat` ya VS Code se khud chalana padta tha. Ab 3 cheezein add hui hain taake Jarvis khud-ba-khud chalta rahe:

**1. Wake word — sirf "Jarvis" bolen**
Ab Jarvis chup-chap background me sirf apna naam sunta rehta hai. Jab tak aap "Jarvis" na bolen, koi command execute nahi hoti. Bolne ke 2 tareeqe:
- Sirf `"Jarvis"` bolen, phir jab wo "Yes?" bole to apni command bolen
- Ya ek hi saans me `"Jarvis, what's the time"` bol dein

Ye `config.json` me `"wake_word": "jarvis"` aur `"wake_word_enabled": true` se control hota hai. Agar bilkul off karna ho (purana wala tareeqa — har baar sunta rahe bina wake word ke), `"wake_word_enabled": false` kar dein.

**2. System tray — window band karne pe app band nahi hoti**
Jab aap Jarvis ki window ka X (close) button dabate hain, ab wo band nahi hoti — background me chalti rehti hai aur wake word sunti rehti hai. Neeche taskbar ke system tray me ek chhota Jarvis icon nazar aayega — usay click karein to window wapas khul jayegi, ya right-click karke "Exit" chunein to poora band ho jayega.

**3. Windows startup pe khud chalna**
1. Pehle `build_exe.bat` chalayein (agar pehle se nahi chalaya) — ye `dist\Jarvis.exe` banayega
2. Phir `install_startup.bat` pe double-click karein — ye Jarvis ko Windows Startup me daal dega
3. Ab jab bhi aap apna PC on karke login karenge, Jarvis khud chal jayega — bilkul background me, VS Code ya kisi terminal ki zaroorat nahi

Agar chahte hain ke window bilkul na dikhe aur seedha tray me chala jaye (login pe koi popup na ho), to `dist\config.json` me `"start_minimized": true` kar dein.

Startup se hata na ho to `uninstall_startup.bat` chala dein.

**Auto-start listening:** GUI khulte hi khud listening shuru ho jati hai (Start button dabane ki zaroorat nahi) — ye `config.json` me `"auto_start_listening": true` se control hota hai.

## Naya HUD (sci-fi) interface
`run_gui.bat` ab ek **eDEX-UI / TRON-style HUD** dikhata hai: glowing cyan corner brackets, live radar jo listening/thinking/speaking ke hisaab se animate hota hai, live clock/date, aur terminal-style conversation log. Neeche do naye buttons bhi hain: **View Memory** aur **Commands** (poori command list dikhane ke liye).

Screenshot/battery features ke liye do extra Python packages chahiye (already `requirements.txt` me add hain): `Pillow` aur `psutil`.

## Urdu + Memory (naya feature)

**Urdu samajhna:** Jarvis ab Urdu mein bola gaya command bhi samajhne ki koshish karega (jaise "mera naam Ali hai"). Yeh `config.json` ke `"language": "ur-PK"` setting se control hota hai. Agar Urdu recognition kaam na kare to yeh khud-ba-khud English (`en-US`) try kar leta hai, is liye dono zubanein ek hi session me chal sakti hain. Agar aap sirf English/Roman-Urdu use karna chahte hain to `config.json` me `"language"` ko `"en-US"` kar dein.

**Cheezein yaad rakhna (permanent memory):** Jo bhi aap Jarvis ko batayen, wo `memory.json` file me save ho jata hai — yani program band kar ke dubara chalayein to bhi yaad rehta hai.

- Naam batana: *"my name is Ali"*, *"mera naam Ali hai"*, ya Urdu script me *"میرا نام علی ہے"*
- Naam poochna: *"what is my name"* ya *"mera naam kya hai"*
- Koi bhi general fact yaad karwana: *"remember my birthday is May 5"* ya *"yaad rakho office ka time 9 baje hai"*
- Wo fact wapas poochna: *"office ka time kya hai"*

Agar kabhi memory reset karni ho to bas `memory.json` file delete kar dein — agli dafa program khud nayi khaali file bana lega.

Naye commands baad me isi tarah add ho sakte hain — ye ek foundation hai, poora "sab kuch" nahi.

## Setup (ek dafa karna hai)

### 1. Python install karein
[python.org/downloads](https://www.python.org/downloads/) se Python 3.10+ install karein.
**Zaroori:** installer me "Add Python to PATH" checkbox zaroor tick karein.

### 2. Ye folder kahin save karein
Poora `jarvis-assistant` folder apne PC pe kisi jagah rakh dein (jaise Desktop pe).

### 3. Dependencies install karein
Folder me Command Prompt kholen (folder ke andar right-click > "Open in Terminal") aur ye chalayen:

```
pip install -r requirements.txt
```

Agar `PyAudio` install hone me error de, to ye try karein:
```
pip install pipwin
pipwin install pyaudio
```

### 4. Weather API key lagayen (optional, weather ke liye zaroori)
1. [openweathermap.org/api](https://openweathermap.org/api) pe free account banayen
2. Apni free API key copy karein
3. `config.json` file kholen, `"weather_api_key": ""` me apni key paste kar dein

### 5. Apne contacts add karein (WhatsApp messages ke liye zaroori)
`contacts.json` kholen aur naam + poora phone number (country code ke saath, jaise `+92...`) daal dein.

### 6. Facebook/Meta ads scheduling set up karein (optional, agar wo feature chahiye)

Ye feature 2 files aur 1 background program use karta hai — Meta security ki wajah se ye cheezein aapko khud lani hongi, main issue nahi kar sakta:

**a) Ad set pehle Ads Manager me bana lein** — normal tareeqe se, lekin **status "Paused"** rakhein. Jarvis sirf is ko ON/OFF karega, naya banayega nahi.

**b) Meta Access Token lein:**
1. [developers.facebook.com](https://developers.facebook.com/) pe jayen, apna app banayen (Business type)
2. Apne Business Manager se app ko ad account access dein
3. "Marketing API" permission ke saath ek **access token** generate karein (System User token best hai, lambe time tak valid rehta hai)
4. Ye token `config.json` me `"meta_access_token"` field me paste karein

**c) Apne ad set ki ID lein:**
Ads Manager me apni ad set khol kar URL ya "..." menu se ad set ID copy karein (ek lamba number hota hai).

**d) `ad_sets.json` me apna naam-to-ID mapping likhein**, jaise:
```json
{
  "eid sale": "120212345678901",
  "winter collection": "120209876543210"
}
```
Yehi naam aap voice se bolenge — jaise "schedule eid sale tomorrow 5 pm to 9 pm".

**e) Background scheduler chalayein:**
`run_scheduler.bat` pe double-click karein — ye ek alag terminal window me hamesha chalta rahega aur har 30 second me check karega ke koi scheduled ad ka waqt aa gaya hai.
**Ye window band mat karein** — jab tak ye chal rahi hai, tab tak hi ads on/off honge. Behtar hai isay Windows startup pe automatically chalne ke liye Task Scheduler me add kar dein (Windows me "Task Scheduler" search karein > "Create Basic Task" > `run_scheduler.bat` ko select karein > "When the computer starts").

### 7. Chalayen

Ab isay chalane ke **teen tareeqe** hain:

**a) Terminal wala version (jaisa pehle tha):**
`run.bat` pe double-click karein — kaala terminal window khulega jisme text dikhta rahega.

**b) Proper HUD app window (naya, recommended):**
`run_gui.bat` pe double-click karein — ye ek sci-fi HUD-style window kholega: animated radar, live clock, **Start/Stop** button, live conversation log, "View Memory" button, aur "Commands" button (poori list). Ye andar se wahi assistant.py hi use karta hai, bas ek futuristic application jesi shakal deta hai.

**c) Ek standalone `.exe` program bana lein (bilkul normal software ki tarah):**
`build_exe.bat` pe double-click karein. Ye pehli dafa thoda time lega (PyInstaller install kar ke `.exe` banayega). Jab mukammal ho jaye to `dist` folder ke andar `Jarvis.exe` mil jayega — is `dist` folder ko kahin bhi (jaise Desktop) copy kar ke rakh sakte hain aur bas double-click kar ke chala sakte hain. **Iske baad Python ya terminal ki bilkul zaroorat nahi** — bilkul normal installed software ki tarah kaam karega, aur Start menu ya Desktop pe shortcut bhi bana sakte hain.

Teeno tareeqon mein microphone permission mangega — allow kar dein.

**Yaad rahe:** voice assistant (`run.bat`) sirf commands sunta hai. Actual ad ON/OFF **`run_scheduler.bat`** wala background program karta hai — is liye scheduling feature use karne ke liye dono ka chalna zaroori hai (pehli baar schedule bolne ke liye `run.bat`, phir hamesha chalte rehne ke liye `run_scheduler.bat`).

## Zaroori baatein (honest limitations)
- Pehli baar WhatsApp message bhejte waqt, browser me WhatsApp Web khulega — ussey pehle apne phone se ek dafa QR code scan kar ke login karna hoga (jaisay normal WhatsApp Web use karte hain)
- Ye internet chahta hai (voice recognition aur weather ke liye)
- Ye microphone ki quality pe depend karta hai — shor wali jagah pe ghalat sun sakta hai
- Ye "har cheez" nahi karta — jo commands upar list ki hain sirf wahi abhi kaam karte hain
- Isay hamesha chalaana hoga (ek terminal window open rehni chahiye) — ye khud background me chup ke nahi chalta abhi
- Ad scheduling sirf tab kaam karegi jab `run_scheduler.bat` chal raha ho — ye check karne ke liye `scheduler_log.txt` file khol kar dekhein ke ad ON/OFF hua ya nahi, ya koi error aayi
- Meta access token ki expiry hoti hai (permanent token System User se milta hai) — agar scheduling achanak kaam karna band kar de, sabse pehle token check karein

## Naya command add karna chahen to
`assistant.py` file me `handle_command()` function ke andar naya `elif` block add karein, aur uske liye ek naya function likhein — jaisay `open_app()`, `check_weather()` waisa hi pattern follow karein.
