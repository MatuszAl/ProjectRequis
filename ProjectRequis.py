import cv2
import mediapipe as mp
import pyautogui
import math
import time
import threading
import speech_recognition as sr
import subprocess
import openai
import urllib.parse
import webbrowser
import pyttsx3



# puautogui setup
pyautogui.FAILSAFE = False
screen_w, screen_h = pyautogui.size()

# MediaPipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1,
                       min_detection_confidence=0.7, min_tracking_confidence=0.7)

#pyTTsx3 setup
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Speed of speech
engine.setProperty('volume', 1)  # Volume (0.0 to 1.0)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Smoothing
prev_x, prev_y = 0, 0
smooth_factor = 2

# Gesture states
is_drawing = False
last_right_click = 0
last_double_click_time = 0
click_interval = 0.75

# Margins
x_margin, y_margin = 0.0, 0.0

# Distance between 2 landmarks
def dist(a, b):
    return ((a.x - b.x)**2 + (a.y - b.y)**2)**0.5

# Voice Command Actions
def paint():
    print("Opening Paint.")
    speak("Opening Paint.")
    subprocess.Popen('mspaint')
    
def text():
    print("Opening Notepad.")
    speak("Opening Notepad.")
    subprocess.Popen('notepad')

def speak(text):
    print(f"[TTS] {text}")
    engine.say(text)
    engine.runAndWait()

def browse_with_voice():
    # Initialize recognizer
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("Please say your search query:")
        #speak("What would you like to search for?")
        
        # Adjust for ambient noise and listen to the user's speech
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
        
        try:
            # Recognize speech using Google's speech recognition
            print("Recognizing...")
            search_query = recognizer.recognize_google(audio)
            print(f"You said: {search_query}")

            # URL encode the search query
            encoded_query = urllib.parse.quote(search_query)

            # Create the Google search URL
            search_url = f"https://www.google.com/search?q={encoded_query}"

            # Open the browser with the search URL
            webbrowser.open(search_url)
            print("Opening browser with your search results...")

            speak(f"Opening browser with your search results for {search_query}.")
            
        except sr.UnknownValueError:
            print("I couldn't understand your speech.")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")

# Background Voice Listener
def voice_listener():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        speak("Initializing voice commands...")
        print("Calibrating mic...")
        recognizer.adjust_for_ambient_noise(source, duration=2)

    while True:
        try:
            with mic as source:
                #print("Listening...")
                audio = recognizer.listen(source, timeout=2.5, phrase_time_limit=2.5)
            #print("Recognizing...")
            command = recognizer.recognize_google(audio).lower()
            print(f"You said: {command}")  # This prints what the microphone hears

            # Action trigger for "paint"
            if "scribble" in command:
                paint()
             
            # Action trigger for "text"    
            if "text" in command:
                text()

            # Action trigger for "browse"
            if "search" in command:
                browse_with_voice()
            
        except sr.WaitTimeoutError:
            print("No speech detected.")
        except sr.UnknownValueError:
            print("Didn't understand.")
        except sr.RequestError as e:
            print(f"API Error: {e}")

# Start voice listener in background
threading.Thread(target=voice_listener, daemon=True).start()

# Main Gesture Loop
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        hand = results.multi_hand_landmarks[0]
        lm = hand.landmark

        thumb = lm[4]
        index = lm[8]
        middle = lm[12]
        ring = lm[16]
        pinky = lm[20]

        # Cursor follows index finger
        x = int((ring.x - x_margin) / (1 - 2 * x_margin) * screen_w)
        y = int((ring.y - y_margin) / (1 - 2 * y_margin) * screen_h)
        x = max(0, min(screen_w - 1, x))
        y = max(0, min(screen_h - 1, y))

        smooth_x = prev_x + (x - prev_x) // smooth_factor
        smooth_y = prev_y + (y - prev_y) // smooth_factor
        pyautogui.moveTo(smooth_x, smooth_y)
        prev_x, prev_y = smooth_x, smooth_y

        current_time = time.time()

        #Drawing mode (thumb + index pinch)
        if dist(thumb, index) < 0.035 and not is_drawing:
            pyautogui.mouseDown()
            is_drawing = True
        elif dist(thumb, index) >= 0.045 and is_drawing:
            pyautogui.mouseUp()
            is_drawing = False

        # Double Click (thumb + middle)
        if dist(thumb, middle) < 0.035:
            if current_time - last_double_click_time > click_interval:
                pyautogui.doubleClick()
                last_double_click_time = current_time

        # Right Click (thumb + pinky)
        if dist(thumb, pinky) < 0.035 and current_time - last_right_click > click_interval:
            pyautogui.click(button='right')
            last_right_click = current_time

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
