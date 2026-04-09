import json
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== НАСТРОЙКИ ==========
NOTIFICATION_THRESHOLD = 5  # Уведомлять, если осталось МЕНЕЕ этого числа (по умолчанию 5)
CHECK_INTERVAL_HOURS = 1    # Проверять остатки каждый час
NOTIFICATION_FILE = "notified_items.json"  # Файл для отслеживания отправленных уведомлений

# ========== ДАННЫЕ ТОВАРОВ ==========
FOLDERS = {
    "🌿 Зелень": [
        "Аралия", "Аспарагус", "Аспидистра", "Берграсс", "Гипсофила", "Грин белл", "Дуб", "Лапник",
        "Паник", "фонтан", "Папоротник", "Питтоспорум", "Робелини", "Рускус Итальянский",
        "Рускус Обычный", "Саллал", "Солидаго", "Статица Лимониум", "Фисташка", "Эвкалипт"
    ],
    "🌹 Роза Кустовая": [
        "Роза кустовая 1 метр", "Роза кустовая 40 см", "Роза кустовая 50 см",
        "Роза кустовая 60 см", "Роза кустовая 70 см", "Роза кустовая 80 см", "Роза кустовая 90 см"
    ],
    "💌 открытки": [
        "Записка 50", "Короб от холода", "Крафт 10", "Кризал", "Маска",
        "Открытка 150", "Открытка 50", "Топпер"
    ],
    "🌸 Роза": [
        "Роза 1 метр", "Роза 35 см", "роза 40 см", "роза 60 см", "роза 60 см",
        "роза 70 см", "роза 80 см", "роза 90 см"
    ],
    "🌼 Хризантемы": [
        "Хризантема Одноголовая", "Хризантема кустовая", "Хризантема САНТИНИ"
    ],
    "🏵️ Роза Эквадор": [
        "Роза Эквадор 1 метр", "Роза Эквадор 110 см", "Роза Эквадор 40 см",
        "Роза Эквадор 50 см", "Роза Эквадор 60 см", "Роза Эквадор 70 см",
        "Роза Эквадор 80 см", "Роза Эквадор 90 см"
    ],
    "✨ Экзотика": [
        "Агапантус", "Аллиум", "Альпиния", "Альстромерия", "Амар", "Амарилис", "Амми", "Ананас",
        "Анемон", "Анитиринум", "Антуриум", "Астер", "Астильба", "Астрантия", "Ахилея", "Бамбук",
        "Банксия", "Брассика", "Бруния", "Бувардия", "Буплерум", "Ванда", "Верба", "Вероника",
        "Вибурнум", "Гвоздика", "Гелиокония", "Гениста", "Гентиана", "Георгина", "Гербера",
        "Гербера мини", "Гиацинт", "Гиперикум", "Гиппеаструм", "Гладиолус", "Глориоза 1 пучок",
        "Глориоза 1 шт", "Гортензия", "Грин Трик", "Дельфиниум", "Илекс", "Ирис", "Калла короткая",
        "Кампанула", "Капсикум", "Клематис", "Краспедия", "Лаванда", "Лилия", "Люпин", "Маттиола",
        "Мимоза", "Монстера", "Мускари", "Наринэ", "Нaрцисс", "Озотамнус", "Оксипетал", "Оринитогалум",
        "Орхидея мини", "Павлин", "Пион", "Подсолнух", "Полиантес", "Протея", "Ранункулюс", "Ромашка",
        "Сафари", "Седум", "Серрурия", "Сирень", "Скабиоза", "Скимия", "Стрелиция", "Танацетум", "Танго",
        "Трахелиум", "Фрезия", "Хамелациум", "Хлеборус", "Хелоне", "Хлопок", "Целозия", "Эрингиум", "Эустома"
    ]
}

DATA_FILE = "inventory.json"

def load_inventory():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    inventory = {}
    for items in FOLDERS.values():
        for item in items:
            inventory[item] = 0
    inventory["роза 40 см"] = 58
    return inventory

def save_inventory(inventory):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)

def load_notified_items():
    """Загружает список товаров, о которых уже уведомили"""
    if os.path.exists(NOTIFICATION_FILE):
        with open(NOTIFICATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_notified_items(notified):
    with open(NOTIFICATION_FILE, "w", encoding="utf-8") as f:
        json.dump(notified, f, ensure_ascii=False, indent=2)

# Хранилище состояний
user_states = {}
# ID администратора (кто будет получать уведомления)
ADMIN_IDS = []  # Сюда добавьте свой Telegram ID

async def send_low_stock_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Проверяет остатки и отправляет уведомления"""
    inventory = context.bot_data["inventory"]
    notified_items = context.bot_data.get("notified_items", {})
    changed = False
    
    low_stock_items = []
    for item, count in inventory.items():
        if 0 < count < NOTIFICATION_THRESHOLD:
            low_stock_items.append((item, count))
    
    # Отправляем уведомления
    for admin_id in ADMIN_IDS:
        try:
            # Проверяем, нужно ли отправить уведомление
            current_time = datetime.now().isoformat()
            
            for item, count in low_stock_items:
                last_notified = notified_items.get(item)
                
                # Отправляем, если:
                # 1. Ещё не уведомляли
                # 2. Прошло больше 6 часов с последнего уведомления (не спамим)
                if not last_notified or (datetime.now() - datetime.fromisoformat(last_notified)) > timedelta(hours=6):
                    # Отправляем уведомление
                    message = (
                        f"⚠️ *ВНИМАНИЕ! НИЗКИЙ ОСТАТОК!* ⚠️\n\n"
                        f"📦 *Товар:* {item}\n"
                        f"🔢 *Осталось:* {count} шт.\n"
                        f"📊 *Порог:* менее {NOTIFICATION_THRESHOLD} шт.\n\n"
                        f"🔄 Пополните склад!"
                    )
                    
                    keyboard = [[
                        InlineKeyboardButton(f"➕ Добавить +1", callback_data=f"inc_{item}"),
                        InlineKeyboardButton(f"✏️ Установить количество", callback_data=f"set_{item}")
                    ]]
                    
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=message,
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    
                    notified_items[item] = current_time
                    changed = True
        
        except Exception as e:
            print(f"Ошибка отправки уведомления {admin_id}: {e}")
    
    # Очищаем старые записи (если товар уже не в критическом состоянии)
    for item in list(notified_items.keys()):
        if inventory.get(item, 0) >= NOTIFICATION_THRESHOLD:
            del notified_items[item]
            changed = True
    
    if changed:
        context.bot_data["notified_items"] = notified_items
        save_notified_items(notified_items)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Добавляем пользователя в список админов, если он первый (можно убрать)
    if user_id not in ADMIN_IDS:
        ADMIN_IDS.append(user_id)
        context.bot_data["admin_ids"] = ADMIN_IDS
        await update.message.reply_text(
            "🔔 *Вы получите уведомления о низких остатках!*\n\n"
            "Когда товара останется менее 5 штук, я пришлю предупреждение.",
            parse_mode="Markdown"
        )
    
    keyboard = []
    for folder_name in FOLDERS.keys():
        keyboard.append([InlineKeyboardButton(folder_name, callback_data=f"folder_{folder_name}")])
    keyboard.append([InlineKeyboardButton("🔍 Поиск", callback_data="search")])
    keyboard.append([InlineKeyboardButton("📊 Статистика", callback_data="stats")])
    keyboard.append([InlineKeyboardButton("⚙️ Настройки уведомлений", callback_data="notification_settings")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌼 *Склад цветов*\n\n"
        f"🔔 Уведомления активны (порог: < {NOTIFICATION_THRESHOLD} шт.)\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "stats":
        inventory = context.bot_data["inventory"]
        total_items = sum(inventory.values())
        total_positions = len(inventory)
        low_stock = [(item, count) for item, count in inventory.items() if 0 < count < NOTIFICATION_THRESHOLD]
        
        text = f"📊 *Статистика склада*\n\n"
        text += f"📦 Всего позиций: {total_positions}\n"
        text += f"🔢 Общее количество: {total_items} шт.\n"
        text += f"⚠️ Порог уведомлений: менее {NOTIFICATION_THRESHOLD} шт.\n\n"
        
        if low_stock:
            text += f"🚨 *Требуют пополнения* ({len(low_stock)} товаров):\n"
            for item, count in low_stock[:15]:
                text += f"• {item}: {count} шт.\n"
        else:
            text += "✅ *Все товары в норме!*"
        
        keyboard = [[InlineKeyboardButton("◀️ В меню", callback_data="back_to_menu")]]
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data == "notification_settings":
        keyboard = [
            [InlineKeyboardButton(f"📊 Текущий порог: {NOTIFICATION_THRESHOLD}", callback_data="show_threshold")],
            [InlineKeyboardButton("➕ Увеличить порог", callback_data="inc_threshold")],
            [InlineKeyboardButton("➖ Уменьшить порог", callback_data="dec_threshold")],
            [InlineKeyboardButton("🔔 Проверить остатки сейчас", callback_data="check_now")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "⚙️ *Настройки уведомлений*\n\n"
            f"🔔 Товары, которых осталось *менее {NOTIFICATION_THRESHOLD} шт.*, "
            f"будут вызывать уведомление.\n\n"
            f"Уведомления приходят раз в 6 часов на один товар, чтобы не спамить.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data == "show_threshold":
        await query.answer(f"Текущий порог: менее {NOTIFICATION_THRESHOLD} штук", show_alert=True)
        return
    
    if data == "inc_threshold":
        global NOTIFICATION_THRESHOLD
        NOTIFICATION_THRESHOLD += 1
        await query.answer(f"Порог увеличен до {NOTIFICATION_THRESHOLD}", show_alert=True)
        await button_handler(update, context)  # обновляем меню
        return
    
    if data == "dec_threshold":
        global NOTIFICATION_THRESHOLD
        if NOTIFICATION_THRESHOLD > 1:
            NOTIFICATION_THRESHOLD -= 1
            await query.answer(f"Порог уменьшен до {NOTIFICATION_THRESHOLD}", show_alert=True)
        else:
            await query.answer("Порог не может быть меньше 1", show_alert=True)
        await button_handler(update, context)
        return
    
    if data == "check_now":
        await query.answer("🔍 Проверяю остатки...")
        await send_low_stock_notifications(context)
        await query.edit_message_text(
            "✅ Проверка выполнена!\n"
            "Если есть товары с низкими остатками, вы получите уведомления.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="notification_settings")]])
        )
        return
    
    if data == "search":
        await query.edit_message_text(
            "🔍 *Поиск товаров*\n\n"
            "Отправьте название товара (или его часть):\n"
            "Например: *роза* или *40 см*",
            parse_mode="Markdown"
        )
        user_states[query.from_user.id] = "waiting_for_search"
        return
    
    if data.startswith("folder_"):
        folder_name = data[7:]
        items = FOLDERS.get(folder_name, [])
        inventory = context.bot_data["inventory"]
        
        text = f"📁 *{folder_name}*\n\n"
        keyboard = []
        for item in items:
            count = inventory.get(item, 0)
            # Подсветка низких остатков
            warning = "⚠️ " if 0 < count < NOTIFICATION_THRESHOLD else ""
            text += f"• {warning}{item}: {count} шт.\n"
            keyboard.append([
                InlineKeyboardButton(f"➖", callback_data=f"dec_{item}"),
                InlineKeyboardButton(f"{item[:25]}", callback_data=f"set_{item}"),
                InlineKeyboardButton(f"➕", callback_data=f"inc_{item}")
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")])
        
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data.startswith("inc_"):
        item_name = data[4:]
        inventory = context.bot_data["inventory"]
        old_count = inventory.get(item_name, 0)
        inventory[item_name] = old_count + 1
        save_inventory(inventory)
        context.bot_data["inventory"] = inventory
        
        # Проверяем, нужно ли убрать уведомление (если стало >= порога)
        if old_count + 1 >= NOTIFICATION_THRESHOLD:
            notified = context.bot_data.get("notified_items", {})
            if item_name in notified:
                del notified[item_name]
                context.bot_data["notified_items"] = notified
                save_notified_items(notified)
        
        await query.answer(f"+1: {item_name[:30]} → {inventory[item_name]}")
        await refresh_current_folder(query, context)
        return
    
    if data.startswith("dec_"):
        item_name = data[4:]
        inventory = context.bot_data["inventory"]
        current = inventory.get(item_name, 0)
        if current > 0:
            inventory[item_name] = current - 1
            save_inventory(inventory)
            context.bot_data["inventory"] = inventory
            
            # Проверяем, нужно ли отправить уведомление о низком остатке
            if 0 < current - 1 < NOTIFICATION_THRESHOLD:
                await check_and_notify_low_stock(context, item_name, current - 1)
            
            await query.answer(f"-1: {item_name[:30]} → {inventory[item_name]}")
        else:
            await query.answer("❌ Не может быть меньше 0", show_alert=True)
        await refresh_current_folder(query, context)
        return
    
    if data.startswith("set_"):
        item_name = data[4:]
        user_states[query.from_user.id] = f"setting_{item_name}"
        await query.edit_message_text(
            f"✏️ *{item_name}*\n\n"
            f"Текущее количество: {context.bot_data['inventory'].get(item_name, 0)} шт.\n\n"
            f"Введите новое количество цифрами:",
            parse_mode="Markdown"
        )
        return
    
    if data == "back_to_menu":
        keyboard = []
        for folder_name in FOLDERS.keys():
            keyboard.append([InlineKeyboardButton(folder_name, callback_data=f"folder_{folder_name}")])
        keyboard.append([InlineKeyboardButton("🔍 Поиск", callback_data="search")])
        keyboard.append([InlineKeyboardButton("📊 Статистика", callback_data="stats")])
        keyboard.append([InlineKeyboardButton("⚙️ Настройки уведомлений", callback_data="notification_settings")])
        await query.edit_message_text(
            "🌼 Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def check_and_notify_low_stock(context: ContextTypes.DEFAULT_TYPE, item_name: str, count: int):
    """Немедленная проверка и отправка уведомления"""
    notified_items = context.bot_data.get("notified_items", {})
    
    for admin_id in ADMIN_IDS:
        last_notified = notified_items.get(item_name)
        
        if not last_notified or (datetime.now() - datetime.fromisoformat(last_notified)) > timedelta(hours=6):
            message = (
                f"⚠️ *НИЗКИЙ ОСТАТОК!* ⚠️\n\n"
                f"📦 *{item_name}*\n"
                f"🔢 Осталось: *{count}* шт.\n"
                f"📊 Нужно пополнить!"
            )
            
            keyboard = [[
                InlineKeyboardButton(f"➕ Добавить +1", callback_data=f"inc_{item_name}"),
                InlineKeyboardButton(f"✏️ Установить количество", callback_data=f"set_{item_name}")
            ]]
            
            await context.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            notified_items[item_name] = datetime.now().isoformat()
            context.bot_data["notified_items"] = notified_items
            save_notified_items(notified_items)
            break

async def refresh_current_folder(query, context):
    current_text = query.message.text
    for folder_name in FOLDERS.keys():
        if folder_name in current_text:
            items = FOLDERS[folder_name]
            inventory = context.bot_data["inventory"]
            text = f"📁 *{folder_name}*\n\n"
            keyboard = []
            for item in items:
                count = inventory.get(item, 0)
                warning = "⚠️ " if 0 < count < NOTIFICATION_THRESHOLD else ""
                text += f"• {warning}{item}: {count} шт.\n"
                keyboard.append([
                    InlineKeyboardButton(f"➖", callback_data=f"dec_{item}"),
                    InlineKeyboardButton(f"{item[:25]}", callback_data=f"set_{item}"),
                    InlineKeyboardButton(f"➕", callback_data=f"inc_{item}")
                ])
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")])
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id in user_states:
        state = user_states[user_id]
        
        if state == "waiting_for_search":
            await search_products(update, context, text)
            del user_states[user_id]
            return
        
        if state.startswith("setting_"):
            item_name = state[8:]
            try:
                new_value = int(text)
                if new_value < 0:
                    await update.message.reply_text("❌ Количество не может быть отрицательным!")
                    return
                
                inventory = context.bot_data["inventory"]
                old_value = inventory.get(item_name, 0)
                inventory[item_name] = new_value
                save_inventory(inventory)
                context.bot_data["inventory"] = inventory
                
                # Обновляем уведомления
                notified = context.bot_data.get("notified_items", {})
                if new_value >= NOTIFICATION_THRESHOLD and item_name in notified:
                    del notified[item_name]
                elif 0 < new_value < NOTIFICATION_THRESHOLD:
                    # Проверяем, нужно ли отправить уведомление
                    await check_and_notify_low_stock(context, item_name, new_value)
                
                context.bot_data["notified_items"] = notified
                save_notified_items(notified)
                
                await update.message.reply_text(f"✅ {item_name}\nНовое количество: {new_value} шт.")
                del user_states[user_id]
                
                # Возвращаем в меню
                keyboard = []
                for folder_name in FOLDERS.keys():
                    keyboard.append([InlineKeyboardButton(folder_name, callback_data=f"folder_{folder_name}")])
                keyboard.append([InlineKeyboardButton("🔍 Поиск", callback_data="search")])
                keyboard.append([InlineKeyboardButton("📊 Статистика", callback_data="stats")])
                keyboard.append([InlineKeyboardButton("⚙️ Настройки уведомлений", callback_data="notification_settings")])
                await update.message.reply_text("🌼 Вернулись в меню:", reply_markup=InlineKeyboardMarkup(keyboard))
                
            except ValueError:
                await update.message.reply_text("❌ Пожалуйста, введите ЦЕЛОЕ число!")
            return

async def search_products(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    inventory = context.bot_data["inventory"]
    results = []
    
    query_lower = query.lower()
    for item, count in inventory.items():
        if query_lower in item.lower():
            results.append((item, count))
    
    if not results:
        await update.message.reply_text(f"❌ Ничего не найдено для: '{query}'")
        return
    
    results.sort(key=lambda x: x[0])
    text = f"🔍 *Результаты поиска:* '{query}'\n\n"
    
    keyboard = []
    for item, count in results[:20]:
        warning = "⚠️ " if 0 < count < NOTIFICATION_THRESHOLD else ""
        text += f"• {warning}{item}: {count} шт.\n"
        keyboard.append([
            InlineKeyboardButton(f"➖", callback_data=f"dec_{item}"),
            InlineKeyboardButton(f"✏️", callback_data=f"set_{item}"),
            InlineKeyboardButton(f"➕", callback_data=f"inc_{item}")
        ])
    
    if len(results) > 20:
        text += f"\n*И ещё {len(results) - 20} товаров...*"
    
    keyboard.append([InlineKeyboardButton("◀️ В меню", callback_data="back_to_menu")])
    
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def notification_loop(context: ContextTypes.DEFAULT_TYPE):
    """Фоновая задача для регулярной проверки остатков"""
    await send_low_stock_notifications(context)

def main():
    # 🔴 ВСТАВЬТЕ СВОЙ ТОКЕН ОТ @BotFather 🔴
    TOKEN = "8433697627:AAE8yyhHKbYsGYLe6v9fisvnnJLcPWC4Kl4"
    
    app = Application.builder().token(TOKEN).build()
    
    inventory = load_inventory()
    notified_items = load_notified_items()
    
    app.bot_data["inventory"] = inventory
    app.bot_data["notified_items"] = notified_items
    app.bot_data["admin_ids"] = []
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем фоновую задачу для проверки остатков каждый час
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(notification_loop, interval=CHECK_INTERVAL_HOURS * 3600, first=10)
        print(f"✅ Фоновая проверка остатков запущена (каждые {CHECK_INTERVAL_HOURS} ч.)")
    
    print("✅ Бот с уведомлениями запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()