from datetime import datetime
import requests

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from config import LOCAL_API_URL
from utils.database import db
from utils.models import Category, Transaction, CategoryType
from utils.helpers import (
    get_or_create_user,
    create_transaction,
    get_balance,
    export_transactions_csv,
    export_transactions_excel,
    get_monthly_expenses_by_category,
    get_balance_trend,
)
from utils.viz import plot_monthly_category_bar, plot_balance_trend
from bot.keyboards import MAIN_MENU, STATS_MENU, SETTINGS_MENU, CURRENCY_MENU, CATEGORY_MENU

(
    STATE_AMOUNT,
    STATE_CATEGORY,
    STATE_STATS_CHOICE,
    STATE_SETTINGS_CHOICE,
    STATE_CURRENCY_SELECT,
    STATE_NEW_CAT_NAME,
    STATE_NEW_CAT_TYPE,
    STATE_DELETE_CAT_SELECT,
    STATE_DELETE_CONFIRM,
    STATE_BUDGET_CAT,
    STATE_BUDGET_AMOUNT,
) = range(11)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_or_create_user(update.effective_user.id)
    await update.message.reply_text(
        "👋 Привет! Я — твой финансовый помощник. Выбери действие:",
        reply_markup=MAIN_MENU
    )


async def add_transaction_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_or_create_user(update.effective_user.id)
    txn_type = CategoryType.expense if update.message.text == 'Добавить расход' else CategoryType.income
    context.user_data['txn_type'] = txn_type
    prompt = '💸 Введите сумму расхода:' if txn_type == CategoryType.expense else '💰 Введите сумму дохода:'
    await update.message.reply_text(prompt, reply_markup=ReplyKeyboardRemove())
    return STATE_AMOUNT


async def amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text('⚠️ Введите число.')
        return STATE_AMOUNT
    context.user_data['amount'] = amount
    user = get_or_create_user(update.effective_user.id)
    txn_type = context.user_data['txn_type']
    cats = Category.query.filter_by(user_id=user.id, type=txn_type).all()
    keyboard = [[c.name] for c in cats] + [['Отмена']]
    await update.message.reply_text('🗂 Выберите категорию:',
                                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return STATE_CATEGORY


async def category_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == 'Отмена':
        await update.message.reply_text('❌ Отменено.', reply_markup=MAIN_MENU)
        return ConversationHandler.END
    user = get_or_create_user(update.effective_user.id)
    amount = context.user_data['amount']
    txn_type = context.user_data['txn_type']
    transaction = create_transaction(user, amount, txn_type, choice)
    if transaction:
        kind = 'расход' if txn_type == CategoryType.expense else 'доход'
        msg = f"✅ {kind.title()} {amount:.2f} {user.currency} в категории «{choice}» сохранён."
    else:
        msg = '⚠️ Категория не найдена.'
    await update.message.reply_text(msg, reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    balance, inc, exp = get_balance(user)
    text = (
        f"📊 <b>Баланс</b>: {balance:.2f} {user.currency}\n"
        f"💵 Доходы: {inc:.2f} {user.currency}\n"
        f"💸 Расходы: {exp:.2f} {user.currency}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=MAIN_MENU)


async def stats_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('📈 Выберите период:', reply_markup=STATS_MENU)
    return STATE_STATS_CHOICE


async def stats_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total = db.session.query(db.func.sum(Transaction.amount)).filter_by(user_id=user.id,
                                                                        type=CategoryType.expense).filter(
        Transaction.timestamp >= start).scalar() or 0
    await update.message.reply_text(f'📅 Расходы за сегодня: {total:.2f} {user.currency}', reply_markup=MAIN_MENU)
    data = {
        c.name: db.session.query(db.func.sum(Transaction.amount)).filter_by(user_id=user.id, type=CategoryType.expense,
                                                                            category_id=c.id).filter(
            Transaction.timestamp >= start).scalar() or 0 for c in
        Category.query.filter_by(user_id=user.id, type=CategoryType.expense)}
    if any(data.values()):
        buf = plot_monthly_category_bar(data)
        await update.message.reply_photo(buf, caption='📊 По категориям сегодня', reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def stats_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    trend = get_balance_trend(user, days=7)
    buf = plot_balance_trend(trend)
    await update.message.reply_photo(buf, caption='📈 Баланс за 7 дней', reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def stats_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    data = get_monthly_expenses_by_category(user)
    total = sum(data.values())
    await update.message.reply_text(f'📆 Расходы за месяц: {total:.2f} {user.currency}', reply_markup=MAIN_MENU)
    if any(data.values()):
        buf = plot_monthly_category_bar(data)
        await update.message.reply_photo(buf, caption='📊 По категориям за месяц', reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    bio = export_transactions_csv(user)
    await update.message.reply_document(document=bio, filename=bio.name, reply_markup=MAIN_MENU)


async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    bio = export_transactions_excel(user)
    await update.message.reply_document(document=bio, filename=bio.name, reply_markup=MAIN_MENU)


async def export_diagrams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    buf1 = plot_monthly_category_bar(get_monthly_expenses_by_category(user))
    buf2 = plot_balance_trend(get_balance_trend(user))
    await update.message.reply_photo(buf1, caption='📊 Расходы по категориям за месяц', reply_markup=MAIN_MENU)
    await update.message.reply_photo(buf2, caption='📈 Динамика баланса за месяц', reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def currency_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    try:
        resp = requests.get(f"{LOCAL_API_URL}/api/rates?base={user.currency}")
        data = resp.json()
        rates = data.get('rates', {})
        date = data.get('date')
        lines = [f"{cur}: {r:.4f}" for cur, r in rates.items()]
        text = f"🌐 Курс валют к {user.currency} на {date}:\n" + '\n'.join(lines)
    except Exception:
        text = '⚠️ Не удалось получить курсы.'
    await update.message.reply_text(text, reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('⚙️ Настройки:', reply_markup=SETTINGS_MENU)
    return STATE_SETTINGS_CHOICE


async def settings_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == 'Выбрать валюту':
        await update.message.reply_text('🌐 Выберите валюту:', reply_markup=CURRENCY_MENU)
        return STATE_CURRENCY_SELECT
    if text == 'Управление категориями':
        await update.message.reply_text('🗂 Меню категорий:', reply_markup=CATEGORY_MENU)
        return STATE_NEW_CAT_NAME
    if text == 'Установить бюджет':
        user = get_or_create_user(update.effective_user.id)
        cats = Category.query.filter_by(user_id=user.id, type=CategoryType.expense).all()
        keyboard = [[c.name] for c in cats] + [['Отмена']]
        await update.message.reply_text('💰 Выберите категорию:',
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return STATE_BUDGET_CAT
    await update.message.reply_text('❌ Отменено.', reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def set_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == 'Отмена':
        await update.message.reply_text('❌ Отменено.', reply_markup=MAIN_MENU)
        return ConversationHandler.END
    user = get_or_create_user(update.effective_user.id)
    user.currency = update.message.text
    db.session.commit()
    await update.message.reply_text(f'✅ Валюта установлена: {user.currency}', reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def prompt_new_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('➕ Введите название категории:', reply_markup=ReplyKeyboardRemove())
    return STATE_NEW_CAT_NAME


async def new_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_cat'] = update.message.text
    await update.message.reply_text('📑 Выберите тип категории:',
                                    reply_markup=ReplyKeyboardMarkup([['Расход'], ['Доход'], ['Отмена']],
                                                                     resize_keyboard=True))
    return STATE_NEW_CAT_TYPE


async def new_category_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == 'Отмена':
        await update.message.reply_text('❌ Отменено.', reply_markup=MAIN_MENU)
        return ConversationHandler.END
    ct = CategoryType.expense if choice == 'Расход' else CategoryType.income
    user = get_or_create_user(update.effective_user.id)
    name = context.user_data['new_cat']
    if not Category.query.filter_by(user_id=user.id, name=name).first():
        db.session.add(Category(user_id=user.id, name=name, type=ct))
        db.session.commit()
        await update.message.reply_text(f'✅ Категория «{name}» добавлена.', reply_markup=MAIN_MENU)
    else:
        await update.message.reply_text('⚠️ Такая категория уже существует.', reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def delete_category_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    cats = Category.query.filter_by(user_id=user.id).all()
    keyboard = [[c.name] for c in cats] + [['Отмена']]
    await update.message.reply_text('🗑 Выберите категорию для удаления:',
                                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return STATE_DELETE_CAT_SELECT


async def delete_category_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    if name == 'Отмена':
        await update.message.reply_text('❌ Отменено.', reply_markup=MAIN_MENU)
        return ConversationHandler.END
    context.user_data['del_cat'] = name
    await update.message.reply_text(f'❓ Удалить категорию «{name}»?',
                                    reply_markup=ReplyKeyboardMarkup([['Да', 'Нет']], resize_keyboard=True))
    return STATE_DELETE_CONFIRM


async def delete_category_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.message.text
    name = context.user_data.get('del_cat')
    if ans == 'Да' and name:
        user = get_or_create_user(update.effective_user.id)
        cat = Category.query.filter_by(user_id=user.id, name=name).first()
        if cat:
            db.session.delete(cat)
            db.session.commit()
            msg = f'✅ Категория «{name}» удалена.'
        else:
            msg = '⚠️ Категория не найдена.'
    else:
        msg = '❌ Отменено.'
    await update.message.reply_text(msg, reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('❌ Операция отменена.', reply_markup=MAIN_MENU)
    return ConversationHandler.END
