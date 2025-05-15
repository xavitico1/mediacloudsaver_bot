import telebot
import yt_dlp
import os
from flask import Flask

# Obtener el token desde las variables de entorno en Render
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# Diccionario para almacenar elecciones de calidad por usuario
user_choices = {}

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "¡Hola! Envíame un enlace de YouTube y te mostraré las opciones de descarga.")

@bot.message_handler(commands=["audio"])
def audio_mode(message):
    bot.reply_to(message, "Envíame un enlace de YouTube para descargar solo el audio.")

@bot.message_handler(func=lambda message: "youtube.com" in message.text or "youtu.be" in message.text)
def list_video_details(message):
    url = message.text
    bot.reply_to(message, "Obteniendo opciones de calidad...")

    ydl_opts = {"listformats": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = info.get("formats", [])
    keyboard = telebot.types.InlineKeyboardMarkup()

    for fmt in formats:
        if fmt.get("format_id") and fmt.get("resolution"):
            details = f"{fmt['format_id']} - {fmt['resolution']} - {fmt.get('fps', 'N/A')} FPS"
            button = telebot.types.InlineKeyboardButton(details, callback_data=f"video_{fmt['format_id']}")
            keyboard.add(button)

        if "audio" in fmt.get("format", "").lower():
            audio_details = f"{fmt['format_id']} - {fmt.get('abr', 'N/A')} kbps"
            button = telebot.types.InlineKeyboardButton(audio_details, callback_data=f"audio_{fmt['format_id']}")
            keyboard.add(button)

    bot.send_message(message.chat.id, "Selecciona la calidad que deseas:", reply_markup=keyboard)
    user_choices[message.chat.id] = url

@bot.callback_query_handler(func=lambda call: call.data.startswith("video_") or call.data.startswith("audio_"))
def process_selection(call):
    format_id = call.data.split("_")[1]
    url = user_choices.get(call.message.chat.id)

    if not url:
        bot.send_message(call.message.chat.id, "Por favor, envía primero un enlace de YouTube.")
        return

    bot.send_message(call.message.chat.id, f"Preparando descarga en formato {format_id}, espera un momento...")

    file_extension = "mp4" if call.data.startswith("video") else "mp3"
    output_filename = f"media.{file_extension}"

    ydl_opts = {
        "format": format_id,
        "outtmpl": output_filename
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Subimos el archivo a Telegram para que el usuario lo descargue cuando quiera
    with open(output_filename, "rb") as media_file:
        bot.send_document(call.message.chat.id, media_file)

    os.remove(output_filename)

# 🔧 Servidor HTTP falso para evitar errores en Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot funcionando en Render"

if __name__ == "__main__":
    from threading import Thread
    Thread(target=bot.polling).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
