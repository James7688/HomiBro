# Homibro Assistant (with GPT-Neo integration using Transformers)

import tkinter as tk
import pyttsx3
import random
import threading
import speech_recognition as sr
from pygame import mixer
import os, requests, json
from bs4 import BeautifulSoup
from PIL import ImageTk, Image
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# ========== SETUP ==========

# Text-to-Speech Engine
engine = pyttsx3.init()
def speak(text):
    engine.say(text)
    engine.runAndWait()

# Load GPT-Neo Model (CPU-friendly)
model_name = "EleutherAI/gpt-neo-1.3B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token  # Fix pad_token warning
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float32)

# Chat memory
chat_history = []

def chat(prompt):
    full_prompt = "The following is a conversation between a user and an assistant. The assistant is helpful, friendly, and informative.\n"
    for i in range(0, len(chat_history), 2):
        full_prompt += f"User: {chat_history[i]}\n"
        if i + 1 < len(chat_history):
            full_prompt += f"Assistant: {chat_history[i + 1]}\n"
    full_prompt += f"User: {prompt}\nAssistant:"

    input_ids = tokenizer.encode(full_prompt, return_tensors="pt", truncation=True, max_length=1024)
    attention_mask = (input_ids != tokenizer.pad_token_id).long()
    output_ids = model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=100,
        do_sample=True,
        temperature=0.8,
        top_p=0.95
    )
    output_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    response = output_text[len(full_prompt):].strip().split("\n")[0]
    return response

# Jokes
jokes = [
    "Why did the computer show up at work late? It had a hard drive.",
    "I'm not a real monkey, but I sure like monkeying around!",
    "My battery life is better than yours. Wait... nevermind.",
    "I used to be a search bar, but I got promoted!"
]

# Initialize mixer
mixer.init()

# ========== MEMORY ==========
memory_file = "homibro_memory.json"
def load_memory():
    if os.path.exists(memory_file):
        with open(memory_file, "r") as f:
            return json.load(f)
    return {}

def save_memory():
    with open(memory_file, "w") as f:
        json.dump(memory, f)

memory = load_memory()

# ========== GUI ==========
root = tk.Tk()
root.title("Homibro")
root.geometry("430x650")
root.resizable(False, False)

canvas = tk.Canvas(root)
scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

scrollable_frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

# Idle Image
idle_image = ImageTk.PhotoImage(Image.open("sprites/idle1.jpg"))
image_label = tk.Label(scrollable_frame, image=idle_image)
image_label.pack(pady=10)

# Chat history display
chat_history_box = tk.Text(scrollable_frame, height=15, width=50, wrap="word")
chat_history_box.pack(pady=5)
chat_history_box.config(state="disabled")

# Chatbox
chat_frame = tk.Frame(scrollable_frame)
chat_frame.pack(pady=5)
chat_entry = tk.Entry(chat_frame, width=35)
chat_entry.pack(side=tk.LEFT, padx=5)

# ========== FUNCTIONS ==========

def append_to_chat(sender, message):
    chat_history_box.config(state="normal")
    chat_history_box.insert(tk.END, f"{sender}: {message}\n")
    chat_history_box.config(state="disabled")
    chat_history_box.see(tk.END)

def update_display(text):
    text_display.config(text=text)
    speak(text)

def tell_joke():
    joke = random.choice(jokes)
    append_to_chat("Homibro", joke)
    speak(joke)

def on_chat_submit():
    user_input = chat_entry.get()
    chat_entry.delete(0, tk.END)
    threading.Thread(target=lambda: smart_command(user_input)).start()

def intro():
    if "name" in memory:
        msg = f"Welcome back, {memory['name']}! I'm Homibro, your assistant."
        append_to_chat("Homibro", msg)
        speak(msg)
    else:
        msg = "Hi! I'm Homibro. What's your name?"
        append_to_chat("Homibro", msg)
        def ask_name():
            user_name = chat_entry.get()
            chat_entry.delete(0, tk.END)
            memory['name'] = user_name
            save_memory()
            response = f"Nice to meet you, {user_name}!"
            append_to_chat("Homibro", response)
            speak(response)
            chat_button.config(command=on_chat_submit)
        chat_button.config(command=ask_name)

def smart_web_search(query):
    url = f"https://www.google.com/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "lxml")
    try:
        result = soup.select_one(".BNeawe").text
    except:
        result = "Sorry, I couldn't find a quick answer."
    append_to_chat("Homibro", result)
    speak(result)

def sing_song():
    folder = "music"
    if not os.path.exists(folder):
        os.makedirs(folder)
        msg = "Your music folder is empty. Add some MP3 files so I can sing for you!"
        append_to_chat("Homibro", msg)
        speak(msg)
        return
    songs = [f for f in os.listdir(folder) if f.endswith(".mp3")]
    if not songs:
        msg = "Your music folder has no MP3 files."
        append_to_chat("Homibro", msg)
        speak(msg)
        return
    song = random.choice(songs)
    msg = f"Singing {song.replace('.mp3','').replace('-',' ').title()}!"
    append_to_chat("Homibro", msg)
    speak(msg)
    mixer.music.load(os.path.join(folder, song))
    mixer.music.play()

def smart_command(text):
    append_to_chat("You", text)
    text = text.strip()
    if not text:
        return

    if "joke" in text:
        tell_joke()
        return
    elif "sing" in text or "song" in text:
        sing_song()
        return

    append_to_chat("Homibro", "Typing...")
    try:
        response = chat(text)
        if not response or len(response.strip()) < 2 or "sorry" in response.lower():
            raise ValueError("Bad or unclear response from model.")
        chat_history.append(text)
        chat_history.append(response)
    except Exception as e:
        try:
            result = "Let me look that up..."
            append_to_chat("Homibro", result)
            speak(result)
            response = None
            smart_web_search(text)
            return
        except:
            response = f"I'm having trouble thinking right now: {e}"

    if response:
        append_to_chat("Homibro", response)
        speak(response)

def listen_to_user():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        speak("I'm listening...")
        audio = recognizer.listen(source)
    try:
        user_input = recognizer.recognize_google(audio)
        smart_command(user_input)
    except:
        speak("Sorry, I didn't catch that. Try again.")

# ========== GUI Buttons ==========

text_display = tk.Label(scrollable_frame, text="Initializing Homibro...", wraplength=380, justify="center")
text_display.pack(pady=5)

tk.Button(scrollable_frame, text="Introduce", command=intro).pack(pady=5)
tk.Button(scrollable_frame, text="Tell a Joke", command=tell_joke).pack(pady=5)
tk.Button(scrollable_frame, text="Sing a Song", command=sing_song).pack(pady=5)
tk.Button(scrollable_frame, text="Speak Command", command=lambda: threading.Thread(target=listen_to_user).start()).pack(pady=10)

chat_button = tk.Button(chat_frame, text="Send", command=on_chat_submit)
chat_button.pack(side=tk.RIGHT)

intro()
root.mainloop()
