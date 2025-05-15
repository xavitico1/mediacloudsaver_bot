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

@bot.message_handler(func=lambda message: "youtube.com" in message.text or "youtu.be" in message.text)
def list_video_details(message):
    url = message.text
    bot.reply_to(message, "Obteniendo opciones de calidad...")

    ydl_opts = {
        "format_sort": ["res:360", "res:480", "res:720", "res:1080"],
        "cookies-from-browser": "brave",  # Usa las cookies de Brave para autenticarse
        "listformats": True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = info.get("formats", [])
    keyboard = telebot.types.InlineKeyboardMarkup()
    target_resolutions = ["360p", "480p", "720p", "1080p"]

    for fmt in formats:
        resolution = fmt.get("resolution")
        format_id = fmt.get("format_id")
        ext = fmt.get("ext", "N/A")
        fps = fmt.get("fps", "N/A")
        audio_channels = fmt.get("audio_channels")

        # Solo opciones que tengan audio y las resoluciones deseadas
        if resolution in target_resolutions and audio_channels:
            details = f"{format_id} - {resolution} - {fps} FPS - {ext}"
            button = telebot.types.InlineKeyboardButton(details, callback_data=f"video_{format_id}")
            keyboard.add(button)

    if keyboard.keyboard:
        bot.send_message(message.chat.id, "Selecciona la calidad que deseas:", reply_markup=keyboard)
        user_choices[message.chat.id] = url
    else:
        bot.send_message(message.chat.id, "No se encontraron calidades compatibles.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("video_"))
def process_selection(call):
    format_id = call.data.split("_")[1]
    url = user_choices.get(call.message.chat.id)

    if not url:
        bot.send_message(call.message.chat.id, "Por favor, envía primero un enlace de YouTube.")
        return

    bot.send_message(call.message.chat.id, f"Preparando descarga en formato {format_id}, espera un momento...")

    output_filename = "video.mp4"

    ydl_opts = {
        "format": format_id,
        "outtmpl": output_filename,
        "cookies-from-browser": "brave"  # Usa cookies desde el navegador Brave
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except yt_dlp.utils.DownloadError:
            bot.send_message(call.message.chat.id, "Error: YouTube requiere autenticación. Verifica que Brave está abierto.")

    # Subimos el archivo a Telegram para que el usuario lo descargue
    if os.path.exists(output_filename):
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
