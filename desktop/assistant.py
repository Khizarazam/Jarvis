"""
Jarvis-style Voice Assistant for Windows
------------------------------------------
Listens for your voice, understands simple commands, and performs them on
your PC: open apps, check weather, send a WhatsApp message, search the web,
tell the time/date.

This is a starting foundation, not a finished "does everything" product.
Real voice assistants (Siri, Alexa) took companies years to build. This
covers the common tasks below and is written so you (or Claude, later) can
add more commands over time by adding new "if command..." blocks.

SETUP: see README.md in this folder before running.
"""

import os
import sys
import json
import time
import platform
import subprocess
import webbrowser
import datetime
import ctypes

import speech_recognition as sr
import pyttsx3
import requests
import dateparser
import re

try:
    import psutil
except ImportError:
    psutil = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

IS_WINDOWS = platform.system() == "Windows"

# ---------------------------------------------------------------------------
# Load configuration
# ---------------------------------------------------------------------------
# When packaged into a standalone .exe (via PyInstaller), __file__ points to a
# temporary extraction folder that gets deleted on exit — so config.json and
# memory.json must instead be read/written next to the actual .exe, or memory
# wouldn't survive a restart. When running as a normal .py script, this is
# just the folder this file lives in, same as before.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
CONTACTS_PATH = os.path.join(BASE_DIR, "contacts.json")

def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_json(CONFIG_PATH, {
    "assistant_name": "Jarvis",
    "weather_api_key": "",
    "default_city": "Lahore",
    "wake_word": "jarvis",
    "wake_word_enabled": True,
    "auto_start_listening": True,
    "start_minimized": False,
    "apps": {
        "chrome": "start chrome",
        "notepad": "notepad",
        "calculator": "calc",
        "whatsapp": "start https://web.whatsapp.com",
        "word": "start winword",
        "excel": "start excel"
    }
})

contacts = load_json(CONTACTS_PATH, {})
AD_SETS_PATH = os.path.join(BASE_DIR, "ad_sets.json")
SCHEDULE_PATH = os.path.join(BASE_DIR, "schedule.json")
ad_sets = load_json(AD_SETS_PATH, {})

# Long-term memory (persists across restarts) — stores things you tell it to remember,
# like your name or any other fact ("remember my name is Ali", "remember my birthday is May 5")
MEMORY_PATH = os.path.join(BASE_DIR, "memory.json")
memory = load_json(MEMORY_PATH, {"user_name": None, "facts": {}})


def save_memory():
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# Voice engines
# ---------------------------------------------------------------------------
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()
tts_engine.setProperty("rate", 175)

# Optional hooks so a GUI (gui.py) can show what's happening, instead of only
# printing to a terminal. If no GUI is running these are simply unused.
_on_speak = None      # callback(text) — called whenever the assistant says something
_on_status = None     # callback(status_text) — called on state changes (Listening/Idle/etc.)


def set_gui_hooks(on_speak=None, on_status=None):
    global _on_speak, _on_status
    _on_speak = on_speak
    _on_status = on_status


def speak(text):
    print(f"[{config['assistant_name']}]: {text}")
    if _on_speak:
        _on_speak(text)
    if _on_status:
        _on_status("Speaking…")
    try:
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception as e:
        print(f"(voice output error, continuing silently: {e})")
    if _on_status:
        _on_status("Idle")


def listen(quiet=False):
    """Listen from the default microphone and return recognized text (lowercase), or '' on failure.
    Tries Urdu first (so aap Urdu mein bol sakte hain), then falls back to English if that fails —
    so both "mera naam Ali hai" (Urdu) and "open chrome" (English) work in the same session.

    quiet=True is used by the wake-word standby loop: it stays silent on recognition
    failures/network hiccups instead of speaking every few seconds, since standby listening
    happens continuously in the background.
    """
    if _on_status:
        _on_status("Listening…")
    with sr.Microphone() as source:
        print("\n(listening...)")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=6, phrase_time_limit=8)
        except sr.WaitTimeoutError:
            if _on_status:
                _on_status("Idle")
            return ""

    if _on_status:
        _on_status("Thinking…")
    primary_lang = config.get("language", "ur-PK")
    fallback_lang = "en-US" if primary_lang != "en-US" else "ur-PK"

    for lang in [primary_lang, fallback_lang]:
        try:
            text = recognizer.recognize_google(audio, language=lang)
            print(f"(you said [{lang}]: {text})")
            if _on_status:
                _on_status("Idle")
            return text.lower()
        except sr.UnknownValueError:
            continue
        except sr.RequestError:
            if _on_status:
                _on_status("Idle")
            if not quiet:
                speak("I can't reach the speech recognition service right now. Check your internet connection.")
            return ""
    if _on_status:
        _on_status("Idle")
    return ""


# ---------------------------------------------------------------------------
# Wake word — lets Jarvis sit passively in the background and only act once
# you say its wake word ("jarvis" by default), instead of treating every
# sound it hears as a command.
# ---------------------------------------------------------------------------

def listen_for_wake_word(stop_check=None):
    """
    Loops quietly listening until the wake word is heard.
    Returns:
      - a string: the words spoken right after the wake word in the same breath
        (e.g. "jarvis open chrome" -> "open chrome"), which may be "" if only
        the wake word was said and a follow-up command should be listened for next.
      - None: if stop_check() returned True (caller asked us to stop, e.g. GUI Stop button).
    """
    wake_word = config.get("wake_word", "jarvis").lower()
    while True:
        if stop_check and stop_check():
            return None
        text = listen(quiet=True)
        if not text:
            continue
        if wake_word in text:
            remainder = text.split(wake_word, 1)[1].strip()
            return remainder


# ---------------------------------------------------------------------------
# Task handlers — each function performs one real action on the PC
# ---------------------------------------------------------------------------

def open_app(command):
    """
    Tries known apps from config.json first (exact, curated commands).
    If nothing matches, falls back to a generic Windows 'start <name>' attempt
    so it can still try to open apps that aren't explicitly configured
    (most installed Windows programs respond to 'start <name>').
    """
    text = command.replace("open", "", 1).strip()

    for app_name, run_command in config["apps"].items():
        if app_name in command:
            speak(f"Opening {app_name}.")
            try:
                os.system(run_command)
            except Exception as e:
                speak(f"I found {app_name} but couldn't launch it.")
                print(f"Error opening {app_name}: {e}")
            return True

    if not text:
        return False

    # Generic fallback for anything not explicitly configured.
    if IS_WINDOWS:
        speak(f"Trying to open {text}.")
        try:
            os.system(f'start "" "{text}"')
        except Exception as e:
            speak(f"I couldn't open {text}. You can add it to config.json under 'apps' for a reliable shortcut.")
            print(f"Error opening {text}: {e}")
        return True
    else:
        speak(f"{text} isn't a configured app, and app-launching only works on Windows right now. "
              f"Add it to config.json under 'apps'.")
        return True


def close_app(command):
    """'close chrome', 'close notepad' — ends the process by name (Windows)."""
    text = command
    for trigger in ["close ", "quit "]:
        if text.startswith(trigger):
            text = text[len(trigger):].strip()
            break
    else:
        return False

    if not text:
        return False

    known_process_names = {
        "chrome": "chrome.exe", "notepad": "notepad.exe", "calculator": "CalculatorApp.exe",
        "word": "WINWORD.EXE", "excel": "EXCEL.EXE", "spotify": "Spotify.exe",
        "edge": "msedge.exe", "firefox": "firefox.exe",
    }
    process_name = known_process_names.get(text, f"{text}.exe")

    if not IS_WINDOWS:
        speak("Closing apps is only supported on Windows right now.")
        return True

    speak(f"Closing {text}.")
    try:
        subprocess.run(["taskkill", "/F", "/IM", process_name], capture_output=True)
    except Exception as e:
        speak(f"I couldn't close {text}.")
        print(f"Error closing {text}: {e}")
    return True


def check_weather(command):
    api_key = config.get("weather_api_key", "")
    if not api_key:
        speak("Weather isn't set up yet. Add a free OpenWeatherMap API key to config.json.")
        return

    city = config.get("default_city", "Lahore")
    # allow "weather in <city>" / "weather for <city>"
    for splitter in [" in ", " for "]:
        if splitter in command:
            city = command.split(splitter, 1)[1].strip().rstrip("?.! ")
            break

    if not city:
        city = config.get("default_city", "Lahore")

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}
    try:
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()
        if resp.status_code != 200:
            speak(f"I couldn't get the weather for {city}. {data.get('message', 'Please check the city name.')}")
            return
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        desc = data["weather"][0]["description"]
        speak(f"It's {temp} degrees in {city}, feels like {feels}, with {desc}.")
    except requests.Timeout:
        speak("The weather service took too long to respond. Try again in a moment.")
    except requests.RequestException:
        speak("I couldn't reach the weather service. Check your internet connection.")
    except (KeyError, IndexError):
        speak(f"I got a response for {city}, but couldn't understand it.")


def send_whatsapp_message(command):
    """
    Command format expected: "message <name> <the message text>"
    or: "whatsapp <name> <the message text>"
    Looks up the phone number for <name> in contacts.json.
    """
    # IMPORTANT: check with startswith, not "in". The old "in command" check
    # matched "message " even when it appeared *inside* the dictated message
    # text (e.g. "whatsapp ali send this message now"), which cut the
    # remainder at the wrong point and broke both name-matching and the
    # message text.
    remainder = None
    for trigger in ["whatsapp ", "message "]:
        if command.startswith(trigger):
            remainder = command[len(trigger):].strip()
            break
    if remainder is None:
        speak("Say it like: message John tell him I'm running late.")
        return

    matched_name = None
    for name in contacts:
        if remainder.startswith(name.lower()):
            matched_name = name
            break

    if not matched_name:
        speak("I don't have that contact saved. Add their name and number to contacts.json first.")
        return

    message_text = remainder[len(matched_name):].strip()
    if not message_text:
        speak(f"What should I say to {matched_name}?")
        message_text = listen()
        if not message_text:
            speak("I didn't catch a message, cancelling.")
            return

    phone = contacts[matched_name]
    if "+" not in phone:
        speak(f"{matched_name}'s number in contacts.json is missing the country code, like +92...")
        return

    try:
        import time
        import webbrowser
        from urllib.parse import quote
        import pyautogui

        pyautogui.FAILSAFE = False
        speak(f"Sending a WhatsApp message to {matched_name}.")

        url = f"https://web.whatsapp.com/send?phone={phone}&text={quote(message_text)}"
        webbrowser.open(url)

        # Give WhatsApp Web time to fully load the chat before touching anything.
        time.sleep(12)

        # The message box sits near the BOTTOM of the page, not the screen's
        # centre. Clicking dead-centre (what pywhatkit's default does) often
        # misses the box entirely on current WhatsApp Web layouts, so nothing
        # gets focused and pressing Enter does nothing — this is the main
        # reason messages silently fail to send. Click near the bottom instead.
        screen_w, screen_h = pyautogui.size()
        pyautogui.click(screen_w // 2, int(screen_h * 0.93))
        time.sleep(1.5)
        pyautogui.press("enter")
        time.sleep(2)
        pyautogui.hotkey("ctrl", "w")
    except Exception as e:
        speak("I couldn't send the WhatsApp message. Make sure WhatsApp Web is already logged in and your browser is on screen.")
        print(f"[WhatsApp send error] {type(e).__name__}: {e}")


def tell_time_or_date(command):
    now = datetime.datetime.now()
    if "date" in command:
        speak(f"Today is {now.strftime('%A, %B %d, %Y')}.")
    else:
        speak(f"It's {now.strftime('%I:%M %p')}.")


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def schedule_ads(command):
    """
    Voice command format: "schedule <ad set name> <natural date/time> to <end time>"
    Example: "schedule example ad tomorrow 5 pm to 9 pm"
    """
    text = command
    for trigger in ["schedule "]:
        if text.startswith(trigger):
            text = text[len(trigger):].strip()
            break

    # Find which known ad set name is mentioned
    matched_name = None
    for name in ad_sets:
        if text.startswith(name.lower()):
            matched_name = name
            break

    if not matched_name:
        known = ", ".join(ad_sets.keys()) if ad_sets else "none yet"
        speak(f"I don't recognize that ad set name. Known ad sets: {known}. Add it to ad_sets.json first.")
        return

    remainder = text[len(matched_name):].strip()

    # Expect something like: "tomorrow 5 pm to 9 pm"
    if " to " not in remainder:
        speak("Say it like: schedule " + matched_name + " tomorrow 5 pm to 9 pm.")
        return

    start_phrase, end_phrase = remainder.split(" to ", 1)

    # If the end phrase has no date word, borrow the date context from the start phrase
    start_dt = dateparser.parse(start_phrase, settings={"PREFER_DATES_FROM": "future"})
    end_dt = dateparser.parse(f"{start_phrase.split()[0]} {end_phrase}"
                               if not any(w in end_phrase for w in ["today", "tomorrow", "monday", "tuesday",
                                                                     "wednesday", "thursday", "friday", "saturday", "sunday"])
                               else end_phrase,
                               settings={"PREFER_DATES_FROM": "future"})

    if not start_dt or not end_dt:
        speak("I couldn't understand that date or time. Try saying it like: tomorrow 5 pm to 9 pm.")
        return

    if end_dt <= start_dt:
        end_dt = end_dt + datetime.timedelta(days=1)

    schedule = load_json(SCHEDULE_PATH, [])
    schedule.append({
        "name": matched_name,
        "ad_set_id": ad_sets[matched_name],
        "date": start_dt.strftime("%Y-%m-%d"),
        "start_time": start_dt.strftime("%H:%M"),
        "end_time": end_dt.strftime("%H:%M"),
        "status": "pending"
    })
    save_json(SCHEDULE_PATH, schedule)

    speak(f"Done. {matched_name} will start at {start_dt.strftime('%I:%M %p on %A')} "
          f"and stop at {end_dt.strftime('%I:%M %p')}. "
          f"Make sure the scheduler service is running so it actually fires.")


def open_website(command):
    """'open website youtube' / 'go to youtube.com' -> opens it in the default browser."""
    text = command
    for trigger in ["open website ", "go to "]:
        if trigger in text:
            text = text.split(trigger, 1)[1].strip()
            break
    if not text:
        speak("Which website should I open?")
        return
    url = text if text.startswith("http") else f"https://{text.replace(' ', '')}" \
        if "." in text else f"https://www.{text.replace(' ', '')}.com"
    speak(f"Opening {text}.")
    webbrowser.open(url)


def control_volume(command):
    """Uses the standard media-key virtual keycodes — works without extra dependencies on Windows."""
    if not IS_WINDOWS:
        speak("Volume control is only supported on Windows right now.")
        return
    VK_VOLUME_MUTE, VK_VOLUME_DOWN, VK_VOLUME_UP = 0xAD, 0xAE, 0xAF
    try:
        if "mute" in command:
            ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            speak("Muted.")
        elif "up" in command or "increase" in command or "raise" in command:
            for _ in range(4):
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
            speak("Volume up.")
        elif "down" in command or "decrease" in command or "lower" in command:
            for _ in range(4):
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
            speak("Volume down.")
        else:
            speak("Say volume up, volume down, or mute.")
    except Exception as e:
        speak("I couldn't change the volume.")
        print(f"Volume control error: {e}")


def system_power(command):
    """shutdown / restart / sleep / lock the PC."""
    if not IS_WINDOWS:
        speak("Power controls are only supported on Windows right now.")
        return
    try:
        if "lock" in command:
            speak("Locking the screen.")
            ctypes.windll.user32.LockWorkStation()
        elif "restart" in command or "reboot" in command:
            speak("Restarting in 5 seconds. Say cancel restart to stop it.")
            os.system("shutdown /r /t 5")
        elif "shut down" in command or "shutdown" in command:
            speak("Shutting down in 5 seconds. Say cancel shutdown to stop it.")
            os.system("shutdown /s /t 5")
        elif "cancel" in command:
            os.system("shutdown /a")
            speak("Cancelled.")
        elif "sleep" in command:
            speak("Going to sleep.")
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    except Exception as e:
        speak("I couldn't do that power action.")
        print(f"System power error: {e}")


def take_screenshot(command):
    if ImageGrab is None:
        speak("Screenshot needs the Pillow package. Run: pip install Pillow")
        return
    try:
        folder = os.path.join(BASE_DIR, "screenshots")
        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(folder, f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        ImageGrab.grab().save(filename)
        speak(f"Screenshot saved to {os.path.basename(filename)}.")
    except Exception as e:
        speak("I couldn't take a screenshot.")
        print(f"Screenshot error: {e}")


def system_status(command):
    if psutil is None:
        speak("System status needs the psutil package. Run: pip install psutil")
        return
    try:
        if "battery" in command:
            battery = psutil.sensors_battery()
            if battery is None:
                speak("This device doesn't report a battery, it might be a desktop.")
            else:
                state = "charging" if battery.power_plugged else "on battery"
                speak(f"Battery is at {round(battery.percent)} percent, {state}.")
        else:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            speak(f"CPU usage is {cpu} percent, and memory usage is {ram} percent.")
    except Exception as e:
        speak("I couldn't read the system status.")
        print(f"System status error: {e}")


def get_wifi_password(command):
    """
    'what's the wifi password' — finds the Wi-Fi network Jarvis's PC is
    currently connected to, and reads back its saved password from Windows
    (the same password Windows already has stored — this doesn't hack or
    guess anything, it just reads it via the built-in 'netsh' command, the
    same way you could manually via Control Panel > Network > Wi-Fi status).

    Note: reading the password (key=clear) usually needs Jarvis to be
    running as Administrator; otherwise Windows will show the profile but
    hide the password.
    """
    if not IS_WINDOWS:
        speak("Wi-Fi password lookup is only supported on Windows right now.")
        return

    try:
        iface_result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"], capture_output=True, timeout=10
        )
        iface_output = iface_result.stdout.decode("utf-8", errors="ignore")

        ssid = None
        for line in iface_output.splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            if key == "ssid":
                ssid = value.strip()
                break

        if not ssid:
            speak("I couldn't find a connected Wi-Fi network right now. Make sure Wi-Fi is on and connected.")
            return

        profile_result = subprocess.run(
            ["netsh", "wlan", "show", "profile", f"name={ssid}", "key=clear"],
            capture_output=True, timeout=10
        )
        profile_output = profile_result.stdout.decode("utf-8", errors="ignore")

        password = None
        for line in profile_output.splitlines():
            line = line.strip()
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            if key.strip().lower() == "key content":
                password = value.strip()
                break

        if password:
            speak(f"You're connected to {ssid}. The password is {password}.")
        else:
            speak(f"You're connected to {ssid}, but I couldn't read a saved password for it. "
                  f"This usually needs Jarvis to be running as Administrator — "
                  f"right-click Jarvis.exe and choose 'Run as administrator', then try again.")
    except subprocess.TimeoutExpired:
        speak("Checking Wi-Fi took too long. Try again.")
    except Exception as e:
        speak("I couldn't check the Wi-Fi password.")
        print(f"Wi-Fi password error: {e}")


def web_search(command):
    query = command.replace("search", "").replace("google", "").strip()
    if not query:
        speak("What should I search for?")
        query = listen()
        if not query:
            return
    speak(f"Searching for {query}.")
    webbrowser.open(f"https://www.google.com/search?q={query}")


# ---------------------------------------------------------------------------
# Memory — remember facts by voice, in Urdu, Roman Urdu, or English
# ---------------------------------------------------------------------------

NAME_PATTERNS = [
    r"(?:remember,?\s*)?my name is (.+)",
    r"tumhara naam (.+) hai",
    r"tumhara nam (.+) hai",
    r"mera naam (.+) hai",
    r"میرا نام (.+) ہے",
    r"تمہارا نام (.+) ہے",
]

NAME_RECALL_TRIGGERS = [
    "what is my name", "what's my name", "who am i",
    "mera naam kya hai", "میرا نام کیا ہے",
]

GENERAL_REMEMBER_PATTERN = r"(?:remember|yaad rakho|yaad rakhna)(?: that| ke)? (.+?) (?:is|hai) (.+)"
GENERAL_RECALL_PATTERN = r"(.+?) kya (?:hai|tha)\??$"


def remember_name(command):
    for pattern in NAME_PATTERNS:
        m = re.search(pattern, command, re.IGNORECASE)
        if m:
            name = m.group(1).strip().rstrip(".؟?")
            memory["user_name"] = name
            save_memory()
            speak(f"Theek hai, main yaad rakhunga ke aapka naam {name} hai.")
            return True
    return False


def recall_name(command):
    if any(trigger in command for trigger in NAME_RECALL_TRIGGERS):
        name = memory.get("user_name")
        if name:
            speak(f"Aapka naam {name} hai.")
        else:
            speak("Mujhe abhi tak pata nahi ke aapka naam kya hai. Aap mujhe bata sakte hain: my name is Ali.")
        return True
    return False


def remember_general_fact(command):
    m = re.search(GENERAL_REMEMBER_PATTERN, command, re.IGNORECASE)
    if m:
        key = m.group(1).strip().lower()
        value = m.group(2).strip().rstrip(".؟?")
        memory.setdefault("facts", {})[key] = value
        save_memory()
        speak(f"Theek hai, main yaad rakhunga ke {key} {value} hai.")
        return True
    return False


def recall_general_fact(command):
    m = re.search(GENERAL_RECALL_PATTERN, command, re.IGNORECASE)
    if m:
        key = m.group(1).strip().lower()
        value = memory.get("facts", {}).get(key)
        if value:
            speak(f"{key} {value} hai.")
            return True
        # Not a real known-fact question — let it fall through to the normal router
        return False
    return False


# ---------------------------------------------------------------------------
# Command router — add new tasks here over time
# ---------------------------------------------------------------------------

def handle_command(command):
    if not command:
        return True

    # "stop listening" must be checked before generic "stop"/volume-down style words,
    # and "cancel shutdown/restart" must be checked before the general exit words.
    if command.strip() in ("exit", "quit", "goodbye") or "stop listening" in command:
        speak("Goodbye.")
        return False

    try:
        if remember_name(command):
            pass
        elif recall_name(command):
            pass
        elif remember_general_fact(command):
            pass
        elif recall_general_fact(command):
            pass
        elif command.startswith("schedule "):
            schedule_ads(command)
        elif "weather" in command:
            check_weather(command)
        elif command.startswith("message ") or command.startswith("whatsapp "):
            send_whatsapp_message(command)
        elif command.startswith("close ") or command.startswith("quit "):
            if not close_app(command):
                speak("Say it like: close chrome.")
        elif "screenshot" in command:
            take_screenshot(command)
        elif any(w in command for w in ["wifi password", "wi-fi password", "wifi ka password",
                                         "network password", "wifi ki password"]):
            get_wifi_password(command)
        elif "battery" in command or "cpu" in command or "system status" in command or "memory usage" in command:
            system_status(command)
        elif any(w in command for w in ["volume", "mute"]):
            control_volume(command)
        elif any(w in command for w in ["shut down", "shutdown", "restart", "reboot", "lock the screen",
                                         "lock screen", "lock my", "sleep mode", "go to sleep",
                                         "cancel shutdown", "cancel restart"]):
            system_power(command)
        elif command.startswith("open website ") or command.startswith("go to "):
            open_website(command)
        elif "open" in command and open_app(command):
            pass
        elif "time" in command or "date" in command:
            tell_time_or_date(command)
        elif "search" in command or "google" in command:
            web_search(command)
        else:
            speak("I don't know that command yet. You can teach me by adding it to assistant.py.")
    except Exception as e:
        # A single bad command should never crash the whole assistant.
        print(f"Unexpected error handling command '{command}': {e}")
        speak("Something went wrong with that command, but I'm still here.")

    return True


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    name = config["assistant_name"]
    wake_enabled = config.get("wake_word_enabled", True)
    wake_word = config.get("wake_word", "jarvis")

    if wake_enabled:
        speak(f"{name} is on standby. Say '{wake_word}' any time to wake me up.")
    else:
        speak(f"{name} is online. Say a command, or say exit to quit.")

    running = True
    while running:
        try:
            if wake_enabled:
                remainder = listen_for_wake_word()
                if remainder is None:
                    break
                if remainder:
                    command = remainder
                else:
                    speak("Yes?")
                    command = listen()
            else:
                command = listen()
        except Exception as e:
            print(f"Microphone/listen error: {e}")
            if _on_status:
                _on_status("Idle")
            time.sleep(1)
            continue
        running = handle_command(command)


if __name__ == "__main__":
    main()
