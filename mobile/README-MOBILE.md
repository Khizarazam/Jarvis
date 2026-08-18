# Jarvis Mobile (Phone version)

Ye asal desktop `assistant.py` ka **phone-friendly web version** hai. Ye Python nahi hai — ye ek website/app hai jo aapke phone ke browser mein khulti hai aur "Add to Home Screen" karne ke baad bilkul normal app ki tarah chalti hai.

**Zaroori sach baat pehle:** phone ek desktop PC nahi hai, aur ek browser page security wajuhat ki bina par PC jaisay OS-level cheezein nahi kar sakta (jaise shutdown karna, wifi password nikalna, dusri apps band karna, volume control). Neeche poori honest list hai ke kya kaam karta hai aur kya nahi.

## Kaise chalayen (setup)

Voice (microphone) sirf **HTTPS** pe kaam karti hai — seedha file khol kar (double-click) microphone kaam nahi karega. Do tareeqe hain:

### Tareeqa A — Free hosting (recommended, permanent link banta hai)
1. Is `jarvis-mobile` folder ko GitHub pe ek naya repository bana kar upload kar dein (ya Netlify Drop — netlify.com/drop — pe seedha folder drag-drop kar dein, koi account bhi zaroori nahi).
2. GitHub use karen to repo ke Settings > Pages me jaa kar "Deploy from branch" on kar dein — kuch minute me ek `https://...github.io/...` link mil jayega.
3. Wo link apne phone ke Chrome (Android) ya Safari (iPhone) me kholein.
4. Chrome me address bar ke menu (⋮) se **"Add to Home Screen"** kar lein — ab ye bilkul app icon ki tarah kaam karega.

### Tareeqa B — Sirf typed commands ke liye, bina hosting ke
Agar sirf typing wala hissa use karna hai (voice nahi), to `index.html` seedha phone pe bhej kar (WhatsApp/email se) file manager se khol sakte hain — text commands, weather, WhatsApp messaging, memory sab kaam karega. Sirf microphone wala voice input HTTPS maangta hai.

## Multiple languages (naya)
Settings mein ab **11 languages** hain: English, Urdu, Hindi, Arabic, French, Spanish, German, Turkish, Bengali, Punjabi, Chinese.

- **English, Urdu, Hindi, Arabic, French, Spanish** — in cheh languages mein Jarvis ke saare jawabat (speak), commands samajhna (time/date/weather/search/naam/facts/exit), aur microphone/voice sab us zaban mein kaam karte hain.
- **German, Turkish, Bengali, Punjabi, Chinese** — inke liye microphone recognition aur reply ki awaz (voice) us zaban ki tarah tuned hoti hai, lekin jawab ka text abhi English mein hi aata hai (poori translation baad mein add ki ja sakti hai — `index.html` ke andar `TRANSLATIONS` object dekhein, wahi pattern follow kar ke naya language block add karein).
- Roman Urdu/Roman Hindi commands (jaise "mera naam Ali hai") kisi bhi selected language ke sath samajh aate hain — ye sirf mic tuning aur voice reply badalta hai.

## Config kahan hai
Desktop version `config.json` / `contacts.json` / `memory.json` files use karta tha. Mobile version yehi cheez app ke andar **⚙ Settings** button se karta hai (data phone ke browser storage me save hota hai, kisi server pe nahi jata):
- Assistant ka naam, language (English/Urdu), wake word
- OpenWeatherMap API key aur default city (weather ke liye — desktop wali dobara, free key)
- Contacts (naam + WhatsApp number) — WhatsApp message bhejne ke liye
- Memory (naam aur facts jo aap "remember..." bol kar save karwayein)

## Kya kaam karta hai (aur kaise achi tarah kaam karta hai)
- Time / date batana
- Weather (city ke saath ya default city)
- **WhatsApp message** — asal mein desktop se **behtar** kaam karta hai: `wa.me` link seedha aapki WhatsApp app khol deta hai, koi QR scan ya "WhatsApp Web login" nahi chahiye
- Web search / Google
- Website kholna (`open website youtube`, `go to gmail.com`)
- Kuch jaani-pehchani apps web se kholna: WhatsApp, YouTube, Gmail, Maps, Instagram, Facebook, Spotify
- Naam aur facts yaad rakhna (Urdu/Roman Urdu/English teeno mein) — `memory.json` ki jagah browser storage
- Battery percentage (kuch Android browsers pe)
- Wake word ("Jarvis") — agar browser Web Speech API support kare (Android Chrome me best kaam karta hai)
- **Typed commands** — agar voice na chale (jaise iPhone Safari pe, jahan voice recognition support nahi hai), to neeche text box me command type kar ke bhi wahi sab kaam ho jata hai

## Kya kaam **nahi** karta (honest limitations, jaisay desktop README me thi)
| Command | Kyun nahi |
|---|---|
| App khol na jo web-based na ho (calculator, notepad, camera, settings, file explorer) | Browser security phone pe dusri native apps launch nahi karne deti |
| App band karna (close/quit) | Browser ko dusri apps band karne ki ijazat nahi |
| Volume up/down/mute | Phone volume ke liye koi web API nahi hai |
| Shutdown / restart / lock / sleep | Power control web page ko allowed nahi |
| Wifi password batana | Security ki wajah se browsers saved Wi-Fi passwords tak access nahi de sakte |
| Screenshot lena | Phone ka apna screenshot shortcut use karein (power + volume down button) |
| CPU / RAM status | Web pages ko ye info phone pe available nahi hoti |
| Meta ads schedule karna | Sirf desktop version me — Ads Manager API access chahiye |

Ye pura list app ke andar bhi **"Commands"** button dabane se dikh jayegi.

## Voice recognition ka reality check
- **Android Chrome:** achi tarah kaam karta hai (Google ka built-in speech engine use karta hai)
- **iPhone Safari:** voice recognition support nahi karta abhi — is liye typed commands wala option zaroori hai, aur wahi automatically use ho jata hai
- Shor wali jagah pe galat sun sakta hai — yehi baat desktop version me bhi thi

## Data kahan save hota hai
Sab kuch — settings, contacts, memory — sirf **aapke phone ke browser** me (localStorage) save hota hai, kisi server pe nahi jata. App uninstall/browser data clear karne se ye sab reset ho jayega — bilkul waisay jaisay desktop pe `memory.json` delete karne se hota tha.

## Naya command add karna chahen to
`index.html` ke andar `runCommand()` function me ek naya `else if` block add karein — bilkul `assistant.py` ke `handle_command()` jaisa pattern.
