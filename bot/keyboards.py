from telegram import ReplyKeyboardMarkup


def build_keyboard(layout):
    return ReplyKeyboardMarkup(layout, resize_keyboard=True)


MAIN_MENU = build_keyboard([
    ["Добавить расход", "Добавить доход"],
    ["Показать баланс", "Статистика"],
    ["Курс валют"],
    ["Экспорт в CSV", "Экспорт в XLSX"],
    ["Диаграммы", "Настройки"]
])

STATS_MENU = build_keyboard([
    ["За день", "За неделю", "За месяц"],
    ["По категориям"],
    ["Назад"]
])

SETTINGS_MENU = build_keyboard([
    ["Выбрать валюту", "Управление категориями"],
    ["Установить бюджет"],
    ["Назад"]
])

CURRENCY_MENU = build_keyboard([
    ["RUB", "USD", "EUR"],
    ["Назад"]
])

CATEGORY_MENU = build_keyboard([
    ["Добавить категорию", "Удалить категорию"],
    ["Назад"]
])
