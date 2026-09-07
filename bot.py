import os
import asyncio
import tempfile
import shutil
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    BotCommand
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")

usuarios_ocupados = {}
idiomas_usuarios = {}

TEXTOS = {
    "pt": {
        "start": "🌍 Escolha o seu idioma:",
        "welcome": "✅ Idioma definido para Português.\n\nEnvie um link do Instagram ou TikTok.",
        "invalid": "❌ Envie um link válido do Instagram ou TikTok.",
        "busy": "⏳ Você já tem um vídeo sendo processado. Aguarde terminar.",
        "processing": "⏳ Processando vídeo... aguarde.",
        "sending": "📤 Enviando vídeo...",
        "caption": "✅ Aqui está seu vídeo!",
        "private": "🔒 Não consegui acessar esse vídeo.\n\nEle pode estar privado, removido ou exigir login.",
        "error": "❌ Não consegui baixar esse vídeo. Verifique o link e tente novamente.",
        "unexpected": "❌ Ocorreu um erro ao processar o vídeo. Tente novamente.",
        "language": "🌍 Escolha o seu idioma:"
    },

    "en": {
        "start": "🌍 Choose your language:",
        "welcome": "✅ Language set to English.\n\nSend an Instagram or TikTok link.",
        "invalid": "❌ Send a valid Instagram or TikTok link.",
        "busy": "⏳ You already have a video being processed. Please wait.",
        "processing": "⏳ Processing video... please wait.",
        "sending": "📤 Sending video...",
        "caption": "✅ Here is your video!",
        "private": "🔒 I couldn't access this video.\n\nIt may be private, removed, or require login.",
        "error": "❌ I couldn't download this video. Check the link and try again.",
        "unexpected": "❌ An error occurred while processing the video. Please try again.",
        "language": "🌍 Choose your language:"
    },

    "fr": {
        "start": "🌍 Choisissez votre langue :",
        "welcome": "✅ Langue définie sur Français.\n\nEnvoyez un lien Instagram ou TikTok.",
        "invalid": "❌ Envoyez un lien Instagram ou TikTok valide.",
        "busy": "⏳ Une vidéo est déjà en cours de traitement. Veuillez patienter.",
        "processing": "⏳ Traitement de la vidéo... veuillez patienter.",
        "sending": "📤 Envoi de la vidéo...",
        "caption": "✅ Voici votre vidéo !",
        "private": "🔒 Je n'ai pas pu accéder à cette vidéo.\n\nElle peut être privée, supprimée ou nécessiter une connexion.",
        "error": "❌ Je n'ai pas pu télécharger cette vidéo. Vérifiez le lien et réessayez.",
        "unexpected": "❌ Une erreur s'est produite. Veuillez réessayer.",
        "language": "🌍 Choisissez votre langue :"
    },

    "es": {
        "start": "🌍 Elige tu idioma:",
        "welcome": "✅ Idioma configurado en Español.\n\nEnvía un enlace de Instagram o TikTok.",
        "invalid": "❌ Envía un enlace válido de Instagram o TikTok.",
        "busy": "⏳ Ya tienes un video en proceso. Espera a que termine.",
        "processing": "⏳ Procesando video... espera.",
        "sending": "📤 Enviando video...",
        "caption": "✅ ¡Aquí está tu video!",
        "private": "🔒 No pude acceder a este video.\n\nPuede ser privado, eliminado o requerir inicio de sesión.",
        "error": "❌ No pude descargar este video. Verifica el enlace e inténtalo de nuevo.",
        "unexpected": "❌ Ocurrió un error al procesar el video. Inténtalo de nuevo.",
        "language": "🌍 Elige tu idioma:"
    },

    "hi": {
        "start": "🌍 अपनी भाषा चुनें:",
        "welcome": "✅ भाषा हिन्दी पर सेट कर दी गई है।\n\nInstagram या TikTok लिंक भेजें।",
        "invalid": "❌ कृपया एक मान्य Instagram या TikTok लिंक भेजें।",
        "busy": "⏳ आपका एक वीडियो पहले से प्रोसेस हो रहा है। कृपया प्रतीक्षा करें।",
        "processing": "⏳ वीडियो प्रोसेस हो रहा है... कृपया प्रतीक्षा करें।",
        "sending": "📤 वीडियो भेजा जा रहा है...",
        "caption": "✅ आपका वीडियो यहाँ है!",
        "private": "🔒 मैं इस वीडियो तक पहुँच नहीं सका।\n\nयह निजी, हटाया गया या लॉगिन की आवश्यकता वाला हो सकता है।",
        "error": "❌ वीडियो डाउनलोड नहीं हो सका। लिंक जाँचें और फिर कोशिश करें।",
        "unexpected": "❌ वीडियो प्रोसेस करते समय त्रुटि हुई। फिर कोशिश करें।",
        "language": "🌍 अपनी भाषा चुनें:"
    },

    "ar": {
        "start": "🌍 اختر لغتك:",
        "welcome": "✅ تم اختيار اللغة العربية.\n\nأرسل رابط Instagram أو TikTok.",
        "invalid": "❌ أرسل رابط Instagram أو TikTok صالحًا.",
        "busy": "⏳ لديك فيديو قيد المعالجة بالفعل. يرجى الانتظار.",
        "processing": "⏳ جارٍ معالجة الفيديو... يرجى الانتظار.",
        "sending": "📤 جارٍ إرسال الفيديو...",
        "caption": "✅ إليك الفيديو!",
        "private": "🔒 لم أتمكن من الوصول إلى هذا الفيديو.\n\nقد يكون خاصًا أو محذوفًا أو يتطلب تسجيل الدخول.",
        "error": "❌ لم أتمكن من تنزيل هذا الفيديو. تحقق من الرابط وحاول مرة أخرى.",
        "unexpected": "❌ حدث خطأ أثناء معالجة الفيديو. حاول مرة أخرى.",
        "language": "🌍 اختر لغتك:"
    }
}


def teclado_idiomas():
    return ReplyKeyboardMarkup(
        [
            ["🇵🇹 Português", "🇬🇧 English"],
            ["🇫🇷 Français", "🇪🇸 Español"],
            ["🇮🇳 हिन्दी", "🇸🇦 العربية"]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇵🇹 Português", callback_data="lang_pt"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ],
        [
            InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr"),
            InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
        ],
        [
            InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi"),
            InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
        ]
    ])


def obter_idioma(user_id):
    return idiomas_usuarios.get(user_id, "pt")

async def configurar_menu(app):
    comandos = [
        BotCommand("start", "🚀 Iniciar o bot"),
        BotCommand("language", "🌍 Mudar idioma"),
    ]

    await app.bot.set_my_commands(comandos)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 Escolha o seu idioma / Choose your language:",
        reply_markup=teclado_idiomas()
    )


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 Escolha o seu idioma / Choose your language:",
        reply_markup=teclado_idiomas()
    )


async def selecionar_idioma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    escolha = update.message.text
    user_id = update.effective_user.id

    idiomas = {
        "🇵🇹 Português": "pt",
        "🇬🇧 English": "en",
        "🇫🇷 Français": "fr",
        "🇪🇸 Español": "es",
        "🇮🇳 हिन्दी": "hi",
        "🇸🇦 العربية": "ar"
    }

    idioma = idiomas.get(escolha)

    if not idioma:
        return

    idiomas_usuarios[user_id] = idioma

    await update.message.reply_text(
        TEXTOS[idioma]["welcome"],
        reply_markup=ReplyKeyboardRemove()
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

    idioma = obter_idioma(user_id)
    t = TEXTOS[idioma]

    if "instagram.com" not in url and "tiktok.com" not in url:
        await update.message.reply_text(t["invalid"])
        return

    agora = asyncio.get_running_loop().time()
    bloqueio = usuarios_ocupados.get(user_id)

    if bloqueio:
        _, inicio = bloqueio

        if agora - inicio < 300:
            await update.message.reply_text(t["busy"])
            return

    request_token = object()
    usuarios_ocupados[user_id] = (request_token, agora)

    status_msg = await update.message.reply_text(
        t["processing"]
    )

    pasta_temp = tempfile.mkdtemp(prefix="bot_video_")

    try:
        loop = asyncio.get_running_loop()

        filename = await loop.run_in_executor(
            None,
            baixar_video,
            url,
            pasta_temp
        )

        if not os.path.exists(filename):
            raise FileNotFoundError("Arquivo não encontrado após o download.")

        await status_msg.edit_text(t["sending"])

        with open(filename, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=t["caption"]
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
            await status_msg.edit_text(t["private"])
        else:
            await status_msg.edit_text(t["error"])

    except Exception as e:
        print(f"Erro inesperado: {e}")
        await status_msg.edit_text(t["unexpected"])

    finally:
        shutil.rmtree(pasta_temp, ignore_errors=True)

        bloqueio_atual = usuarios_ocupados.get(user_id)

        if bloqueio_atual and bloqueio_atual[0] is request_token:
            usuarios_ocupados.pop(user_id, None)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN não configurado.")

    app = ApplicationBuilder().token(TOKEN).post_init(configurar_menu).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("language", language))

    app.add_handler(
        MessageHandler(
            filters.Regex(r"^(🇵🇹 Português|🇬🇧 English|🇫🇷 Français|🇪🇸 Español|🇮🇳 हिन्दी|🇸🇦 العربية)$"),
            selecionar_idioma
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND),
            download_video
        )
    )

    print("Bot rodando...")
    app.run_polling()


