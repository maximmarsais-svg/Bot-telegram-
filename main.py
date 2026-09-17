import os
import asyncio
import psycopg2
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- SERVEUR KEEP-ALIVE POUR RENDER ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
    server.serve_forever()

# --- CONNEXION BASE DE DONNÉES SUPABASE ---
DB_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DB_URL)

def save_media_to_db(password, media_list):
    conn = get_db_connection()
    cur = conn.cursor()
    for item in media_list:
        cur.execute(
            "INSERT INTO vault (password, file_type, file_id) VALUES (%s, %s, %s)",
            (password, item["type"], item["id"])
        )
    conn.commit()
    cur.close()
    conn.close()

def get_media_from_db(password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT file_type, file_id FROM vault WHERE password = %s ORDER BY id ASC", (password,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"type": row[0], "id": row[1]} for row in rows]

# --- COMMANDES TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔒 **Coffre-fort Illimité & Permanent**\n\n"
        "1. Envoie tes photos/vidéos (par paquets de 10, 50 ou 100).\n"
        "2. Tape `/save MOT_DE_PASSE` pour tout enregistrer.\n"
        "3. Tape `/get MOT_DE_PASSE` pour récupérer tes médias."
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "user_queue" not in context.user_data:
        context.user_data["user_queue"] = []

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data["user_queue"].append({"type": "photo", "id": file_id})
    elif update.message.video:
        file_id = update.message.video.file_id
        context.user_data["user_queue"].append({"type": "video", "id": file_id})

async def save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Précise un mot de passe : `/save MON_CODE`")
        return

    password = context.args[0]
    queue = context.user_data.get("user_queue", [])

    if not queue:
        await update.message.reply_text("⚠️ Aucune photo/vidéo en attente. Envoie-les d'abord !")
        return

    # Sauvegarde dans Supabase
    save_media_to_db(password, queue)
    
    added = len(queue)
    context.user_data["user_queue"] = []

    all_media = get_media_from_db(password)
    total = len(all_media)

    await update.message.reply_text(
        f"✅ **{added} fichier(s)** ajouté(s) en base !\n"
        f"📁 Total enregistré pour le code `{password}` : **{total} fichier(s)**."
    )

async def get_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Précise le mot de passe : `/get MON_CODE`")
        return

    password = context.args[0]
    items = get_media_from_db(password)

    if not items:
        await update.message.reply_text("❌ Aucun fichier trouvé pour ce mot de passe.")
        return

    await update.message.reply_text(f"📦 Envoi de {len(items)} fichier(s)...")

    for item in items:
        try:
            if item["type"] == "photo":
                await update.message.reply_photo(photo=item["id"])
            elif item["type"] == "video":
                await update.message.reply_video(video=item["id"])
            await asyncio.sleep(0.3)  # Évite les blocages anti-spam
        except Exception as e:
            print(f"Erreur d'envoi : {e}")

# --- DÉMARRAGE ---
def main():
    Thread(target=run_http_server, daemon=True).start()

    token = os.environ.get("BOT_TOKEN")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("save", save_cmd))
    app.add_handler(CommandHandler("get", get_cmd))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

    print("Le bot démarre...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
