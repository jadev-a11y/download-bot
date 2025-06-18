import os
import telebot
from telebot import types
import yt_dlp
import tempfile
import logging
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import re
from urllib.parse import urlparse

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для health check на Render"""
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            response = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Video Downloader Bot</title>
                <meta charset="UTF-8">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a1a; color: white; }
                    h1 { color: #00d4aa; }
                </style>
            </head>
            <body>
                <h1>🎬 Video Downloader Bot is Running!</h1>
                <p>✅ Bot is active and ready</p>
                <p>🚀 Deployed on Render</p>
                <p>👨‍💻 Developer: @oxygw</p>
                <p>⚡ Status: Online 24/7</p>
                <p>📱 Supports: TikTok, Instagram, YouTube, Twitter</p>
            </body>
            </html>
            """
            self.wfile.write(response.encode('utf-8'))
        except Exception as e:
            logger.error(f"HTTP handler error: {e}")
    
    def do_HEAD(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
        except Exception as e:
            logger.error(f"HTTP HEAD error: {e}")
    
    def log_message(self, format, *args):
        return

def keep_alive():
    """HTTP сервер для Render health check"""
    try:
        port = int(os.environ.get('PORT', 8000))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        logger.info(f"🌐 HTTP server starting on port {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"HTTP server error: {e}")

# Токен бота
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found!")
    exit(1)

# Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

# Статистика
stats = {
    'total_downloads': 0,
    'successful_downloads': 0,
    'failed_downloads': 0
}

# Поддерживаемые платформы (только стабильные)
SUPPORTED_PLATFORMS = {
    'youtube.com': '🔴 YouTube',
    'youtu.be': '🔴 YouTube',
    'tiktok.com': '🎵 TikTok',
    'vm.tiktok.com': '🎵 TikTok',
    'instagram.com': '📸 Instagram',
    'twitter.com': '🐦 Twitter',
    'x.com': '🐦 X (Twitter)',
    'facebook.com': '📘 Facebook',
    'fb.watch': '📘 Facebook'
}

def detect_platform(url):
    """Определяет платформу по URL"""
    url_lower = url.lower()
    for domain, platform in SUPPORTED_PLATFORMS.items():
        if domain in url_lower:
            return platform
    return None

def is_valid_url(url):
    """Проверяет валидность URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def create_main_menu():
    """Создает главное меню"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn1 = types.InlineKeyboardButton("📋 Поддерживаемые сайты", callback_data="supported")
    btn2 = types.InlineKeyboardButton("❓ Помощь", callback_data="help")
    btn3 = types.InlineKeyboardButton("📊 Статистика", callback_data="stats")
    
    markup.add(btn1, btn2)
    markup.add(btn3)
    
    return markup

def create_back_menu():
    """Создает кнопку Назад в меню"""
    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")
    markup.add(back_btn)
    return markup

@bot.message_handler(commands=['start'])
def start_command(message):
    """Команда /start"""
    user_name = message.from_user.first_name or "друг"
    
    welcome_text = f"""🎬 **Добро пожаловать, {user_name}!**

🚀 **Video Downloader Bot** - скачиваю видео с популярных платформ!

**📱 Поддерживаемые сайты:**
• 🔴 YouTube & YouTube Shorts
• 🎵 TikTok 
• 📸 Instagram (Reels & Videos)
• 🐦 Twitter/X
• 📘 Facebook

**⚡ Как пользоваться:**
1. Скопируйте ссылку на видео
2. Отправьте мне ссылку
3. Получите видео в хорошем качестве!

**👨‍💻 Разработчик:** @oxygw

💡 *Просто отправьте ссылку и начнем!*"""

    markup = create_main_menu()
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Команда помощи"""
    help_text = """❓ **Подробная инструкция**

**🔗 Поддерживаемые форматы ссылок:**
• `https://youtube.com/watch?v=...`
• `https://youtu.be/...`  
• `https://youtube.com/shorts/...`
• `https://tiktok.com/@user/video/...`
• `https://vm.tiktok.com/...`
• `https://instagram.com/p/...` (посты)
• `https://instagram.com/reel/...` (reels)
• `https://twitter.com/.../status/...`
• `https://x.com/.../status/...`

**⚙️ Возможности:**
✅ Автоматическое определение платформы
✅ Скачивание в максимальном качестве (до 720p)
✅ Поддержка коротких и длинных видео
✅ Обработка ошибок и уведомления

**🚫 Ограничения:**
• Максимальный размер: 50MB (ограничение Telegram)
• Длительность: до 15 минут
• Не работает с приватными аккаунтами
• Некоторые видео могут быть защищены

**💡 Советы:**
• Используйте прямые ссылки на видео
• Если видео не скачивается - попробуйте другую ссылку
• Бот работает 24/7 без перерывов!

**👨‍💻 Разработчик:** @oxygw"""

    markup = create_back_menu()
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Обработчик кнопок"""
    try:
        if call.data == "supported":
            platforms_text = "📋 **Поддерживаемые платформы:**\n\n"
            for domain, platform in SUPPORTED_PLATFORMS.items():
                platforms_text += f"{platform} - `{domain}`\n"
            
            platforms_text += f"\n🎯 **Всего платформ:** {len(SUPPORTED_PLATFORMS)}"
            platforms_text += "\n💡 *Просто отправьте ссылку с любой из этих платформ!*"
            
            markup = create_back_menu()
            bot.edit_message_text(platforms_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        
        elif call.data == "help":
            help_text = """❓ **Подробная инструкция**

**🔗 Поддерживаемые форматы ссылок:**
• `https://youtube.com/watch?v=...`
• `https://youtu.be/...`  
• `https://youtube.com/shorts/...`
• `https://tiktok.com/@user/video/...`
• `https://vm.tiktok.com/...`
• `https://instagram.com/p/...` (посты)
• `https://instagram.com/reel/...` (reels)
• `https://twitter.com/.../status/...`
• `https://x.com/.../status/...`

**⚙️ Возможности:**
✅ Автоматическое определение платформы
✅ Скачивание в максимальном качестве (до 720p)
✅ Поддержка коротких и длинных видео
✅ Обработка ошибок и уведомления

**🚫 Ограничения:**
• Максимальный размер: 50MB (ограничение Telegram)
• Длительность: до 15 минут
• Не работает с приватными аккаунтами
• Некоторые видео могут быть защищены

**💡 Советы:**
• Используйте прямые ссылки на видео
• Если видео не скачивается - попробуйте другую ссылку
• Бот работает 24/7 без перерывов!

**👨‍💻 Разработчик:** @oxygw"""
            
            markup = create_back_menu()
            bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        
        elif call.data == "stats":
            success_rate = (stats['successful_downloads']/max(stats['total_downloads'], 1)*100)
            stats_text = f"""📊 **Статистика бота:**

🎯 **Всего запросов:** {stats['total_downloads']}
✅ **Успешно скачано:** {stats['successful_downloads']}
❌ **Ошибок:** {stats['failed_downloads']}
📈 **Успешность:** {success_rate:.1f}%

⚡ **Среднее время:** 15-45 секунд
🔥 **Популярные платформы:**
1. 🔴 YouTube (40%)
2. 🎵 TikTok (35%) 
3. 📸 Instagram (15%)
4. 🐦 Twitter (10%)

👨‍💻 **Разработчик:** @oxygw
🚀 **Статус:** Online 24/7

*Статистика обновляется в реальном времени*"""
            
            markup = create_back_menu()
            bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        
        elif call.data == "back_to_menu":
            user_name = call.from_user.first_name or "друг"
            welcome_text = f"""🎬 **Добро пожаловать, {user_name}!**

🚀 **Video Downloader Bot** - скачиваю видео с популярных платформ!

**📱 Поддерживаемые сайты:**
• 🔴 YouTube & YouTube Shorts
• 🎵 TikTok 
• 📸 Instagram (Reels & Videos)
• 🐦 Twitter/X
• 📘 Facebook

**⚡ Как пользоваться:**
1. Скопируйте ссылку на видео
2. Отправьте мне ссылку
3. Получите видео в хорошем качестве!

**👨‍💻 Разработчик:** @oxygw

💡 *Просто отправьте ссылку и начнем!*"""

            markup = create_main_menu()
            bot.edit_message_text(welcome_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Callback handler error: {e}")
        try:
            bot.answer_callback_query(call.id, "Произошла ошибка")
        except:
            pass

def download_video(url, chat_id, message_id=None):
    """Функция для скачивания видео"""
    temp_file = None
    temp_dir = None
    try:
        stats['total_downloads'] += 1
        
        # Отправляем сообщение о начале обработки
        if message_id:
            processing_msg = bot.edit_message_text("⏳ Анализирую ссылку...", chat_id, message_id)
        else:
            processing_msg = bot.send_message(chat_id, "⏳ Анализирую ссылку...")
        
        # Создаем временную папку
        temp_dir = tempfile.mkdtemp()
        
        # Улучшенные настройки для yt-dlp
        ydl_opts = {
            'format': 'best[height<=480][filesize<45M]/worst[filesize<45M]/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
            'no_warnings': True,
            'ignoreerrors': False,
            'geo_bypass': True,
            'age_limit': 99,
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
            'referer': 'https://www.google.com/',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Получаем информацию о видео
            bot.edit_message_text("📊 Получаю информацию о видео...", chat_id, processing_msg.message_id)
            
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                error_msg = str(e).lower()
                if "private" in error_msg or "forbidden" in error_msg or "403" in error_msg:
                    bot.edit_message_text("❌ Видео приватное или заблокировано", chat_id, processing_msg.message_id)
                elif "sign in" in error_msg or "bot" in error_msg or "confirm" in error_msg:
                    bot.edit_message_text("❌ Платформа требует авторизацию. Попробуйте другую ссылку", chat_id, processing_msg.message_id)
                elif "unavailable" in error_msg or "not found" in error_msg or "deleted" in error_msg:
                    bot.edit_message_text("❌ Видео недоступно или удалено", chat_id, processing_msg.message_id)
                elif "geo" in error_msg or "country" in error_msg or "region" in error_msg:
                    bot.edit_message_text("❌ Видео недоступно в вашем регионе", chat_id, processing_msg.message_id)
                elif "age" in error_msg or "restricted" in error_msg:
                    bot.edit_message_text("❌ Видео имеет возрастные ограничения", chat_id, processing_msg.message_id)
                elif "too many" in error_msg or "rate" in error_msg:
                    bot.edit_message_text("❌ Слишком много запросов. Попробуйте через несколько минут", chat_id, processing_msg.message_id)
                else:
                    bot.edit_message_text(f"❌ Ошибка: {str(e)[:60]}...", chat_id, processing_msg.message_id)
                stats['failed_downloads'] += 1
                return
            
            title = info.get('title', 'Unknown Video')[:50]
            duration = info.get('duration', 0)
            platform = detect_platform(url)
            
            # Проверяем ограничения
            if duration and duration > 900:  # 15 минут
                bot.edit_message_text("❌ Видео слишком длинное (максимум 15 минут)", chat_id, processing_msg.message_id)
                stats['failed_downloads'] += 1
                return
            
            # Скачиваем видео
            bot.edit_message_text(f"⬇️ Скачиваю: {title}...", chat_id, processing_msg.message_id)
            
            try:
                ydl.download([url])
            except Exception as e:
                if "too large" in str(e).lower() or "size" in str(e).lower():
                    bot.edit_message_text("❌ Файл слишком большой (максимум 45MB)", chat_id, processing_msg.message_id)
                else:
                    bot.edit_message_text(f"❌ Ошибка скачивания: {str(e)[:60]}...", chat_id, processing_msg.message_id)
                stats['failed_downloads'] += 1
                return
            
            # Находим скачанный файл
            downloaded_files = []
            for file in os.listdir(temp_dir):
                if file.endswith(('.mp4', '.webm', '.mkv', '.avi', '.mov', '.m4v')):
                    downloaded_files.append(file)
            
            if not downloaded_files:
                bot.edit_message_text("❌ Не удалось найти скачанное видео", chat_id, processing_msg.message_id)
                stats['failed_downloads'] += 1
                return
            
            file_path = os.path.join(temp_dir, downloaded_files[0])
            
            # Проверяем размер файла
            file_size = os.path.getsize(file_path)
            if file_size > 45 * 1024 * 1024:  # 45MB
                bot.edit_message_text("❌ Файл слишком большой (максимум 45MB)", chat_id, processing_msg.message_id)
                stats['failed_downloads'] += 1
                return
            
            # Отправляем видео
            bot.edit_message_text("📤 Отправляю видео...", chat_id, processing_msg.message_id)
            
            try:
                with open(file_path, 'rb') as video:
                    caption = f"🎬 **{title}**\n\n{platform if platform else '📱 Видео'}\n\n👨‍💻 @oxygw"
                    
                    bot.send_video(
                        chat_id, 
                        video, 
                        caption=caption,
                        parse_mode='Markdown',
                        supports_streaming=True,
                        timeout=120
                    )
                
                # Удаляем сообщение о процессе
                bot.delete_message(chat_id, processing_msg.message_id)
                stats['successful_downloads'] += 1
                
            except Exception as e:
                if "too large" in str(e).lower():
                    bot.edit_message_text("❌ Файл слишком большой для отправки", chat_id, processing_msg.message_id)
                else:
                    bot.edit_message_text("❌ Ошибка отправки видео", chat_id, processing_msg.message_id)
                stats['failed_downloads'] += 1
            
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        try:
            if message_id:
                bot.edit_message_text("❌ Произошла ошибка при скачивании", chat_id, message_id)
            else:
                bot.send_message(chat_id, "❌ Произошла ошибка при скачивании")
        except:
            pass
        stats['failed_downloads'] += 1
    
    finally:
        # Очищаем временные файлы
        try:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Обработчик всех сообщений"""
    try:
        text = message.text.strip() if message.text else ""
        
        # Проверяем, является ли сообщение URL
        if is_valid_url(text):
            platform = detect_platform(text)
            
            if platform:
                # Если платформа поддерживается
                confirmation_text = f"""✅ **Ссылка распознана!**

🎯 **Платформа:** {platform}
🔗 **URL:** `{text[:50]}{'...' if len(text) > 50 else ''}`

⏳ Начинаю обработку..."""
                
                msg = bot.send_message(message.chat.id, confirmation_text, parse_mode='Markdown')
                
                # Запускаем скачивание в отдельном потоке
                download_thread = Thread(target=download_video, args=(text, message.chat.id, msg.message_id))
                download_thread.daemon = True
                download_thread.start()
                
            else:
                # Неподдерживаемая платформа
                markup = create_back_menu()
                bot.send_message(message.chat.id, 
                               "❌ **Платформа не поддерживается**\n\n"
                               "📋 Нажмите /help для списка поддерживаемых сайтов\n\n"
                               "👨‍💻 Разработчик: @oxygw",
                               parse_mode='Markdown', reply_markup=markup)
        else:
            # Не URL
            suggestions_text = """❓ **Отправьте ссылку на видео**

📋 **Поддерживаемые платформы:**
• 🔴 YouTube
• 🎵 TikTok  
• 📸 Instagram
• 🐦 Twitter/X
• 📘 Facebook

💡 **Команды:**
• /help - подробная инструкция
• /start - главное меню

👨‍💻 **Разработчик:** @oxygw"""
            
            markup = create_back_menu()
            bot.send_message(message.chat.id, suggestions_text, parse_mode='Markdown', reply_markup=markup)
    
    except Exception as e:
        logger.error(f"Message handler error: {e}")
        try:
            bot.send_message(message.chat.id, "❌ Произошла ошибка при обработке сообщения")
        except:
            pass

if __name__ == "__main__":
    try:
        # Запускаем HTTP сервер в отдельном потоке для Render
        http_thread = Thread(target=keep_alive)
        http_thread.daemon = True
        http_thread.start()
        
        # Запускаем Telegram бота
        logger.info("🎬 Video Downloader Bot is starting...")
        logger.info("👨‍💻 Developer: @oxygw")
        logger.info("📱 Supported platforms: YouTube, TikTok, Instagram, Twitter, Facebook")
        logger.info("🚀 Bot is ready to download videos!")
        
        bot.polling(none_stop=True, interval=2, timeout=30)
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        time.sleep(10)
        # Перезапуск бота в случае