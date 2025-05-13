from flask import Flask, jsonify, request
import requests

from utils.database import init_db

PRIMARY_API = "https://api.exchangerate.host/latest"
FALLBACK_API = "https://open.er-api.com/v6/latest"


def create_app():
    app = Flask(__name__)
    init_db(app)

    @app.route("/api/rates")
    def get_rates():
        base = request.args.get("base", "RUB").upper()
        symbols = request.args.get("symbols", "USD,EUR,RUB").upper()
        targets = [s.strip() for s in symbols.split(",") if s.strip()]

        rates = {}
        date = None

        try:
            resp = requests.get(f"{PRIMARY_API}?base={base}&symbols={symbols}", timeout=5)
            data = resp.json()
            rates = data.get("rates", {})
            date = data.get("date")
        except Exception:
            pass

        if not rates:
            try:
                resp = requests.get(f"{PRIMARY_API}?base={base}", timeout=5)
                full = resp.json().get("rates", {})
                date = resp.json().get("date") or date
                rates = {cur: full[cur] for cur in targets if cur in full}
            except Exception:
                pass

        if not rates:
            try:
                resp = requests.get(f"{FALLBACK_API}/{base}", timeout=5)
                data = resp.json()
                fallback = data.get("rates", {})
                date = data.get("time_last_update_utc") or date
                rates = {cur: fallback[cur] for cur in targets if cur in fallback}
            except Exception:
                pass

        return jsonify({"base": base, "date": date, "rates": rates})

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
