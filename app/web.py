from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import Book, CartItem, Category, Order, OrderItem, Role, User
from app.services.payment import PaymentService

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def home():
    featured_books = Book.query.order_by(Book.id.asc()).limit(12).all()
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template("home.html", books=featured_books, categories=categories)


@web_bp.get("/catalog")
def catalog():
    categories = Category.query.order_by(Category.name.asc()).all()
    selected = request.args.get("category_id", type=int)
    query = Book.query
    if selected:
        query = query.filter_by(category_id=selected)
    books = query.order_by(Book.title.asc()).limit(120).all()
    return render_template("catalog.html", books=books, categories=categories, selected=selected)


@web_bp.get("/categories")
def categories():
    return render_template("categories.html", categories=Category.query.order_by(Category.name.asc()).all())


@web_bp.get("/books/<int:book_id>")
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template("book_detail.html", book=book)


@web_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")

        if not email or not password or not full_name:
            flash(_("All fields are required."), "error")
        elif User.query.filter_by(email=email).first():
            flash(_("A user with that email already exists."), "error")
        else:
            role_obj = Role.query.filter_by(name="user").first()
            if not role_obj:
                role_obj = Role(name="user")
                db.session.add(role_obj)
                db.session.flush()
            user = User(email=email, full_name=full_name, role=role_obj)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(_("Registration successful. Please log in."), "success")
            return redirect(url_for("web.login"))

    return render_template("register.html")


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash(_("Invalid credentials."), "error")
        else:
            login_user(user)
            flash(_("Welcome back!"), "success")
            return redirect(url_for("web.home"))
    return render_template("login.html")


@web_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash(_("You have been logged out."), "success")
    return redirect(url_for("web.home"))


@web_bp.get("/cart")
@login_required
def cart_page():
    return render_template("cart.html", cart_items=current_user.cart_items)


@web_bp.post("/cart/add/<int:book_id>")
@login_required
def cart_add(book_id):
    book = Book.query.get_or_404(book_id)
    qty = max(request.form.get("quantity", type=int, default=1), 1)
    item = CartItem.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if item:
        item.quantity += qty
    else:
        db.session.add(CartItem(user_id=current_user.id, book_id=book_id, quantity=qty))
    db.session.commit()
    flash(_("Book added to cart."), "success")
    return redirect(url_for("web.cart_page"))


@web_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    if request.method == "POST":
        shipping_address = request.form.get("shipping_address", "").strip()
        payment_method = request.form.get("payment_method", "mock")
        payment_token = request.form.get("payment_token")
        if not shipping_address:
            flash(_("Shipping address is required."), "error")
            return render_template("checkout.html", cart_items=current_user.cart_items)
        if not current_user.cart_items:
            flash(_("Your cart is empty."), "error")
            return render_template("checkout.html", cart_items=current_user.cart_items)

        total = Decimal("0.00")
        for item in current_user.cart_items:
            if item.quantity > item.book.stock_quantity:
                flash(_("Insufficient stock for %(title)s", title=item.book.title), "error")
                return render_template("checkout.html", cart_items=current_user.cart_items)
            total += Decimal(item.book.price) * item.quantity

        for item in list(current_user.cart_items):
            affected = (
                Book.query.filter(Book.id == item.book_id, Book.stock_quantity >= item.quantity)
                .update({Book.stock_quantity: Book.stock_quantity - item.quantity}, synchronize_session=False)
            )
            if affected == 0:
                db.session.rollback()
                flash(_("Insufficient stock for %(title)s", title=item.book.title), "error")
                return render_template("checkout.html", cart_items=current_user.cart_items)

        try:
            payment_reference = PaymentService.charge(float(total), payment_method, payment_token)
        except ValueError:
            db.session.rollback()
            flash(_("Invalid payment request."), "error")
            return render_template("checkout.html", cart_items=current_user.cart_items)

        order = Order(
            user_id=current_user.id,
            total_amount=total,
            shipping_address=shipping_address,
            payment_reference=payment_reference,
            status="paid",
        )
        db.session.add(order)
        db.session.flush()
        for item in list(current_user.cart_items):
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    book_id=item.book_id,
                    title_snapshot=item.book.title,
                    unit_price=item.book.price,
                    quantity=item.quantity,
                )
            )
            db.session.delete(item)
        db.session.commit()
        flash(_("Order created successfully."), "success")
        return redirect(url_for("web.orders"))

    return render_template("checkout.html", cart_items=current_user.cart_items)


@web_bp.get("/orders")
@login_required
def orders():
    return render_template(
        "orders.html",
        orders=Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all(),
    )


@web_bp.get("/profile")
@login_required
def profile():
    return render_template("profile.html")


@web_bp.get("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash(_("Admin access required."), "error")
        return redirect(url_for("web.home"))
    return render_template(
        "admin.html",
        book_count=Book.query.count(),
        category_count=Category.query.count(),
    )
