def test_categories_page_renders(client):
    response = client.get('/categories')
    assert response.status_code == 200
    assert b'Categories' in response.data


def test_orders_page_requires_auth(client):
    response = client.get('/orders')
    assert response.status_code in (302, 401)


def test_orders_page_for_authenticated_user(client):
    client.post(
        '/api/users/register',
        json={'email': 'webuser@example.com', 'password': 'Pass123!', 'full_name': 'Web User'},
    )
    client.post('/api/users/login', json={'email': 'webuser@example.com', 'password': 'Pass123!'})

    response = client.get('/orders')
    assert response.status_code == 200
    assert b'Orders' in response.data


def test_web_register_post_creates_user(client):
    response = client.post(
        "/register",
        data={"full_name": "Web Reg", "email": "webreg@example.com", "password": "Pass123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Registration successful" in response.data


def test_web_login_post_authenticates_user(client):
    client.post(
        "/api/users/register",
        json={"email": "weblogin@example.com", "password": "Pass123!", "full_name": "Web Login"},
    )
    response = client.post(
        "/login",
        data={"email": "weblogin@example.com", "password": "Pass123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
