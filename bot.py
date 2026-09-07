import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import yt_dlp

# Substitua pelo seu Token do BotFather
TOKEN = os.getenv("BOT_TOKEN")

# Configurações do yt-dlp para baixar a melhor qualidade sem áudio/vídeo separados
YDL_OPTIONS = {
    'format': 'best',
    'quiet': True,
    'no_warnings': True,
    'outtmpl': 'downloaded_%(id)s.%(ext)s',
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Me envie um link do Instagram ou TikTok e eu baixo o vídeo para você.")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    
    # Validação básica de URL
    if "instagram.com" not in url and "tiktok.com" not in url:
        await update.message.reply_text("Por favor, envie um link válido do Instagram ou TikTok.")
        return

    status_msg = await update.message.reply_text("Processando vídeo... aguarde.")

    try:
        # Extração da URL do vídeo usando yt-dlp
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # Envio do arquivo para o Telegram
        with open(filename, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption="Aqui está seu vídeo!")
        
        # Limpeza do arquivo local para não lotar o servidor
        os.remove(filename)
        await status_msg.delete()

    except Exception as e:
        print(f"Erro: {e}")
        await status_msg.edit_text("Ocorreu um erro ao baixar o vídeo. O link pode estar privado ou indisponível.")

if __name__ == '__main__':
    # Inicializa o bot
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), download_video))

    print("Bot rodando...")
    app.run_polling()

