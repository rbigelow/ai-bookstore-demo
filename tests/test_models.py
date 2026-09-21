from app.extensions import db
from app.models import Book, Category, Review, Role, User


def test_user_admin_role_property(app):
    with app.app_context():
        role_admin = Role.query.filter_by(name="admin").first()
        user = User(email="boss@example.com", full_name="Boss", role=role_admin)
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()
        assert user.is_admin is True


def test_book_average_rating(app):
    with app.app_context():
        category = Category.query.first()
        role = Role.query.filter_by(name="user").first()
        user = User(email="reader@example.com", full_name="Reader", role=role)
        second_user = User(email="reader2@example.com", full_name="Reader Two", role=role)
        user.set_password("Pass123!")
        second_user.set_password("Pass123!")
        book = Book(
            title="TDD by Example",
            author="Kent Beck",
            description="Testing sample",
            price=19.99,
            isbn="9780000999999",
            stock_quantity=10,
            cover_image_url="https://picsum.photos/seed/tdd/300/450",
            language="English",
            category=category,
        )
        db.session.add_all([user, second_user, book])
        db.session.flush()
        db.session.add_all(
            [
                Review(user_id=user.id, book_id=book.id, rating=5, comment="Great"),
                Review(user_id=second_user.id, book_id=book.id, rating=3, comment="Okay"),
            ]
        )
        db.session.commit()

        refreshed = Book.query.get(book.id)
        assert refreshed.review_count == 2
        assert refreshed.average_rating == 4.0
