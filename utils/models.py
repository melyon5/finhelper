import enum
from datetime import datetime

from utils.database import db


class CategoryType(enum.Enum):
    expense = "expense"
    income = "income"


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    currency = db.Column(db.String(3), default="RUB")
    categories = db.relationship("Category", back_populates="user", lazy="dynamic")
    transactions = db.relationship("Transaction", back_populates="user", lazy="dynamic")
    budgets = db.relationship("Budget", back_populates="user", lazy="dynamic")


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.Enum(CategoryType), nullable=False)
    user = db.relationship("User", back_populates="categories")
    transactions = db.relationship("Transaction", back_populates="category", lazy="dynamic")
    budgets = db.relationship("Budget", back_populates="category", lazy="dynamic")


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.Enum(CategoryType), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", back_populates="transactions")
    category = db.relationship("Category", back_populates="transactions")


class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    user = db.relationship("User", back_populates="budgets")
    category = db.relationship("Category", back_populates="budgets")
