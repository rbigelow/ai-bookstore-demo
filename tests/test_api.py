def register_and_login(client, email="user@example.com", secret="Pass123!", full_name="Test User"):
    client.post(
        "/api/users/register",
        json={"email": email, "password": secret, "full_name": full_name},
    )
    return client.post("/api/users/login", json={"email": email, "password": secret})


def test_register_login_and_profile(client):
    response = client.post(
        "/api/users/register",
        json={"email": "alice@example.com", "password": "Pass123!", "full_name": "Alice"},
    )
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["email"] == "alice@example.com"

    login = client.post("/api/users/login", json={"email": "alice@example.com", "password": "Pass123!"})
    assert login.status_code == 200

    profile = client.get("/api/users/profile")
    assert profile.status_code == 200
    assert profile.get_json()["data"]["full_name"] == "Alice"


def test_books_list_with_filters(client):
    response = client.get("/api/books?page=1&per_page=10&language=English&sort=price&order=desc")
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["pagination"]["per_page"] == 10
    assert len(payload["items"]) <= 10


def test_cart_checkout_and_orders(client):
    register_and_login(client)

    books = client.get("/api/books?per_page=1").get_json()["data"]["items"]
    book_id = books[0]["id"]

    add_item = client.post("/api/cart/items", json={"book_id": book_id, "quantity": 2})
    assert add_item.status_code == 200

    checkout = client.post(
        "/api/orders",
        json={"shipping_address": "123 Main Street", "payment_method": "mock", "payment_token": "tok_test"},
    )
    assert checkout.status_code == 201
    order_id = checkout.get_json()["data"]["id"]

    orders = client.get("/api/orders")
    assert orders.status_code == 200
    assert orders.get_json()["data"]["items"][0]["id"] == order_id


def test_review_crud(client):
    register_and_login(client)
    book_id = client.get("/api/books?per_page=1").get_json()["data"]["items"][0]["id"]

    created = client.post(
        f"/api/books/{book_id}/reviews",
        json={"rating": 5, "comment": "Excellent read."},
    )
    assert created.status_code == 201
    review_id = created.get_json()["data"]["id"]

    updated = client.put(f"/api/reviews/{review_id}", json={"rating": 4, "comment": "Still great."})
    assert updated.status_code == 200
    assert updated.get_json()["data"]["rating"] == 4

    deleted = client.delete(f"/api/reviews/{review_id}")
    assert deleted.status_code == 200
