import random

import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import Book, Category, Role, TwoFactorSetting, User


CATEGORY_NAMES = [
    "Fiction",
    "Non-Fiction",
    "Science & Technology",
    "History",
    "Biography & Memoir",
    "Children's Books",
    "Young Adult",
    "Mystery & Thriller",
    "Fantasy & Sci-Fi",
    "Self-Help & Personal Development",
]


@click.command("seed")
@with_appcontext
def seed_command():
    seed_data()
    click.echo("Database seeded.")


def seed_data():
    role_user = Role.query.filter_by(name="user").first()
    role_admin = Role.query.filter_by(name="admin").first()
    if not role_user:
        role_user = Role(name="user")
        db.session.add(role_user)
    if not role_admin:
        role_admin = Role(name="admin")
        db.session.add(role_admin)
    db.session.flush()

    categories = []
    for name in CATEGORY_NAMES:
        category = Category.query.filter_by(name=name).first()
        if not category:
            category = Category(name=name, description=f"Books in {name}")
            db.session.add(category)
        categories.append(category)
    db.session.flush()

    if Book.query.count() < 100:
        start_idx = Book.query.count()
        for i in range(start_idx, 100):
            category = categories[i % len(categories)]
            book = Book(
                title=f"Placeholder Book {i + 1}",
                author=f"Author {i + 1}",
                description=f"A compelling description for placeholder book {i + 1} in {category.name}.",
                price=round(9.99 + (i % 20) * 1.5, 2),
                isbn=f"9780000{i + 1:06d}",
                stock_quantity=random.randint(5, 40),
                cover_image_url=f"https://picsum.photos/seed/book-{i + 1}/300/450",
                language="English" if i % 3 else "French",
                category=category,
            )
            db.session.add(book)

    admin = User.query.filter_by(email="admin@bookstore.local").first()
    if not admin:
        admin = User(
            email="admin@bookstore.local",
            full_name="Bookstore Admin",
            role=role_admin,
            language_preference="en",
            two_factor_enabled=False,
        )
        admin.set_password("Admin123!")
        db.session.add(admin)
        db.session.flush()
        db.session.add(TwoFactorSetting(user_id=admin.id, enabled=False, method="app"))
    elif not admin.two_factor_secret:
        admin.two_factor_secret = User.two_factor_secret.default.arg()

    db.session.commit()
