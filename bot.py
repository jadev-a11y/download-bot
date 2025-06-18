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
import shutil

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
                <h1>🎬 Video Downloader Bot</h1>
                <p>✅ Online and Ready</p>
                <p>👨‍💻 Developer: @oxygw</p>
            </body>
            </html>
            """
            self.wfile.write(response.encode('utf-8'))
        except Exception as e:
            logger.error(f"HTTP error: {e}")
    
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        return

def keep_alive():
    """HTTP сервер для Render"""
    try:
        port = int(os.environ.get('PORT', 8000))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        logger.info(f"HTTP server starting on port {port}")
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
stats = {'total': 0, 'success': 0, 'failed': 0}

# Поддерживаемые платформы
PLATFORMS = {
    'youtube.com': '🔴 YouTube',
    'youtu.be': '🔴 YouTube',
    'tiktok.com': '🎵 TikTok',
    'vm.tiktok.com': '🎵 TikTok',
    'instagram.com': '📸 Instagram',
    'twitter.com': '🐦 Twitter',
    'x.com': '🐦 X'
}

def detect_platform(url):
    """Определяет платформу"""
    for domain, platform in PLATFORMS.items():
        if domain in url.lower():
            return platform
    return None

def is_valid_url(url):
    """Проверяет URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def safe_send_message(chat_id, text, reply_markup=None, parse_mode='Markdown'):
    """Безопасная отправка сообщения с retry"""
    for attempt in range(3):
        try:
            return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            if "too many requests" in str(e).lower():
                time.sleep(2 ** attempt)
                continue
            elif attempt == 2:
                try:
                    return bot.send_message(chat_id, "❌ Ошибка отправки сообщения")
                except:
                    pass
            break
    return None

def safe_edit_message(chat_id, message_id, text, reply_markup=None, parse_mode='Markdown'):
    """Безопасное редактирование сообщения"""
    for attempt in range(3):
        try:
            return bot.edit_message_text(text, chat_id, message_id, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            if "too many requests" in str(e).lower():
                time.sleep(2 ** attempt)
                continue
            elif "message is not modified" in str(e).lower():
                return True
            elif attempt == 2:
                return None
            break
    return None

@bot.message_handler(commands=['start'])
def start_command(message):
    """Команда /start"""
    user_name = message.from_user.first_name or "друг"
    
    text = f"""🎬 **Добро пожаловать, {user_name}!**

🚀 **Video Downloader Bot**

**📱 Поддерживаемые сайты:**
• 🔴 YouTube & Shorts
• 🎵 TikTok 
• 📸 Instagram
• 🐦 Twitter/X

**⚡ Как пользоваться:**
1. Скопируйте ссылку на видео
2. Отправьте мне ссылку
3. Получите видео!

**👨‍💻 Разработчик:** @oxygw

💡 *Отправьте ссылку для начала!*"""

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📋 Поддерживаемые сайты", callback_data="supported")
    btn2 = types.InlineKeyboardButton("❓ Помощь", callback_data="help")
    btn3 = types.InlineKeyboardButton("📊 Статистика", callback_data="stats")
    markup.add(btn1, btn2)
    markup.add(btn3)
    
    safe_send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Обработчик кнопок"""
    try:
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton("🔙 Назад в меню", callback_data="menu")
        markup.add(back_btn)
        
        if call.data == "supported":
            text = "📋 **Поддерживаемые платформы:**\n\n"
            for domain, platform in PLATFORMS.items():
                text += f"{platform} - `{domain}`\n"
            text += "\n💡 *Отправьте ссылку с любой платформы!*"
            
        elif call.data == "help":
            text = """❓ **Инструкция**

**🔗 Форматы ссылок:**
• `https://youtube.com/watch?v=...`
• `https://youtu.be/...`
• `https://tiktok.com/@user/video/...`
• `https://instagram.com/p/...`
• `https://twitter.com/.../status/...`

**⚙️ Возможности:**
✅ Автоопределение платформы
✅ Качество до 480p
✅ Размер до 40MB
✅ Длительность до 10 минут

**💡 Советы:**
• Используйте прямые ссылки
• Если не работает - попробуйте другую ссылку
• Бот работает 24/7

**👨‍💻 Разработчик:** @oxygw"""
            
        elif call.data == "stats":
            success_rate = (stats['success']/max(stats['total'], 1)*100) if stats['total'] > 0 else 0
            text = f"""📊 **Статистика:**

🎯 **Всего запросов:** {stats['total']}
✅ **Успешно:** {stats['success']}
❌ **Ошибок:** {stats['failed']}
📈 **Успешность:** {success_rate:.1f}%

👨‍💻 **Разработчик:** @oxygw
🚀 **Статус:** Online 24/7"""
            
        elif call.data == "menu":
            user_name = call.from_user.first_name or "друг"
            text = f"""🎬 **Добро пожаловать, {user_name}!**

🚀 **Video Downloader Bot**

**📱 Поддерживаемые сайты:**
• 🔴 YouTube & Shorts
• 🎵 TikTok 
• 📸 Instagram
• 🐦 Twitter/X

**⚡ Как пользоваться:**
1. Скопируйте ссылку на видео
2. Отправьте мне ссылку
3. Получите видео!

**👨‍💻 Разработчик:** @oxygw

💡 *Отправьте ссылку для начала!*"""
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn1 = types.InlineKeyboardButton("📋 Поддерживаемые сайты", callback_data="supported")
            btn2 = types.InlineKeyboardButton("❓ Помощь", callback_data="help")
            btn3 = types.InlineKeyboardButton("📊 Статистика", callback_data="stats")
            markup.add(btn1, btn2)
            markup.add(btn3)
        
        safe_edit_message(call.message.chat.id, call.message.message_id, text, reply_markup=markup)
        
        try:
            bot.answer_callback_query(call.id)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Callback error: {e}")

def download_video(url, chat_id, message_id):
    """Скачивание видео"""
    temp_dir = None
    try:
        stats['total'] += 1
        
        # Статус: анализ
        safe_edit_message(chat_id, message_id, "⏳ Анализирую ссылку...")
        
        # Создаем временную папку
        temp_dir = tempfile.mkdtemp()
        
        # Настройки yt-dlp
        ydl_opts = {
            'format': 'worst[height<=480]/best[height<=480]/worst',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'geo_bypass': True,
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Получаем информацию
            safe_edit_message(chat_id, message_id, "📊 Получаю информацию...")
            
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                error_msg = str(e).lower()
                if any(word in error_msg for word in ['private', 'forbidden', '403']):
                    safe_edit_message(chat_id, message_id, "❌ Видео приватное или заблокировано")
                elif any(word in error_msg for word in ['sign in', 'bot', 'confirm']):
                    safe_edit_message(chat_id, message_id, "❌ Требуется авторизация. Попробуйте другую ссылку")
                elif any(word in error_msg for word in ['unavailable', 'not found', 'deleted']):
                    safe_edit_message(chat_id, message_id, "❌ Видео недоступно или удалено")
                elif any(word in error_msg for word in ['geo', 'country', 'region']):
                    safe_edit_message(chat_id, message_id, "❌ Видео недоступно в вашем регионе")
                elif any(word in error_msg for word in ['too many', 'rate', 'limit']):
                    safe_edit_message(chat_id, message_id, "❌ Слишком много запросов. Попробуйте через 5 минут")
                else:
                    safe_edit_message(chat_id, message_id, f"❌ Ошибка: {str(e)[:50]}...")
                stats['failed'] += 1
                return
            
            title = info.get('title', 'Video')[:40]
            duration = info.get('duration', 0)
            platform = detect_platform(url)
            
            # Проверки
            if duration and duration > 600:  # 10 минут
                safe_edit_message(chat_id, message_id, "❌ Видео слишком длинное (максимум 10 минут)")
                stats['failed'] += 1
                return
            
            # Скачиваем
            safe_edit_message(chat_id, message_id, f"⬇️ Скачиваю: {title}...")
            
            try:
                ydl.download([url])
            except Exception as e:
                safe_edit_message(chat_id, message_id, f"❌ Ошибка скачивания: {str(e)[:50]}...")
                stats['failed'] += 1
                return
            
            # Ищем файл
            video_files = []
            for file in os.listdir(temp_dir):
                if file.endswith(('.mp4', '.webm', '.mkv', '.avi', '.mov')):
                    video_files.append(file)
            
            if not video_files:
                safe_edit_message(chat_id, message_id, "❌ Файл не найден")
                stats['failed'] += 1
                return
            
            file_path = os.path.join(temp_dir, video_files[0])
            file_size = os.path.getsize(file_path)
            
            if file_size > 40 * 1024 * 1024:  # 40MB
                safe_edit_message(chat_id, message_id, "❌ Файл слишком большой (максимум 40MB)")
                stats['failed'] += 1
                return
            
            # Отправляем
            safe_edit_message(chat_id, message_id, "📤 Отправляю...")
            
            try:
                with open(file_path, 'rb') as video:
                    caption = f"🎬 {title}\n\n{platform or '📱 Видео'}\n\n👨‍💻 @oxygw"
                    
                    bot.send_video(
                        chat_id, 
                        video, 
                        caption=caption,
                        supports_streaming=True,
                        timeout=60
                    )
                
                # Удаляем статусное сообщение
                try:
                    bot.delete_message(chat_id, message_id)
                except:
                    pass
                    
                stats['success'] += 1
                
            except Exception as e:
                safe_edit_message(chat_id, message_id, "❌ Ошибка отправки видео")
                stats['failed'] += 1
                
    except Exception as e:
        logger.error(f"Download error: {e}")
        safe_edit_message(chat_id, message_id, "❌ Произошла ошибка")
        stats['failed'] += 1
    
    finally:
        # Очистка
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Обработчик сообщений"""
    try:
        text = message.text.strip() if message.text else ""
        
        if is_valid_url(text):
            platform = detect_platform(text)
            
            if platform:
                msg_text = f"""✅ **Ссылка распознана!**

🎯 **Платформа:** {platform}
🔗 **URL:** `{text[:40]}...`

⏳ Начинаю обработку..."""
                
                msg = safe_send_message(message.chat.id, msg_text)
                if msg:
                    # Запускаем скачивание в потоке
                    thread = Thread(target=download_video, args=(text, message.chat.id, msg.message_id))
                    thread.daemon = True
                    thread.start()
            else:
                markup = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton("🔙 Назад в меню", callback_data="menu")
                markup.add(back_btn)
                
                safe_send_message(message.chat.id, 
                               "❌ **Платформа не поддерживается**\n\n"
                               "📋 Нажмите кнопку ниже для списка сайтов\n\n"
                               "👨‍💻 @oxygw",
                               reply_markup=markup)
        else:
            markup = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton("🔙 Главное меню", callback_data="menu")
            markup.add(back_btn)
            
            safe_send_message(message.chat.id,
                           "❓ **Отправьте ссылку на видео**\n\n"
                           "📋 **Поддержка:**\n"
                           "• 🔴 YouTube\n"
                           "• 🎵 TikTok\n"
                           "• 📸 Instagram\n"
                           "• 🐦 Twitter/X\n\n"
                           "👨‍💻 **Разработчик:** @oxygw",
                           reply_markup=markup)
    
    except Exception as e:
        logger.error(f"Message handler error: {e}")

if __name__ == "__main__":
    try:
        # HTTP сервер
        http_thread = Thread(target=keep_alive)
        http_thread.daemon = True
        http_thread.start()
        
        # Запуск бота
        logger.info("🎬 Video Downloader Bot starting...")
        logger.info("👨‍💻 Developer: @oxygw")
        logger.info("🚀 Bot ready!")
        
        # Polling с увеличенными интервалами
        bot.polling(none_stop=True, interval=3, timeout=60)
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        time.sleep(15)
        os.execv(__file__, [__file__])