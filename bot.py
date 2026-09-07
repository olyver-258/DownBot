import os
import asyncio
import tempfile
import shutil
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")

# Guarda quais usuários já têm um download em andamento
usuarios_ocupados = set()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Me envie um link do Instagram ou TikTok e eu baixo o vídeo para você."
    )


def baixar_video(url, pasta_temp):
    ydl_options = {
        "format": "best",
        "quiet": True,
        "no_warnings": True,
        "outtmpl": os.path.join(pasta_temp, "video_%(id)s.%(ext)s"),
    }

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    return filename


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.effective_user.id

    # Aceita somente Instagram e TikTok
    if "instagram.com" not in url and "tiktok.com" not in url:
        await update.message.reply_text(
            "❌ Envie um link válido do Instagram ou TikTok."
        )
        return

    # Anti-spam: impede o mesmo usuário de iniciar vários downloads ao mesmo tempo
    if user_id in usuarios_ocupados:
        await update.message.reply_text(
            "⏳ Você já tem um vídeo sendo processado. Aguarde terminar."
        )
        return

    usuarios_ocupados.add(user_id)

    status_msg = await update.message.reply_text(
        "⏳ Processando vídeo... aguarde."
    )

    pasta_temp = tempfile.mkdtemp(prefix="bot_video_")

    try:
        loop = asyncio.get_running_loop()

        # Executa o yt-dlp fora da thread principal do bot
        filename = await loop.run_in_executor(
            None,
            baixar_video,
            url,
            pasta_temp
        )

        if not os.path.exists(filename):
            raise FileNotFoundError("Arquivo não encontrado após o download.")

        await status_msg.edit_text("📤 Enviando vídeo...")

        with open(filename, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption="✅ Aqui está seu vídeo!"
            )

        await status_msg.delete()

    except yt_dlp.utils.DownloadError as e:
        print(f"Erro yt-dlp: {e}")

        erro = str(e).lower()

        if (
            "private" in erro
            or "login required" in erro
            or "not available" in erro
            or "unavailable" in erro
        ):
            await status_msg.edit_text(
                "🔒 Não consegui acessar esse vídeo.\n\n"
                "Ele pode estar privado, removido ou exigir login."
            )
        else:
            await status_msg.edit_text(
                "❌ Não consegui baixar esse vídeo. "
                "Verifique o link e tente novamente."
            )

    except Exception as e:
        print(f"Erro inesperado: {e}")

        await status_msg.edit_text(
            "❌ Ocorreu um erro ao processar o vídeo. Tente novamente."
        )

    finally:
        # Remove somente os arquivos temporários do Railway
        # O vídeo já enviado no Telegram NÃO é apagado
        try:
            shutil.rmtree(pasta_temp, ignore_errors=True)
        except Exception as e:
            print(f"Erro ao limpar arquivos temporários: {e}")

        usuarios_ocupados.discard(user_id)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN não configurado.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND),
            download_video
        )
    )

    print("Bot rodando...")
    app.run_polling()

