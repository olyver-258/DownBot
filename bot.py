import os
import re
import asyncio
import tempfile
import shutil
from pathlib import Path

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    BotCommand,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

import yt_dlp


# =========================================================
# CONFIGURAÇÃO
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Telegram Bot API normalmente limita uploads de bots.
# Mantemos margem de segurança.
MAX_FILE_SIZE = 49 * 1024 * 1024

# user_id -> (token_da_requisicao, horario_inicio)
usuarios_ocupados = {}

# user_id -> idioma
idiomas_usuarios = {}


# =========================================================
# TEXTOS / IDIOMAS
# =========================================================

TEXTOS = {
    "pt": {
        "start": "🌍 Escolha o seu idioma:",
        "welcome": (
            "✅ Idioma definido para Português.\n\n"
            "Envie um link do Instagram, TikTok ou Facebook e Twitter/X."
        ),
        "invalid": (
            "❌ Envie um link válido do Instagram, TikTok ou Facebook e Twitter/X."
        ),
        "busy": (
            "⏳ Você já tem um vídeo sendo processado. Aguarde terminar."
        ),
        "processing": "⏳ Processando vídeo... aguarde.",
        "sending": "📤 Enviando vídeo...",
        "caption": "✅ Aqui está seu vídeo!",
        "private": (
            "🔒 Não consegui acessar esse vídeo.\n\n"
            "Ele pode estar privado, removido, indisponível ou exigir login."
        ),
        "too_large": (
            "⚠️ O vídeo é grande demais para ser enviado pelo bot."
        ),
        "error": (
            "❌ Não consegui baixar esse vídeo. "
            "Verifique o link e tente novamente."
        ),
        "unexpected": (
            "❌ Ocorreu um erro ao processar o vídeo. Tente novamente."
        ),
        "language": "🌍 Escolha o seu idioma:",
    },

    "en": {
        "start": "🌍 Choose your language:",
        "welcome": (
            "✅ Language set to English.\n\n"
            "Send an Instagram, TikTok or Facebook e Twitter/X link."
        ),
        "invalid": (
            "❌ Send a valid Instagram, TikTok or Facebook e Twitter/X link."
        ),
        "busy": (
            "⏳ You already have a video being processed. Please wait."
        ),
        "processing": "⏳ Processing video... please wait.",
        "sending": "📤 Sending video...",
        "caption": "✅ Here is your video!",
        "private": (
            "🔒 I couldn't access this video.\n\n"
            "It may be private, removed, unavailable, or require login."
        ),
        "too_large": (
            "⚠️ This video is too large to be sent by the bot."
        ),
        "error": (
            "❌ I couldn't download this video. "
            "Check the link and try again."
        ),
        "unexpected": (
            "❌ An error occurred while processing the video. Please try again."
        ),
        "language": "🌍 Choose your language:",
    },

    "fr": {
        "start": "🌍 Choisissez votre langue :",
        "welcome": (
            "✅ Langue définie sur Français.\n\n"
            "Envoyez un lien Instagram, TikTok ou Facebook e Twitter/X."
        ),
        "invalid": (
            "❌ Envoyez un lien Instagram, TikTok ou Facebook e Twitter/X valide."
        ),
        "busy": (
            "⏳ Une vidéo est déjà en cours de traitement. Veuillez patienter."
        ),
        "processing": "⏳ Traitement de la vidéo... veuillez patienter.",
        "sending": "📤 Envoi de la vidéo...",
        "caption": "✅ Voici votre vidéo !",
        "private": (
            "🔒 Je n'ai pas pu accéder à cette vidéo.\n\n"
            "Elle peut être privée, supprimée, indisponible "
            "ou nécessiter une connexion."
        ),
        "too_large": (
            "⚠️ Cette vidéo est trop volumineuse pour être envoyée par le bot."
        ),
        "error": (
            "❌ Je n'ai pas pu télécharger cette vidéo. "
            "Vérifiez le lien et réessayez."
        ),
        "unexpected": (
            "❌ Une erreur s'est produite lors du traitement de la vidéo. "
            "Veuillez réessayer."
        ),
        "language": "🌍 Choisissez votre langue :",
    },

    "es": {
        "start": "🌍 Elige tu idioma:",
        "welcome": (
            "✅ Idioma configurado en Español.\n\n"
            "Envía un enlace de Instagram, TikTok o Facebook e Twitter/X."
        ),
        "invalid": (
            "❌ Envía un enlace válido de Instagram, TikTok o Facebook e Twitter/X."
        ),
        "busy": (
            "⏳ Ya tienes un video en proceso. Espera a que termine."
        ),
        "processing": "⏳ Procesando video... espera.",
        "sending": "📤 Enviando video...",
        "caption": "✅ ¡Aquí está tu video!",
        "private": (
            "🔒 No pude acceder a este video.\n\n"
            "Puede ser privado, eliminado, no disponible "
            "o requerir inicio de sesión."
        ),
        "too_large": (
            "⚠️ Este video es demasiado grande para enviarlo con el bot."
        ),
        "error": (
            "❌ No pude descargar este video. "
            "Verifica el enlace e inténtalo de nuevo."
        ),
        "unexpected": (
            "❌ Ocurrió un error al procesar el video. Inténtalo de nuevo."
        ),
        "language": "🌍 Elige tu idioma:",
    },

    "hi": {
        "start": "🌍 अपनी भाषा चुनें:",
        "welcome": (
            "✅ भाषा हिन्दी पर सेट कर दी गई है।\n\n"
            "Instagram, TikTok या Facebook e Twitter/X लिंक भेजें।"
        ),
        "invalid": (
            "❌ कृपया एक मान्य Instagram, TikTok या Facebook e Twitter/X लिंक भेजें।"
        ),
        "busy": (
            "⏳ आपका एक वीडियो पहले से प्रोसेस हो रहा है। कृपया प्रतीक्षा करें।"
        ),
        "processing": "⏳ वीडियो प्रोसेस हो रहा है... कृपया प्रतीक्षा करें।",
        "sending": "📤 वीडियो भेजा जा रहा है...",
        "caption": "✅ आपका वीडियो यहाँ है!",
        "private": (
            "🔒 मैं इस वीडियो तक पहुँच नहीं सका।\n\n"
            "यह निजी, हटाया गया, अनुपलब्ध या लॉगिन की आवश्यकता वाला हो सकता है।"
        ),
        "too_large": (
            "⚠️ यह वीडियो बॉट द्वारा भेजने के लिए बहुत बड़ा है।"
        ),
        "error": (
            "❌ वीडियो डाउनलोड नहीं हो सका। लिंक जाँचें और फिर कोशिश करें।"
        ),
        "unexpected": (
            "❌ वीडियो प्रोसेस करते समय त्रुटि हुई। फिर कोशिश करें।"
        ),
        "language": "🌍 अपनी भाषा चुनें:",
    },

    "ar": {
        "start": "🌍 اختر لغتك:",
        "welcome": (
            "✅ تم اختيار اللغة العربية.\n\n"
            "أرسل رابط Instagram أو TikTok أو Facebook e Twitter/X."
        ),
        "invalid": (
            "❌ أرسل رابط Instagram أو TikTok أو Facebook e Twitter/X صالحًا."
        ),
        "busy": (
            "⏳ لديك فيديو قيد المعالجة بالفعل. يرجى الانتظار."
        ),
        "processing": "⏳ جارٍ معالجة الفيديو... يرجى الانتظار.",
        "sending": "📤 جارٍ إرسال الفيديو...",
        "caption": "✅ إليك الفيديو!",
        "private": (
            "🔒 لم أتمكن من الوصول إلى هذا الفيديو.\n\n"
            "قد يكون خاصًا أو محذوفًا أو غير متاح أو يتطلب تسجيل الدخول."
        ),
        "too_large": (
            "⚠️ حجم هذا الفيديو كبير جدًا ولا يمكن للبوت إرساله."
        ),
        "error": (
            "❌ لم أتمكن من تنزيل هذا الفيديو. "
            "تحقق من الرابط وحاول مرة أخرى."
        ),
        "unexpected": (
            "❌ حدث خطأ أثناء معالجة الفيديو. حاول مرة أخرى."
        ),
        "language": "🌍 اختر لغتك:",
    },
}


# =========================================================
# IDIOMAS / MENU
# =========================================================

def teclado_idiomas():
    return ReplyKeyboardMarkup(
        [
            ["🇵🇹 Português", "🇬🇧 English"],
            ["🇫🇷 Français", "🇪🇸 Español"],
            ["🇮🇳 हिन्दी", "🇸🇦 العربية"],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def obter_idioma(user_id):
    return idiomas_usuarios.get(user_id, "pt")


async def configurar_menu(app):
    comandos = [
        BotCommand("start", "🚀 Iniciar o bot"),
        BotCommand("language", "🌍 Mudar idioma"),
    ]

    await app.bot.set_my_commands(comandos)


# =========================================================
# COMANDOS ADMINISTRATIVOS
# =========================================================

async def manutencao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    enviados = 0
    falhas = 0

    for user_id in list(idiomas_usuarios.keys()):
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🛠️ O bot está em manutenção para melhorias e correções. "
                    "Voltaremos em breve! 🚀"
                ),
            )
            enviados += 1
        except Exception as e:
            print(f"Erro ao avisar {user_id}: {e}")
            falhas += 1

    await update.message.reply_text(
        f"📢 Aviso enviado!\n"
        f"✅ Enviados: {enviados}\n"
        f"❌ Falhas: {falhas}"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "📊 Estatísticas do bot\n\n"
        f"👥 Usuários nesta sessão: {len(idiomas_usuarios)}\n"
        f"⏳ Downloads ativos: {len(usuarios_ocupados)}"
    )


async def meu_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 Seu Telegram User ID é: {update.effective_user.id}"
    )


# =========================================================
# /START E /LANGUAGE
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 Escolha o seu idioma / Choose your language:",
        reply_markup=teclado_idiomas(),
    )


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 Escolha o seu idioma / Choose your language:",
        reply_markup=teclado_idiomas(),
    )


async def selecionar_idioma(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    escolha = update.message.text
    user_id = update.effective_user.id

    idiomas = {
        "🇵🇹 Português": "pt",
        "🇬🇧 English": "en",
        "🇫🇷 Français": "fr",
        "🇪🇸 Español": "es",
        "🇮🇳 हिन्दी": "hi",
        "🇸🇦 العربية": "ar",
    }

    idioma = idiomas.get(escolha)

    if not idioma:
        return

    idiomas_usuarios[user_id] = idioma

    await update.message.reply_text(
        TEXTOS[idioma]["welcome"],
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================================
# LINKS
# =========================================================

def extrair_url(texto):
    if not texto:
        return None

    match = re.search(r"https?://[^\s]+", texto)

    if not match:
        return None

    # Remove sinais que às vezes ficam colados no fim do link.
    return match.group(0).rstrip(".,;!?)]}>'\"")


def identificar_plataforma(url):
    url = url.lower()

    if "instagram.com" in url:
        return "instagram"

    if "tiktok.com" in url:
        return "tiktok"

    if "facebook.com" in url or "fb.watch" in url:
        return "facebook"

    if "twitter.com" in url or "x.com" in url:
        return "twitter"

    return None


# =========================================================
# DOWNLOAD COM YT-DLP
# =========================================================

def baixar_video(url, pasta_temp):
    ydl_options = {
        # Tenta priorizar MP4 sem exigir merge com ffmpeg.
        "format": "best",  
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 3,
        "restrictfilenames": True,
        "outtmpl": os.path.join(
            pasta_temp,
            "video_%(id)s.%(ext)s",
        ),
    }

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    legenda = info.get("description") or info.get("title") or ""

    # Caminho previsto pelo yt-dlp.
    if filename and os.path.exists(filename):
        return filename, legenda

    # Alguns sites podem alterar nome/extensão final.
    arquivos = [
        p for p in Path(pasta_temp).iterdir()
        if p.is_file()
        and not p.name.endswith(".part")
        and not p.name.endswith(".ytdl")
    ]

    if arquivos:
        # Se houver mais de um, usa o maior arquivo real.
        maior = max(arquivos, key=lambda p: p.stat().st_size)
        return str(maior), legenda

    raise FileNotFoundError(
        "Download concluído, mas nenhum arquivo final foi encontrado."
    )


# =========================================================
# RECEBER E PROCESSAR LINK
# =========================================================

async def download_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id
    idioma = obter_idioma(user_id)
    t = TEXTOS[idioma]

    url = extrair_url(update.message.text)
    plataforma = identificar_plataforma(url) if url else None

    if not url or not plataforma:
        await update.message.reply_text(t["invalid"])
        return

    agora = asyncio.get_running_loop().time()
    bloqueio = usuarios_ocupados.get(user_id)

    # Se houver bloqueio recente, não deixa iniciar outro download.
    if bloqueio:
        _, inicio = bloqueio

        if agora - inicio < 300:
            await update.message.reply_text(t["busy"])
            return

        # Bloqueio antigo/travado: remove.
        usuarios_ocupados.pop(user_id, None)

    request_token = object()
    usuarios_ocupados[user_id] = (request_token, agora)

    status_msg = await update.message.reply_text(
        t["processing"]
    )

    pasta_temp = tempfile.mkdtemp(prefix="bot_video_")
    video_enviado = False

    try:
        loop = asyncio.get_running_loop()

        filename, legenda = await loop.run_in_executor(
            None,
            baixar_video,
            url,
            pasta_temp,
        )

        caption_envio = (
            legenda
            if legenda and len(legenda) <= 1024
            else t["caption"]
        )

        if not os.path.exists(filename):
            raise FileNotFoundError(
                "Arquivo não encontrado após o download."
            )

        tamanho = os.path.getsize(filename)

        if tamanho > MAX_FILE_SIZE:
            await status_msg.edit_text(t["too_large"])
            return

        await status_msg.edit_text(t["sending"])

        with open(filename, "rb") as video_file:
            try:
                await update.message.reply_video(
                    video=video_file,
                    caption=caption_envio,
                    supports_streaming=True,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=60,
                    pool_timeout=60,
                )

            except Exception as erro_video:
                # Alguns arquivos são baixados corretamente, mas o Telegram
                # não os aceita como "vídeo". Nesse caso, tenta como documento.
                print(
                    f"Falha ao enviar como vídeo "
                    f"[{plataforma}]: {erro_video}"
                )

                video_file.seek(0)

                await update.message.reply_document(
                    document=video_file,
                    caption=caption_envio,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=60,
                    pool_timeout=60,
                )

        # Só marcamos como enviado depois que o Telegram confirmou o envio.
        video_enviado = True

        if legenda and len(legenda) > 1024:
            await update.message.reply_text(legenda)

        try:
            await status_msg.delete()
        except Exception as e:
            print(f"Erro ao apagar mensagem de status: {e}")

    except yt_dlp.utils.DownloadError as e:
        print(f"Erro yt-dlp [{plataforma}]: {e}")

        # Evita o falso erro caso o arquivo já tenha sido enviado.
        if video_enviado:
            return

        erro = str(e).lower()

        erros_privados = (
            "private",
            "login required",
            "sign in",
            "not available",
            "unavailable",
            "removed",
            "deleted",
            "members-only",
            "members only",
            "age-restricted",
        )

        if any(texto in erro for texto in erros_privados):
            try:
                await status_msg.edit_text(t["private"])
            except Exception:
                pass
        else:
            try:
                await status_msg.edit_text(t["error"])
            except Exception:
                pass

    except Exception as e:
        print(
            f"Erro inesperado [{plataforma}]: "
            f"{type(e).__name__}: {e}"
        )

        # Correção do problema antigo:
        # se o vídeo já foi enviado, não mostra uma mensagem de erro depois.
        if not video_enviado:
            try:
                await status_msg.edit_text(t["unexpected"])
            except Exception:
                pass

    finally:
        shutil.rmtree(
            pasta_temp,
            ignore_errors=True,
        )

        bloqueio_atual = usuarios_ocupados.get(user_id)

        if (
            bloqueio_atual
            and bloqueio_atual[0] is request_token
        ):
            usuarios_ocupados.pop(user_id, None)


# =========================================================
# INICIAR BOT
# =========================================================

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN não configurado.")

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(configurar_menu)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("language", language)
    )

    app.add_handler(
        CommandHandler("meuid", meu_id)
    )

    app.add_handler(
        CommandHandler("stats", stats)
    )

    app.add_handler(
        CommandHandler("manutencao", manutencao)
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"^(🇵🇹 Português|🇬🇧 English|🇫🇷 Français|"
                r"🇪🇸 Español|🇮🇳 हिन्दी|🇸🇦 العربية)$"
            ),
            selecionar_idioma,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND),
            download_video,
        )
    )

    print("Bot rodando...")
    print("Plataformas: Instagram | TikTok | Facebook | Twitter/X")

    app.run_polling(
        drop_pending_updates=True
    )
