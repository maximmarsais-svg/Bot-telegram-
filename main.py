import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

DATA_FILE = "vault_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Bienvenue sur le Coffre-fort Partagé !**\n\n"
        "📸 **Pour sauvegarder un média :**\n"
        "1. Transfère ou envoie des photos/vidéos au bot.\n"
        "2. Envoie la commande `/save MOT_DE_PASSE` juste après.\n\n"
        "🔓 **Pour récupérer des médias :**\n"
        "Envoie la commande `/get MOT_DE_PASSE`.",
        parse_mode="Markdown"
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.photo:
        file_id = msg.photo[-1].file_id
        file_type = "photo"
    elif msg.video:
        file_id = msg.video.file_id
        file_type = "video"
    else:
        return

    if "temp_media" not in context.user_data:
        context.user_data["temp_media"] = []
    
    context.user_data["temp_media"].append({"type": file_type, "file_id": file_id})
    count = len(context.user_data["temp_media"])
    await update.message.reply_text(f"📥 {count} média(s) reçu(s) ! Envoie `/save MOT_DE_PASSE` pour les verrouiller.")

async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "temp_media" not in context.user_data or not context.user_data["temp_media"]:
        await update.message.reply_text("⚠️ Envoie ou transfère d'abord des photos/vidéos au bot avant de faire `/save`.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Utilisation : `/save MON_MOT_DE_PASSE`")
        return

    password = context.args[0]
    media_list = context.user_data.pop("temp_media")

    data = load_data()
    if password not in data:
        data[password] = []

    data[password].extend(media_list)
    save_data(data)

    await update.message.reply_text(
        f"🔒 {len(media_list)} média(s) ajouté(s) au dossier verrouillé par le mot de passe : `{password}`",
        parse_mode="Markdown"
    )

async def retrieve_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Utilisation : `/get MON_MOT_DE_PASSE`")
        return

    password = context.args[0]
    data = load_data()

    if password not in data or not data[password]:
        await update.message.reply_text("❌ Aucun média trouvé pour ce mot de passe.")
        return

    await update.message.reply_text(f"🔓 Mot de passe correct ! Envoi des médias du dossier `{password}`...")
    for item in data[password]:
        if item["type"] == "photo":
            await update.message.reply_photo(photo=item["file_id"])
        elif item["type"] == "video":
            await update.message.reply_video(video=item["file_id"])

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("Erreur : BOT_TOKEN non défini.")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("save", save_media))
    app.add_handler(CommandHandler("get", retrieve_media))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

    app.run_polling()

if __name__ == "__main__":
    main()
  
