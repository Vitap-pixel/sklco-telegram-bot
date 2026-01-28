import logging
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8556537689:AAHD0oO-zFbqn8lXEaGUWQNi2HMi3W2KpZk")
API_URL = "https://api.skl-co.ru/rest/products"
API_QUANTITY_URL = "https://api.skl-co.ru/rest/quantity"
API_TOKEN = os.environ.get("API_TOKEN", "K5kpa-Ohz0nQCjQDxL7n1swdgNcrVk_F")

# ПРАВИЛЬНЫЕ СКЛАДЫ ПО РЕГИОНАМ
WAREHOUSE_GROUPS = {
    'Санкт-Петербург (СЗФО)': [
        ('szfo_tr', 'СПб (тр)'),
        ('szfo_internet', 'СПб (интернет)'),
        ('szfo_main', 'СПб (основной)'),
        ('szfo_project', 'СПб (проекты)'),
        ('szfo_sng', 'СПб (СНГ)'),
        ('szfo_seti', 'СПб (сети)')
    ],
    'Москва (МОП)': [
        ('mop_tr', 'Москва (тр)'),
        ('mop_internet', 'Москва (интернет)'),
        ('mop_project', 'Москва (проекты)'),
        ('mop_sng', 'Москва (СНГ)'),
        ('mop_seti', 'Москва (сети)')
    ],
    'Новосибирск (НОП)': [
        ('nop_tr', 'Новосибирск (тр)'),
        ('nop_internet', 'Новосибирск (интернет)'),
        ('nop_project', 'Новосибирск (проекты)'),
        ('nop_sng', 'Новосибирск (СНГ)'),
        ('nop_seti', 'Новосибирск (сети)'),
        ('nop_rc', 'Новосибирск (РЦ)')
    ],
    'Ростов на Дону (РОП)': [
        ('rop_tr', 'Ростов (тр)'),
        ('rop_internet', 'Ростов (интернет)'),
        ('rop_project', 'Ростов (проекты)'),
        ('rop_seti', 'Ростов (сети)')
    ],
    'Самара (СОП)': [
        ('sop_tr', 'Самара (тр)'),
        ('sop_internet', 'Самара (интернет)'),
        ('sop_project', 'Самара (проекты)'),
        ('sop_seti', 'Самара (сети)')
    ],
    'Екатеринбург (УОП)': [
        ('uop_tr', 'Екатеринбург (тр)'),
        ('uop_internet', 'Екатеринбург (интернет)'),
        ('uop_project', 'Екатеринбург (проекты)'),
        ('uop_seti', 'Екатеринбург (сети)')
    ]
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить артикул", callback_data='check_article')],
        [InlineKeyboardButton("🏢 Склады", callback_data='warehouses')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 *Бот проверки остатков Skl-co*\n\n"
        "✅ Проверяю 29 складов в 6 регионах\n"
        "✅ Детальная информация по каждому складу\n"
        "✅ Быстрый ответ\n"
        "✅ Не важно, как написан артикул (регистр не учитывается)\n\n"
        "Просто отправьте артикул товара!\n"
        "Пример: `PRO0000i32` или `Pro0000i32`\n\n"
        "⚠️ Не работает сообщи Перепёлкину Виктору",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'check_article':
        await query.edit_message_text(
            "📝 *Введите артикул товара:*\n\n"
            "Пример: `PRO0000i32`\n\n"
            "Или используйте команду:\n"
            "`/check PRO0000i32`\n\n"
            "⚠️ *Регистр не важен:*\n"
            "`abc123`, `ABC123` и `Abc123` - одно и то же",
            parse_mode='Markdown'
        )
    
    elif query.data == 'warehouses':
        await show_warehouses(query)

async def show_warehouses(query):
    """Показать информацию о складах"""
    text = "🏢 *Все склады Skl-Co*\n\n"
    
    for region, warehouses in WAREHOUSE_GROUPS.items():
        text += f"*{region}* ({len(warehouses)} складов):\n"
        for code, name in warehouses:
            text += f"• {name} (`{code}`)\n"
        text += "\n"
    
    text += f"*Всего:* {sum(len(w) for w in WAREHOUSE_GROUPS.values())} складов"
    
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить артикул", callback_data='check_article')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /check"""
    if not context.args:
        await update.message.reply_text(
            "📝 *Использование:* `/check <артикул>`\n\n"
            "*Пример:*\n"
            "`/check 002M006i77`\n"
            "`/check 123456`\n\n"
            "⚠️ *Регистр не важен* - можно писать как угодно",
            parse_mode='Markdown'
        )
        return
    
    article = context.args[0]
    await process_article(update.message, article)

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех сообщений"""
    if update.message and update.message.text:
        text = update.message.text.strip()
        
        # Пропускаем команды
        if text.startswith('/'):
            return
        
        # Обрабатываем как артикул
        await process_article(update.message, text)

def get_product_info_sync(article: str):
    """Синхронная функция для получения информации о товаре"""
    try:
        # Запрашиваем только основную информацию о товаре
        response = requests.get(
            API_URL,
            params={
                'expand': 'photos',  # Только фото, остальное не нужно
                'article': article.upper()  # Приводим к верхнему регистру для точного поиска
            },
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {API_TOKEN}'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0]
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении информации о товаре: {e}")
        return None

def get_quantity_info_sync(article: str):
    """Синхронная функция для получения информации об остатках"""
    try:
        params = {'product_art': article}
        
        # Собираем все коды складов
        for warehouses in WAREHOUSE_GROUPS.values():
            for code, _ in warehouses:
                params[f'fieldsMap[{code}]'] = code
        
        response = requests.get(
            API_QUANTITY_URL,
            params=params,
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {API_TOKEN}'
            },
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении остатков: {e}")
        return None

async def process_article(message, article: str):
    """Обработка артикула"""
    article = article.strip()
    
    if not article:
        await message.reply_text("❌ Введите артикул товара.")
        return
    
    logger.info(f"Проверка артикула: '{article}'")
    
    # Показываем, что бот печатает
    try:
        await message.reply_chat_action(action="typing")
    except:
        pass
    
    try:
        # Получаем информацию о товаре и остатках параллельно в отдельном потоке
        loop = asyncio.get_event_loop()
        
        # Запускаем синхронные функции в отдельных потоках
        product_task = loop.run_in_executor(None, get_product_info_sync, article)
        quantity_task = loop.run_in_executor(None, get_quantity_info_sync, article)
        
        # Ждем завершения обеих задач
        product_info, quantity_data = await asyncio.gather(product_task, quantity_task)
        
        if not quantity_data:
            await message.reply_text(f"📭 *Артикул:* `{article}`\n\nТовар не найден на складах.", parse_mode='Markdown')
            return
        
        # Ищем товар в данных об остатках (игнорируем регистр)
        product = None
        original_article = article
        article_lower = article.lower()
        
        for item in quantity_data:
            if isinstance(item, dict):
                item_art = item.get('product_art', '')
                if isinstance(item_art, str) and item_art.lower() == article_lower:
                    product = item
                    original_article = item_art
                    break
        
        if not product:
            await message.reply_text(f"📭 *Артикул:* `{article}`\n\nТовар не найден на складах.", parse_mode='Markdown')
            return
        
        # Анализируем остатки по регионам
        region_results = {}
        
        for region_name, warehouses in WAREHOUSE_GROUPS.items():
            region_total = 0
            warehouse_details = []
            
            for code, name in warehouses:
                qty = product.get(code)
                if qty is not None:
                    try:
                        qty_int = int(qty) if qty else 0
                    except:
                        qty_int = 0
                    
                    region_total += qty_int
                    if qty_int > 0:
                        warehouse_details.append(f"    └ {name}: `{qty_int} шт.`")
            
            if region_total > 0:
                region_results[region_name] = {
                    'total': region_total,
                    'details': warehouse_details
                }
        
        # Формируем ответ с остатками
        total_quantity = sum(r['total'] for r in region_results.values())
        
        # Заголовок с информацией о товаре, если есть
        response_text = ""
        if product_info:
            # Добавляем фото, если есть
            photo_url = None
            if product_info.get('photo'):
                photo_url = product_info['photo']
            elif product_info.get('photos') and len(product_info['photos']) > 0:
                photo_url = product_info['photos'][0].get('file_path')
            
            if photo_url:
                # Добавляем ресайз для уменьшения размера
                if '?' not in photo_url:
                    photo_url += '?resize=900x900'
                else:
                    photo_url += '&resize=900x900'
                
                try:
                    await message.reply_photo(
                        photo=photo_url,
                        caption=f"📸 *{original_article}*"
                    )
                except Exception as photo_error:
                    logger.error(f"Ошибка при отправке фото: {photo_error}")
                    # Продолжаем без фото
        
        response_text += f"📦 *Товар:* `{original_article}`\n\n"
        
        if product_info:
            # Добавляем основную информацию
            if product_info.get('name'):
                name = product_info['name']
                # Экранируем специальные символы Markdown
                escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                for char in escape_chars:
                    name = name.replace(char, f'\\{char}')
                
                if len(name) > 100:
                    name = name[:100] + "..."
                response_text += f"*Название:* {name}\n"
            
            if product_info.get('brand'):
                response_text += f"*Бренд:* `{product_info['brand']}`\n"
            
            if product_info.get('category'):
                response_text += f"*Категория:* `{product_info['category']}`\n"
            
            if product_info.get('collection'):
                response_text += f"*Коллекция:* `{product_info['collection']}`\n"
            
            if product_info.get('rrc'):
                response_text += f"*РРЦ:* `{product_info['rrc']} ₽`\n"
            
            if product_info.get('arc'):
                response_text += f"*АРЦ:* `{product_info['arc']} ₽`\n"
            
            response_text += "\n"
        
        # Добавляем информацию об остатках
        response_text += f"📊 *Остатки:* `{total_quantity} шт.`\n\n"
        
        if total_quantity > 0:
            # Показываем регионы с остатками
            response_text += "*🏭 Наличие по регионам:*\n"
            for region_name, data in region_results.items():
                response_text += f"• *{region_name}:* `{data['total']} шт.`\n"
                for detail in data['details']:
                    response_text += f"{detail}\n"
                response_text += "\n"
        else:
            response_text += "📭 *Товар отсутствует на всех складах*\n\n"
        
        response_text += f"*🏢 Проверено регионов:* `{len(WAREHOUSE_GROUPS)}`\n"
        response_text += f"*📦 Проверено складов:* `{sum(len(w) for w in WAREHOUSE_GROUPS.values())}`\n"
        
        # Простые кнопки без подробной информации
        keyboard = [
            [
                InlineKeyboardButton("🔄 Проверить другой", callback_data='check_article'),
                InlineKeyboardButton("🏢 Склады", callback_data='warehouses')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем сообщение
        if len(response_text) > 4000:
            # Разбиваем на части если слишком длинное
            parts = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    await message.reply_text(part, parse_mode='Markdown', reply_markup=reply_markup)
                else:
                    await message.reply_text(part, parse_mode='Markdown')
        else:
            await message.reply_text(response_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except requests.exceptions.Timeout:
        await message.reply_text("⏳ *Превышено время ожидания*\n\nСервер не отвечает.", parse_mode='Markdown')
    except requests.exceptions.ConnectionError:
        await message.reply_text("🔌 *Ошибка подключения*\n\nНе удалось подключиться к серверу.", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        await message.reply_text("⚠️ *Произошла ошибка*\n\nПопробуйте еще раз.", parse_mode='Markdown')

async def warehouses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /warehouses"""
    # Создаем фейковый query для использования существующей функции
    class FakeQuery:
        def __init__(self, message):
            self.message = message
            self.edit_message_text = message.reply_text
    
    fake_query = FakeQuery(update.message)
    await show_warehouses(fake_query)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить артикул", callback_data='check_article')],
        [InlineKeyboardButton("🏢 Склады", callback_data='warehouses')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📚 *Помощь*\n\n"
        "*Основные команды:*\n"
        "• `/start` - Главное меню\n"
        "• `/check <артикул>` - Проверить остатки\n"
        "• `/warehouses` - Список складов\n"
        "• `/help` - Эта справка\n\n"
        "*Как использовать:*\n"
        "1. Отправьте артикул в чат\n"
        "2. Или используйте `/check артикул`\n"
        "3. Получите детальную информацию\n\n"
        "*Что показывает бот:*\n"
        "• Фото товара (если есть)\n"
        "• Название товара\n"
        "• Бренд, категорию, коллекцию\n"
        "• Цены: РРЦ и АРЦ\n"
        "• Остатки по всем складам\n"
        "• Детали по каждому региону\n\n"
        "*Особенности:*\n"
        "• *Регистр не важен* - `abc123`, `ABC123`, `Abc123`\n"
        "• Проверяет 29 складов в 6 регионах\n"
        "• Показывает детали по каждому складу\n\n"
        "*Примеры артикулов:*\n"
        "`002M006i77` `002m006i77` `ABC-123` `abc-123`",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

def main():
    """Запуск бота"""
    print("=" * 60)
    print("🤖 БОТ ДЛЯ ПРОВЕРКИ ОСТАТКОВ SKL-CO")
    print("УПРОЩЕННАЯ ВЕРСИЯ - ОСНОВНАЯ ИНФОРМАЦИЯ")
    print("=" * 60)
    print("✨ ВОЗМОЖНОСТИ:")
    print("• Фото товара (900x900px)")
    print("• Название, бренд, категория, коллекция")
    print("• Цены: РРЦ и АРЦ")
    print("• Остатки по 29 складам в 6 регионах")
    print("• Детали по каждому складу")
    print("=" * 60)
    
    try:
        # Создаем приложение
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики команд
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("check", check_command))
        app.add_handler(CommandHandler("warehouses", warehouses_command))
        
        # Обработчики кнопок (только основные, без details_)
        app.add_handler(CallbackQueryHandler(button_handler, pattern='^(check_article|warehouses)$'))
        
        # Обработчик всех текстовых сообщений
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
        
        print("✅ Бот запущен и готов к работе!")
        print("=" * 60)
        print("Команды:")
        print("/start - Начать работу")
        print("/help - Помощь")
        print("/check <артикул> - Проверить остатки с фото")
        print("/warehouses - Список складов")
        print("=" * 60)
        print("Или просто отправьте артикул в чат")
        print("=" * 60)
        print(f"Проверяет: {sum(len(w) for w in WAREHOUSE_GROUPS.values())} складов")
        print("Регистр артикула игнорируется!")
        print("=" * 60)
        
        # Запускаем бота
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")

if __name__ == '__main__':
    main()