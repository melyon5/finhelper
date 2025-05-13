import io
import csv
from datetime import datetime, timedelta, time, timezone
from typing import Dict, List, Tuple, Optional

import pandas as pd

from utils.database import db
from utils.models import User, Category, Transaction, CategoryType, Budget

BOM = '\ufeff'


def get_or_create_user(tg_id: int) -> User:
    user = User.query.filter_by(telegram_id=tg_id).first()
    if not user:
        user = User(telegram_id=tg_id)
        db.session.add(user)
        db.session.commit()
        _init_categories(user)
    return user


def _init_categories(user: User) -> None:
    defaults = [
        ("Еда", CategoryType.expense),
        ("Транспорт", CategoryType.expense),
        ("Развлечения", CategoryType.expense),
        ("Зарплата", CategoryType.income),
        ("Бонус", CategoryType.income),
    ]
    for name, ctype in defaults:
        db.session.add(Category(user_id=user.id, name=name, type=ctype))
    db.session.commit()


def create_transaction(user: User, amount: float, ctype: CategoryType, cat_name: str) -> Optional[Transaction]:
    cat = Category.query.filter_by(user_id=user.id, name=cat_name, type=ctype).first()
    if not cat:
        return None
    t = Transaction(
        user_id=user.id,
        amount=amount,
        type=ctype,
        category_id=cat.id
    )
    db.session.add(t)
    db.session.commit()
    return t


def get_balance(user: User) -> Tuple[float, float, float]:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inc = (
            db.session.query(db.func.sum(Transaction.amount))
            .filter_by(user_id=user.id, type=CategoryType.income)
            .filter(Transaction.timestamp >= start)
            .scalar() or 0.0
    )
    exp = (
            db.session.query(db.func.sum(Transaction.amount))
            .filter_by(user_id=user.id, type=CategoryType.expense)
            .filter(Transaction.timestamp >= start)
            .scalar() or 0.0
    )
    return inc - exp, inc, exp


def get_balance_trend(user: User, days: int = 30) -> List[Tuple[datetime, float]]:
    end = datetime.now(timezone.utc)
    start_date = (end - timedelta(days=days - 1)).date()
    daily_net: Dict[datetime.date, float] = {}
    transactions = (
        Transaction.query
        .filter_by(user_id=user.id)
        .filter(Transaction.timestamp >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))
        .order_by(Transaction.timestamp)
        .all()
    )
    for txn in transactions:
        d = txn.timestamp.date()
        delta = txn.amount if txn.type == CategoryType.income else -txn.amount
        daily_net[d] = daily_net.get(d, 0.0) + delta
    trend: List[Tuple[datetime, float]] = []
    cumulative = 0.0
    for i in range(days):
        current = start_date + timedelta(days=i)
        cumulative += daily_net.get(current, 0.0)
        trend.append((datetime.combine(current, time.min, tzinfo=timezone.utc), cumulative))
    return trend


def export_transactions_csv(user: User) -> io.BytesIO:
    buffer = io.StringIO()
    buffer.write(BOM)
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(["ID", "Сумма", "Тип", "Категория", "Дата/Время"])
    rows = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp).all()
    for t in rows:
        writer.writerow([
            t.id,
            f"{t.amount:.2f}",
            t.type.value,
            t.category.name,
            t.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ])
    bio = io.BytesIO(buffer.getvalue().encode('utf-8'))
    bio.name = 'transactions.csv'
    bio.seek(0)
    return bio


def export_transactions_excel(user: User) -> io.BytesIO:
    rows = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp).all()
    records = [
        {
            'ID': t.id,
            'Сумма': t.amount,
            'Тип': t.type.value,
            'Категория': t.category.name,
            'Дата/Время': t.timestamp
        }
        for t in rows
    ]
    df = pd.DataFrame(records)
    df['Сумма'] = df['Сумма'].map(lambda x: f"{x:.2f}")
    df['Дата/Время'] = pd.to_datetime(df['Дата/Время']).dt.strftime("%Y-%m-%d %H:%M:%S")
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Transactions')
    bio.name = 'transactions.xlsx'
    bio.seek(0)
    return bio


def set_budget(user: User, category_name: str, amount: float) -> bool:
    cat = Category.query.filter_by(
        user_id=user.id,
        name=category_name,
        type=CategoryType.expense
    ).first()
    if not cat:
        return False
    budget = Budget.query.filter_by(user_id=user.id, category_id=cat.id).first()
    if budget:
        budget.amount = amount
    else:
        db.session.add(Budget(user_id=user.id, category_id=cat.id, amount=amount))
    db.session.commit()
    return True


def get_category_spent(user: User, category_id: int) -> float:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spent = (
            db.session.query(db.func.sum(Transaction.amount))
            .filter_by(
                user_id=user.id,
                type=CategoryType.expense,
                category_id=category_id
            )
            .filter(Transaction.timestamp >= start)
            .scalar() or 0.0
    )
    return spent


def get_monthly_expenses_by_category(user: User) -> Dict[str, float]:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    data: Dict[str, float] = {}
    cats = Category.query.filter_by(user_id=user.id, type=CategoryType.expense).all()
    for cat in cats:
        total = (
                db.session.query(db.func.sum(Transaction.amount))
                .filter_by(user_id=user.id, type=CategoryType.expense, category_id=cat.id)
                .filter(Transaction.timestamp >= start)
                .scalar() or 0.0
        )
        data[cat.name] = total
    return data
