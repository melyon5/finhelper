from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date, datetime

from utils.database import db
from utils.models import User, Transaction, CategoryType
from utils.helpers import get_category_spent
from config import DAILY_SUMMARY_HOUR


def send_daily_summary(bot, app):
    with app.app_context():
        today = date.today()
        start = datetime.combine(today, datetime.min.time())
        for user in User.query.all():
            total = (db.session.query(db.func.sum(Transaction.amount))
                     .filter_by(user_id=user.id, type=CategoryType.expense)
                     .filter(Transaction.timestamp >= start)
                     .scalar() or 0)
            bot.send_message(
                chat_id=user.telegram_id,
                text=f"📊 Ежедневная сводка: {total:.2f} {user.currency}"
            )


def check_budgets(bot, app):
    with app.app_context():
        for user in User.query.all():
            for b in user.budgets:
                spent = get_category_spent(user, b.category_id)
                limit = b.amount
                if limit <= 0:
                    continue
                pct = spent / limit * 100
                if pct >= 80:
                    msg = (
                        f"⚠️ Бюджет «{b.category.name}»: {spent:.2f}/{limit:.2f} "
                        f"{user.currency} ({pct:.0f}%)"
                    )
                    bot.send_message(chat_id=user.telegram_id, text=msg)


def init_scheduler(bot, app):
    sched = BackgroundScheduler()
    sched.add_job(
        send_daily_summary, 'cron', hour=DAILY_SUMMARY_HOUR, minute=0,
        args=[bot, app], id='daily_summary'
    )
    sched.add_job(
        check_budgets, 'cron', hour=9, minute=0,
        args=[bot, app], id='check_budgets'
    )
    sched.start()
    return sched
