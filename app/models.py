from datetime import datetime
from decimal import Decimal
import secrets

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    language_preference = db.Column(db.String(8), default="en", nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)

    two_factor_enabled = db.Column(db.Boolean, default=False, nullable=False)
    two_factor_method = db.Column(db.String(32), default="app", nullable=False)
    firebase_uid = db.Column(db.String(128), nullable=True)
    two_factor_secret = db.Column(db.String(64), nullable=False, default=lambda: secrets.token_hex(16))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    role = db.relationship("Role")
    reviews = db.relationship("Review", back_populates="user", cascade="all,delete-orphan")
    cart_items = db.relationship("CartItem", back_populates="user", cascade="all,delete-orphan")
    orders = db.relationship("Order", back_populates="user", cascade="all,delete-orphan")
    two_factor_settings = db.relationship(
        "TwoFactorSetting", back_populates="user", cascade="all,delete-orphan"
    )

    @property
    def is_admin(self):
        return self.role and self.role.name == "admin"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, default="", nullable=False)

    books = db.relationship("Book", back_populates="category")


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    isbn = db.Column(db.String(32), unique=True, nullable=False, index=True)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    cover_image_url = db.Column(db.String(500), nullable=False)
    language = db.Column(db.String(16), nullable=False, default="English")
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)

    category = db.relationship("Category", back_populates="books")
    reviews = db.relationship("Review", back_populates="book", cascade="all,delete-orphan")

    @property
    def average_rating(self):
        if not self.reviews:
            return 0.0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 2)

    @property
    def review_count(self):
        return len(self.reviews)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="reviews")
    book = db.relationship("Book", back_populates="reviews")

    __table_args__ = (db.UniqueConstraint("user_id", "book_id", name="uniq_user_book_review"),)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    user = db.relationship("User", back_populates="cart_items")
    book = db.relationship("Book")

    __table_args__ = (db.UniqueConstraint("user_id", "book_id", name="uniq_user_book_cart"),)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    shipping_address = db.Column(db.Text, nullable=False)
    payment_reference = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="created")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all,delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    title_snapshot = db.Column(db.String(255), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", back_populates="items")
    book = db.relationship("Book")


class TwoFactorSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    enabled = db.Column(db.Boolean, default=False, nullable=False)
    method = db.Column(db.String(32), default="app", nullable=False)
    phone_number = db.Column(db.String(32), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="two_factor_settings")
