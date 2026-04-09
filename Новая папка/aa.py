import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

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
    inventory["роза 40 см"] = 58  # пример
    return inventory

def save_inventory(inventory):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)

# Хранилище состояний для ручного ввода
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for folder_name in FOLDERS.keys():
        keyboard.append([InlineKeyboardButton(folder_name, callback_data=f"folder_{folder_name}")])
    keyboard.append([InlineKeyboardButton("🔍 Поиск", callback_data="search")])
    keyboard.append([InlineKeyboardButton("📊 Статистика", callback_data="stats")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌼 *Склад цветов*\n\n"
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
        low_stock = [item for item, count in inventory.items() if count < 5 and count > 0]
        
        text = f"📊 *Статистика склада*\n\n"
        text += f"📦 Всего позиций: {total_positions}\n"
        text += f"🔢 Общее количество: {total_items} шт.\n"
        if low_stock:
            text += f"\n⚠️ *Заканчивается* (<5 шт):\n"
            for item in low_stock[:10]:
                text += f"• {item}: {inventory[item]} шт.\n"
        
        keyboard = [[InlineKeyboardButton("◀️ В меню", callback_data="back_to_menu")]]
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
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
            text += f"• {item}: {count} шт.\n"
            # Кнопки для каждого товара
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
        inventory[item_name] = inventory.get(item_name, 0) + 1
        save_inventory(inventory)
        context.bot_data["inventory"] = inventory
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
        await query.edit_message_text(
            "🌼 Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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
                text += f"• {item}: {count} шт.\n"
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
                inventory[item_name] = new_value
                save_inventory(inventory)
                context.bot_data["inventory"] = inventory
                
                await update.message.reply_text(f"✅ {item_name}\nНовое количество: {new_value} шт.")
                del user_states[user_id]
                
                # Возвращаем в меню
                keyboard = []
                for folder_name in FOLDERS.keys():
                    keyboard.append([InlineKeyboardButton(folder_name, callback_data=f"folder_{folder_name}")])
                keyboard.append([InlineKeyboardButton("🔍 Поиск", callback_data="search")])
                keyboard.append([InlineKeyboardButton("📊 Статистика", callback_data="stats")])
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
    for item, count in results[:20]:  # максимум 20 результатов
        text += f"• {item}: {count} шт.\n"
        keyboard.append([
            InlineKeyboardButton(f"➖ {item[:20]}", callback_data=f"dec_{item}"),
            InlineKeyboardButton(f"✏️", callback_data=f"set_{item}"),
            InlineKeyboardButton(f"{item[:20]} ➕", callback_data=f"inc_{item}")
        ])
    
    if len(results) > 20:
        text += f"\n*И ещё {len(results) - 20} товаров...*"
    
    keyboard.append([InlineKeyboardButton("◀️ В меню", callback_data="back_to_menu")])
    
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    # 🔴 ВСТАВЬТЕ ТОКЕН ОТ @BotFather 🔴
    TOKEN = "8433697627:AAE8yyhHKbYsGYLe6v9fisvnnJLcPWC4Kl4"
    
    app = Application.builder().token(TOKEN).build()
    
    inventory = load_inventory()
    app.bot_data["inventory"] = inventory
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()