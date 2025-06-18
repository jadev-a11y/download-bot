import os
import telebot
from telebot import types
import qrcode
from PIL import Image, ImageDraw, ImageFont
import io
import logging
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import tempfile
from pyzbar import pyzbar
import cv2
import numpy as np

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
                <title>QR Code Generator Bot</title>
                <meta charset="UTF-8">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #1a1a1a; color: white; }
                    h1 { color: #00d4aa; }
                </style>
            </head>
            <body>
                <h1>📱 QR Code Generator Bot</h1>
                <p>✅ Online and Ready</p>
                <p>🔧 Generate QR codes instantly</p>
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
stats = {
    'qr_generated': 0,
    'qr_scanned': 0,
    'total_users': set()
}

# Хранилище настроек пользователей
user_settings = {}

def create_main_menu():
    """Создает главное меню"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn1 = types.InlineKeyboardButton("📱 Создать QR код", callback_data="create_qr")
    btn2 = types.InlineKeyboardButton("🔍 Сканировать QR", callback_data="scan_info")
    btn3 = types.InlineKeyboardButton("⚙️ Размер QR", callback_data="settings")
    btn4 = types.InlineKeyboardButton("📊 Статистика", callback_data="stats")
    btn5 = types.InlineKeyboardButton("❓ Помощь", callback_data="help")
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    
    return markup

def create_size_menu(user_id):
    """Создает меню выбора размера"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    current_size = user_settings.get(user_id, {}).get('size', 300)
    
    sizes = [200, 300, 400, 600]
    for size in sizes:
        text = f"{'✅ ' if size == current_size else ''}{size}x{size}"
        markup.add(types.InlineKeyboardButton(text, callback_data=f"size_{size}"))
    
    back_btn = types.InlineKeyboardButton("🔙 Назад в меню", callback_data="menu")
    markup.add(back_btn)
    
    return markup

def create_back_menu():
    """Создает кнопку назад"""
    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton("🔙 Назад в меню", callback_data="menu")
    markup.add(back_btn)
    return markup

def generate_qr_code(text, size=300):
    """Генерирует QR код"""
    try:
        # Создаем QR код
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        
        # Создаем изображение
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Изменяем размер
        qr_img = qr_img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Сохраняем в байты
        img_buffer = io.BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer
    except Exception as e:
        logger.error(f"QR generation error: {e}")
        return None

def scan_qr_code(image_bytes):
    """Сканирует QR код из изображения"""
    try:
        # Конвертируем bytes в numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Сканируем QR коды
        decoded_objects = pyzbar.decode(image)
        
        if decoded_objects:
            results = []
            for obj in decoded_objects:
                data = obj.data.decode('utf-8')
                qr_type = obj.type
                results.append(f"**Тип:** {qr_type}\n**Данные:** `{data}`")
            return results
        else:
            return None
    except Exception as e:
        logger.error(f"QR scan error: {e}")
        return None

@bot.message_handler(commands=['start'])
def start_command(message):
    """Команда /start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "друг"
    
    # Добавляем пользователя в статистику
    stats['total_users'].add(user_id)
    
    # Устанавливаем настройки по умолчанию
    if user_id not in user_settings:
        user_settings[user_id] = {'size': 300}
    
    welcome_text = f"""📱 **Добро пожаловать, {user_name}!**

🚀 **QR Code Generator Bot**

**🔧 Возможности:**
• 📱 Создание QR кодов из текста, ссылок
• 🔍 Сканирование QR кодов из фото
• ⚙️ Настройка размера (200x200 до 600x600)
• 📊 Статистика использования

**⚡ Как пользоваться:**
1. Нажмите "Создать QR код"
2. Отправьте текст или ссылку
3. Получите готовый QR код!

**👨‍💻 Разработчик:** @oxygw

💡 *Выберите действие ниже:*"""

    markup = create_main_menu()
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Обработчик кнопок"""
    try:
        user_id = call.from_user.id
        
        if call.data == "create_qr":
            text = """📱 **Создание QR кода**

📝 **Отправьте мне:**
• Любой текст
• Ссылку на сайт
• Номер телефона
• Email адрес
• Или что угодно еще!

⚙️ **Текущий размер:** {}x{}

💡 *Просто отправьте текст следующим сообщением*""".format(
                user_settings.get(user_id, {}).get('size', 300),
                user_settings.get(user_id, {}).get('size', 300)
            )
            
            markup = create_back_menu()
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 parse_mode='Markdown', reply_markup=markup)
        
        elif call.data == "scan_info":
            text = """🔍 **Сканирование QR кода**

📷 **Отправьте мне фото с QR кодом**

✅ **Поддерживаемые форматы:**
• QR Code
• Data Matrix
• Aztec Code
• Code128, Code39
• EAN13, UPC-A

💡 *Просто отправьте фото следующим сообщением*"""
            
            markup = create_back_menu()
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 parse_mode='Markdown', reply_markup=markup)
        
        elif call.data == "settings":
            text = """⚙️ **Настройки размера QR кода**

📏 **Выберите размер:**"""
            
            markup = create_size_menu(user_id)
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 parse_mode='Markdown', reply_markup=markup)
        
        elif call.data.startswith("size_"):
            size = int(call.data.replace("size_", ""))
            if user_id not in user_settings:
                user_settings[user_id] = {}
            user_settings[user_id]['size'] = size
            
            text = f"""✅ **Размер установлен: {size}x{size}**

📏 **Выберите размер:**"""
            
            markup = create_size_menu(user_id)
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 parse_mode='Markdown', reply_markup=markup)
        
        elif call.data == "stats":
            total_users = len(stats['total_users'])
            text = f"""📊 **Статистика бота**

👥 **Всего пользователей:** {total_users}
📱 **QR кодов создано:** {stats['qr_generated']}
🔍 **QR кодов отсканировано:** {stats['qr_scanned']}

⚡ **Ваши настройки:**
📏 Размер QR: {user_settings.get(user_id, {}).get('size', 300)}x{user_settings.get(user_id, {}).get('size', 300)}

👨‍💻 **Разработчик:** @oxygw
🚀 **Статус:** Online 24/7"""
            
            markup = create_back_menu()
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 parse_mode='Markdown', reply_markup=markup)
        
        elif call.data == "help":
            text = """❓ **Помощь по использованию**

**📱 Создание QR кода:**
1. Нажмите "Создать QR код"
2. Отправьте любой текст
3. Получите готовый QR код

**🔍 Сканирование QR кода:**
1. Нажмите "Сканировать QR"
2. Отправьте фото с QR кодом
3. Получите расшифровку

**⚙️ Настройки:**
• Размеры: 200x200, 300x300, 400x400, 600x600
• Высокое качество изображений
• Быстрая обработка

**💡 Примеры использования:**
• QR для Wi-Fi пароля
• QR для ссылки на сайт
• QR для контактной информации
• QR для геолокации

**🔧 Команды:**
• /start - главное меню
• /stats - статистика

👨‍💻 **Разработчик:** @oxygw"""
            
            markup = create_back_menu()
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 parse_mode='Markdown', reply_markup=markup)
        
        elif call.data == "menu":
            user_name = call.from_user.first_name or "друг"
            welcome_text = f"""📱 **Добро пожаловать, {user_name}!**

🚀 **QR Code Generator Bot**

**🔧 Возможности:**
• 📱 Создание QR кодов из текста, ссылок
• 🔍 Сканирование QR кодов из фото
• ⚙️ Настройка размера (200x200 до 600x600)
• 📊 Статистика использования

**⚡ Как пользоваться:**
1. Нажмите "Создать QR код"
2. Отправьте текст или ссылку
3. Получите готовый QR код!

**👨‍💻 Разработчик:** @oxygw

💡 *Выберите действие ниже:*"""
            
            markup = create_main_menu()
            bot.edit_message_text(welcome_text, call.message.chat.id, call.message.message_id, 
                                 parse_mode='Markdown', reply_markup=markup)
        
        try:
            bot.answer_callback_query(call.id)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Callback error: {e}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Обработчик фотографий"""
    try:
        user_id = message.from_user.id
        stats['total_users'].add(user_id)
        
        # Отправляем статус
        status_msg = bot.send_message(message.chat.id, "🔍 Сканирую QR код...")
        
        # Получаем фото
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Сканируем QR код
        results = scan_qr_code(downloaded_file)
        
        if results:
            stats['qr_scanned'] += 1
            
            response_text = "✅ **QR код успешно отсканирован!**\n\n"
            for i, result in enumerate(results, 1):
                response_text += f"**QR #{i}:**\n{result}\n\n"
            
            response_text += "👨‍💻 **Разработчик:** @oxygw"
            
            # Удаляем статусное сообщение
            bot.delete_message(message.chat.id, status_msg.message_id)
            
            markup = create_back_menu()
            bot.send_message(message.chat.id, response_text, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.edit_message_text("❌ **QR код не найден**\n\n"
                                 "💡 Убедитесь что:\n"
                                 "• QR код четко виден\n"
                                 "• Фото хорошего качества\n"
                                 "• QR код не поврежден\n\n"
                                 "🔄 Попробуйте еще раз", 
                                 message.chat.id, status_msg.message_id, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Photo handler error: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка при обработке фото")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Обработчик текстовых сообщений"""
    try:
        user_id = message.from_user.id
        text = message.text.strip()
        
        # Добавляем пользователя в статистику
        stats['total_users'].add(user_id)
        
        if not text:
            markup = create_back_menu()
            bot.send_message(message.chat.id, 
                           "❓ **Отправьте текст для создания QR кода**\n\n"
                           "📱 Или используйте кнопки меню ниже", 
                           parse_mode='Markdown', reply_markup=markup)
            return
        
        # Отправляем статус
        status_msg = bot.send_message(message.chat.id, "📱 Создаю QR код...")
        
        # Получаем размер из настроек пользователя
        size = user_settings.get(user_id, {}).get('size', 300)
        
        # Генерируем QR код
        qr_image = generate_qr_code(text, size)
        
        if qr_image:
            stats['qr_generated'] += 1
            
            # Определяем тип контента
            if text.startswith(('http://', 'https://')):
                content_type = "🔗 Ссылка"
            elif text.startswith(('tel:', '+', '8')) or text.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').isdigit():
                content_type = "📞 Телефон"
            elif '@' in text and '.' in text:
                content_type = "📧 Email"
            else:
                content_type = "📝 Текст"
            
            caption = f"""✅ **QR код создан!**

{content_type}: `{text[:100]}{'...' if len(text) > 100 else ''}`
📏 **Размер:** {size}x{size}

👨‍💻 **Разработчик:** @oxygw"""
            
            # Удаляем статусное сообщение
            bot.delete_message(message.chat.id, status_msg.message_id)
            
            # Отправляем QR код
            markup = create_back_menu()
            bot.send_photo(message.chat.id, qr_image, caption=caption, 
                          parse_mode='Markdown', reply_markup=markup)
        else:
            bot.edit_message_text("❌ Ошибка создания QR кода", 
                                 message.chat.id, status_msg.message_id)
    
    except Exception as e:
        logger.error(f"Text handler error: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка при создании QR кода")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Команда статистики"""
    user_id = message.from_user.id
    total_users = len(stats['total_users'])
    
    text = f"""📊 **Статистика бота**

👥 **Всего пользователей:** {total_users}
📱 **QR кодов создано:** {stats['qr_generated']}
🔍 **QR кодов отсканировано:** {stats['qr_scanned']}

⚡ **Ваши настройки:**
📏 Размер QR: {user_settings.get(user_id, {}).get('size', 300)}x{user_settings.get(user_id, {}).get('size', 300)}

👨‍💻 **Разработчик:** @oxygw"""
    
    markup = create_back_menu()
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

if __name__ == "__main__":
    try:
        # HTTP сервер для Render
        http_thread = Thread(target=keep_alive)
        http_thread.daemon = True
        http_thread.start()
        
        # Запуск бота
        logger.info("📱 QR Code Generator Bot starting...")
        logger.info("👨‍💻 Developer: @oxygw")
        logger.info("🚀 Bot ready!")
        
        bot.polling(none_stop=True, interval=1, timeout=60)
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        time.sleep(10)