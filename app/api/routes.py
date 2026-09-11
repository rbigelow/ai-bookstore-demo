from decimal import Decimal

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import asc, desc

from app.extensions import db
from app.models import (
    Book,
    CartItem,
    Category,
    Order,
    OrderItem,
    Review,
    Role,
    TwoFactorSetting,
    User,
)
from app.services.payment import PaymentService
from app.services.two_factor import TwoFactorService

api_bp = Blueprint("api", __name__)


def response(data=None, message="OK", error=None, status=200):
    return jsonify({"data": data, "message": message, "error": error}), status


def admin_required():
    if not current_user.is_authenticated:
        return response(error="auth_required", message="Authentication required", status=401)
    if not current_user.is_admin:
        return response(error="forbidden", message="Admin access required", status=403)
    return None


def parse_pagination():
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 10)), 1), 50)
    return page, per_page


def user_payload(user):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "language_preference": user.language_preference,
        "role": user.role.name,
        "two_factor_enabled": user.two_factor_enabled,
        "two_factor_method": user.two_factor_method,
    }


def category_payload(category):
    return {"id": category.id, "name": category.name, "description": category.description}


def book_payload(book):
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "description": book.description,
        "price": float(book.price),
        "isbn": book.isbn,
        "stock_quantity": book.stock_quantity,
        "cover_image_url": book.cover_image_url,
        "language": book.language,
        "category": category_payload(book.category),
        "average_rating": book.average_rating,
        "review_count": book.review_count,
    }


def review_payload(review):
    return {
        "id": review.id,
        "book_id": review.book_id,
        "user_id": review.user_id,
        "user_name": review.user.full_name,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at.isoformat(),
        "updated_at": review.updated_at.isoformat(),
    }


def cart_payload(user):
    items = []
    total = Decimal("0.00")
    for item in user.cart_items:
        subtotal = Decimal(item.book.price) * item.quantity
        total += subtotal
        items.append(
            {
                "id": item.id,
                "book_id": item.book_id,
                "title": item.book.title,
                "quantity": item.quantity,
                "unit_price": float(item.book.price),
                "subtotal": float(subtotal),
            }
        )
    return {"items": items, "total": float(total)}


def order_payload(order):
    return {
        "id": order.id,
        "user_id": order.user_id,
        "status": order.status,
        "total_amount": float(order.total_amount),
        "shipping_address": order.shipping_address,
        "payment_reference": order.payment_reference,
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "id": item.id,
                "book_id": item.book_id,
                "title": item.title_snapshot,
                "unit_price": float(item.unit_price),
                "quantity": item.quantity,
            }
            for item in order.items
        ],
    }


@api_bp.post("/users/register")
def register_user():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    full_name = (payload.get("full_name") or payload.get("name") or "").strip()

    if not email or not password or not full_name:
        return response(error="validation_error", message="email, password and full_name are required", status=400)
    if User.query.filter_by(email=email).first():
        return response(error="already_exists", message="User already exists", status=409)

    role = Role.query.filter_by(name="user").first()
    if not role:
        role = Role(name="user")
        db.session.add(role)
        db.session.flush()

    user = User(email=email, full_name=full_name, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(TwoFactorSetting(user_id=user.id, enabled=False, method="app"))
    db.session.commit()

    return response(data=user_payload(user), message="User created", status=201)


@api_bp.post("/users/login")
def login_api():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    otp_code = payload.get("otp_code")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return response(error="invalid_credentials", message="Invalid credentials", status=401)

    if user.two_factor_enabled:
        two_factor = TwoFactorService.verify_code(user, otp_code)
        if not two_factor.verified:
            return response(
                data={"requires_2fa": True, "method": user.two_factor_method},
                error="two_factor_required",
                message=two_factor.message,
                status=401,
            )

    login_user(user)
    session.permanent = True
    return response(data=user_payload(user), message="Logged in")


@api_bp.post("/users/logout")
@login_required
def logout_api():
    logout_user()
    return response(message="Logged out")


@api_bp.get("/users/profile")
@login_required
def get_profile():
    return response(data=user_payload(current_user))


@api_bp.put("/users/profile")
@login_required
def update_profile():
    payload = request.get_json(silent=True) or {}
    if "full_name" in payload:
        current_user.full_name = payload["full_name"].strip() or current_user.full_name
    if payload.get("language_preference") in {"en", "fr"}:
        current_user.language_preference = payload["language_preference"]
        session["lang"] = payload["language_preference"]
    if "two_factor_enabled" in payload:
        current_user.two_factor_enabled = bool(payload["two_factor_enabled"])
    if payload.get("two_factor_method") in {"app", "sms"}:
        current_user.two_factor_method = payload["two_factor_method"]

    setting = TwoFactorSetting.query.filter_by(user_id=current_user.id).first()
    if not setting:
        setting = TwoFactorSetting(user_id=current_user.id)
        db.session.add(setting)
    setting.enabled = current_user.two_factor_enabled
    setting.method = current_user.two_factor_method
    if payload.get("phone_number"):
        setting.phone_number = payload["phone_number"]

    db.session.commit()
    return response(data=user_payload(current_user), message="Profile updated")


@api_bp.get("/users")
def list_users():
    error = admin_required()
    if error:
        return error
    page, per_page = parse_pagination()
    paginated = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return response(
        data={
            "items": [user_payload(user) for user in paginated.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "pages": paginated.pages,
            },
        }
    )


@api_bp.get("/categories")
def list_categories():
    categories = Category.query.order_by(Category.name.asc()).all()
    return response(data=[category_payload(c) for c in categories])


@api_bp.get("/categories/<int:category_id>")
def get_category(category_id):
    category = Category.query.get_or_404(category_id)
    return response(data=category_payload(category))


@api_bp.post("/categories")
def create_category():
    error = admin_required()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return response(error="validation_error", message="name is required", status=400)
    if Category.query.filter_by(name=name).first():
        return response(error="already_exists", message="category already exists", status=409)

    category = Category(name=name, description=(payload.get("description") or "").strip())
    db.session.add(category)
    db.session.commit()
    return response(data=category_payload(category), message="Category created", status=201)


@api_bp.put("/categories/<int:category_id>")
def update_category(category_id):
    error = admin_required()
    if error:
        return error
    category = Category.query.get_or_404(category_id)
    payload = request.get_json(silent=True) or {}
    if payload.get("name"):
        category.name = payload["name"].strip()
    if "description" in payload:
        category.description = (payload["description"] or "").strip()
    db.session.commit()
    return response(data=category_payload(category), message="Category updated")


@api_bp.delete("/categories/<int:category_id>")
def delete_category(category_id):
    error = admin_required()
    if error:
        return error
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    return response(message="Category deleted")


@api_bp.get("/books")
def list_books():
    page, per_page = parse_pagination()
    query = Book.query

    if request.args.get("q"):
        term = f"%{request.args['q'].strip()}%"
        query = query.filter((Book.title.ilike(term)) | (Book.author.ilike(term)) | (Book.description.ilike(term)))
    if request.args.get("category_id"):
        query = query.filter(Book.category_id == int(request.args["category_id"]))
    if request.args.get("min_price"):
        query = query.filter(Book.price >= Decimal(request.args["min_price"]))
    if request.args.get("max_price"):
        query = query.filter(Book.price <= Decimal(request.args["max_price"]))
    if request.args.get("language"):
        query = query.filter(Book.language.ilike(request.args["language"]))

    sort_field = request.args.get("sort", "title")
    sort_order = request.args.get("order", "asc")
    sort_map = {"title": Book.title, "price": Book.price, "author": Book.author, "id": Book.id}
    col = sort_map.get(sort_field, Book.title)
    query = query.order_by(desc(col) if sort_order == "desc" else asc(col))

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    items = [book_payload(book) for book in paginated.items]

    min_rating = request.args.get("min_rating")
    if min_rating:
        threshold = float(min_rating)
        items = [item for item in items if item["average_rating"] >= threshold]

    return response(
        data={
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "pages": paginated.pages,
            },
        }
    )


@api_bp.get("/books/<int:book_id>")
def get_book(book_id):
    book = Book.query.get_or_404(book_id)
    return response(data=book_payload(book))


@api_bp.post("/books")
def create_book():
    error = admin_required()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    required = ["title", "author", "description", "price", "isbn", "stock_quantity", "cover_image_url", "language", "category_id"]
    missing = [field for field in required if field not in payload]
    if missing:
        return response(error="validation_error", message=f"Missing fields: {', '.join(missing)}", status=400)

    category = Category.query.get(payload["category_id"])
    if not category:
        return response(error="not_found", message="Category not found", status=404)

    book = Book(
        title=payload["title"],
        author=payload["author"],
        description=payload["description"],
        price=Decimal(str(payload["price"])),
        isbn=payload["isbn"],
        stock_quantity=int(payload["stock_quantity"]),
        cover_image_url=payload["cover_image_url"],
        language=payload["language"],
        category=category,
    )
    db.session.add(book)
    db.session.commit()
    return response(data=book_payload(book), message="Book created", status=201)


@api_bp.put("/books/<int:book_id>")
def update_book(book_id):
    error = admin_required()
    if error:
        return error
    book = Book.query.get_or_404(book_id)
    payload = request.get_json(silent=True) or {}

    for field in ["title", "author", "description", "isbn", "cover_image_url", "language"]:
        if field in payload:
            setattr(book, field, payload[field])
    if "price" in payload:
        book.price = Decimal(str(payload["price"]))
    if "stock_quantity" in payload:
        book.stock_quantity = int(payload["stock_quantity"])
    if "category_id" in payload:
        category = Category.query.get(payload["category_id"])
        if not category:
            return response(error="not_found", message="Category not found", status=404)
        book.category = category

    db.session.commit()
    return response(data=book_payload(book), message="Book updated")


@api_bp.delete("/books/<int:book_id>")
def delete_book(book_id):
    error = admin_required()
    if error:
        return error
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    return response(message="Book deleted")


@api_bp.get("/cart")
@login_required
def get_cart():
    return response(data=cart_payload(current_user))


@api_bp.post("/cart/items")
@login_required
def add_cart_item():
    payload = request.get_json(silent=True) or {}
    book_id = payload.get("book_id")
    quantity = max(int(payload.get("quantity", 1)), 1)
    book = Book.query.get(book_id)
    if not book:
        return response(error="not_found", message="Book not found", status=404)

    item = CartItem.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if item:
        item.quantity += quantity
    else:
        item = CartItem(user_id=current_user.id, book_id=book_id, quantity=quantity)
        db.session.add(item)

    db.session.commit()
    return response(data=cart_payload(current_user), message="Item added")


@api_bp.put("/cart/items/<int:item_id>")
@login_required
def update_cart_item(item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    payload = request.get_json(silent=True) or {}
    quantity = int(payload.get("quantity", 1))
    if quantity <= 0:
        db.session.delete(item)
    else:
        item.quantity = quantity
    db.session.commit()
    return response(data=cart_payload(current_user), message="Cart updated")


@api_bp.delete("/cart/items/<int:item_id>")
@login_required
def remove_cart_item(item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return response(data=cart_payload(current_user), message="Item removed")


@api_bp.post("/orders")
@login_required
def create_order():
    payload = request.get_json(silent=True) or {}
    if not current_user.cart_items:
        return response(error="empty_cart", message="Cart is empty", status=400)

    shipping_address = (payload.get("shipping_address") or "").strip()
    payment_method = payload.get("payment_method", "mock")
    payment_token = payload.get("payment_token")
    if not shipping_address:
        return response(error="validation_error", message="shipping_address is required", status=400)

    total = Decimal("0.00")
    for item in current_user.cart_items:
        if item.quantity > item.book.stock_quantity:
            return response(error="out_of_stock", message=f"Insufficient stock for {item.book.title}", status=400)
        total += Decimal(item.book.price) * item.quantity

    try:
        payment_reference = PaymentService.charge(float(total), payment_method, payment_token)
    except ValueError as exc:
        return response(error="payment_error", message=str(exc), status=400)

    order = Order(
        user_id=current_user.id,
        total_amount=total,
        shipping_address=shipping_address,
        payment_reference=payment_reference,
        status="paid",
    )
    db.session.add(order)
    db.session.flush()

    for cart_item in current_user.cart_items:
        cart_item.book.stock_quantity -= cart_item.quantity
        db.session.add(
            OrderItem(
                order_id=order.id,
                book_id=cart_item.book_id,
                title_snapshot=cart_item.book.title,
                unit_price=cart_item.book.price,
                quantity=cart_item.quantity,
            )
        )
        db.session.delete(cart_item)

    db.session.commit()
    return response(data=order_payload(order), message="Order created", status=201)


@api_bp.get("/orders")
@login_required
def list_orders():
    page, per_page = parse_pagination()
    query = Order.query
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)
    paginated = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return response(
        data={
            "items": [order_payload(order) for order in paginated.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "pages": paginated.pages,
            },
        }
    )


@api_bp.get("/orders/<int:order_id>")
@login_required
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    if not current_user.is_admin and order.user_id != current_user.id:
        return response(error="forbidden", message="Access denied", status=403)
    return response(data=order_payload(order))


@api_bp.get("/books/<int:book_id>/reviews")
def list_reviews(book_id):
    Book.query.get_or_404(book_id)
    reviews = Review.query.filter_by(book_id=book_id).order_by(Review.created_at.desc()).all()
    return response(data=[review_payload(r) for r in reviews])


@api_bp.post("/books/<int:book_id>/reviews")
@login_required
def create_review(book_id):
    Book.query.get_or_404(book_id)
    payload = request.get_json(silent=True) or {}
    rating = int(payload.get("rating", 0))
    comment = (payload.get("comment") or "").strip()

    if rating < 1 or rating > 5 or not comment:
        return response(error="validation_error", message="rating (1-5) and comment are required", status=400)

    if Review.query.filter_by(book_id=book_id, user_id=current_user.id).first():
        return response(error="already_exists", message="You already reviewed this book", status=409)

    review = Review(book_id=book_id, user_id=current_user.id, rating=rating, comment=comment)
    db.session.add(review)
    db.session.commit()
    return response(data=review_payload(review), message="Review created", status=201)


@api_bp.put("/reviews/<int:review_id>")
@login_required
def update_review(review_id):
    review = Review.query.get_or_404(review_id)
    if not current_user.is_admin and review.user_id != current_user.id:
        return response(error="forbidden", message="Cannot edit this review", status=403)

    payload = request.get_json(silent=True) or {}
    if "rating" in payload:
        rating = int(payload["rating"])
        if rating < 1 or rating > 5:
            return response(error="validation_error", message="rating must be 1-5", status=400)
        review.rating = rating
    if "comment" in payload:
        review.comment = (payload["comment"] or "").strip()

    db.session.commit()
    return response(data=review_payload(review), message="Review updated")


@api_bp.delete("/reviews/<int:review_id>")
@login_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    if not current_user.is_admin and review.user_id != current_user.id:
        return response(error="forbidden", message="Cannot delete this review", status=403)
    db.session.delete(review)
    db.session.commit()
    return response(message="Review deleted")
