from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters

from bot.commands import (
    start_command,
    add_transaction_entry,
    amount_received,
    category_received,
    show_balance,
    stats_menu_handler,
    stats_today,
    stats_week,
    stats_month,
    export_csv,
    export_excel,
    export_diagrams,
    currency_rates,
    settings_menu,
    settings_choice,
    set_currency,
    prompt_new_category,
    new_category_name,
    new_category_type,
    delete_category_prompt,
    delete_category_confirm,
    delete_category_execute,
    cancel_handler,
    STATE_AMOUNT,
    STATE_CATEGORY,
    STATE_STATS_CHOICE,
    STATE_SETTINGS_CHOICE,
    STATE_CURRENCY_SELECT,
    STATE_NEW_CAT_NAME,
    STATE_NEW_CAT_TYPE,
    STATE_DELETE_CAT_SELECT,
    STATE_DELETE_CONFIRM,
)


def register_handlers(app: Application):
    app.add_handler(CommandHandler("start", start_command))

    transaction_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^(Добавить расход|Добавить доход)$"), add_transaction_entry)
        ],
        states={
            STATE_AMOUNT: [
                MessageHandler(filters.Regex(r"^[0-9]+(\.[0-9]+)?$"), amount_received)
            ],
            STATE_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, category_received)
            ],
        },
        fallbacks=[MessageHandler(filters.Regex(r"^Отмена$"), cancel_handler)],
        allow_reentry=True,
    )
    app.add_handler(transaction_conv)

    app.add_handler(MessageHandler(filters.Regex(r"^Показать баланс$"), show_balance))

    stats_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^Статистика$"), stats_menu_handler)],
        states={
            STATE_STATS_CHOICE: [
                MessageHandler(filters.Regex(r"^За день$"), stats_today),
                MessageHandler(filters.Regex(r"^За неделю$"), stats_week),
                MessageHandler(filters.Regex(r"^За месяц$"), stats_month),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex(r"^Отмена$"), cancel_handler)],
        allow_reentry=True,
    )
    app.add_handler(stats_conv)

    app.add_handler(MessageHandler(filters.Regex(r"^Экспорт в CSV$"), export_csv))
    app.add_handler(MessageHandler(filters.Regex(r"^Экспорт в XLSX$"), export_excel))
    app.add_handler(MessageHandler(filters.Regex(r"^Диаграммы$"), export_diagrams))
    app.add_handler(MessageHandler(filters.Regex(r"^Курс валют$"), currency_rates))

    settings_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^Настройки$"), settings_menu)],
        states={
            STATE_SETTINGS_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_choice)
            ],
            STATE_CURRENCY_SELECT: [
                MessageHandler(filters.Regex(r"^(RUB|USD|EUR|Отмена)$"), set_currency)
            ],
            STATE_NEW_CAT_NAME: [
                MessageHandler(filters.Regex(r"^Добавить категорию$"), prompt_new_category),
                MessageHandler(filters.Regex(r"^Удалить категорию$"), delete_category_prompt),
            ],
            STATE_NEW_CAT_TYPE: [
                MessageHandler(filters.Regex(r"^(Расход|Доход|Отмена)$"), new_category_type)
            ],
            STATE_DELETE_CAT_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_category_confirm)
            ],
            STATE_DELETE_CONFIRM: [
                MessageHandler(filters.Regex(r"^(Да|Нет)$"), delete_category_execute)
            ],
        },
        fallbacks=[MessageHandler(filters.Regex(r"^Отмена$"), cancel_handler)],
        allow_reentry=True,
    )
    app.add_handler(settings_conv)
