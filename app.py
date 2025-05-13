import logging
from threading import Thread
from telegram.ext import ApplicationBuilder

from config import BOT_TOKEN
from bot.handlers import register_handlers
from utils.schedule_tasks import init_scheduler
from utils.app import create_app as create_flask_app

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def _run_api(app):
    app.run(host="127.0.0.1", port=5000, debug=False)


def main():
    logger.info("Старт API и бота")
    flask_app = create_flask_app()
    flask_app.app_context().push()
    Thread(target=_run_api, args=(flask_app,), daemon=True).start()
    logger.info("API запущен на http://127.0.0.1:5000")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    register_handlers(app)
    init_scheduler(app.bot, flask_app)
    logger.info("Запуск polling")
    app.run_polling()


if __name__ == "__main__":
    main()
