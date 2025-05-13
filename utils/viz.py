import io
import matplotlib.pyplot as plt


def plot_monthly_category_bar(data):
    names, values = zip(*data.items())
    fig, ax = plt.subplots()
    ax.bar(names, values)
    ax.set_xticklabels(names, rotation=45, ha='right')
    ax.set_title("Расходы по категориям за месяц")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    return buf


def plot_balance_trend(points):
    dates, balances = zip(*points)
    fig, ax = plt.subplots()
    ax.plot(dates, balances)
    fig.autofmt_xdate()
    ax.set_title("Тренд баланса за месяц")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    return buf
