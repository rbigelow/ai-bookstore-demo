# API Documentation

Base URL: `/api`

All responses follow:

```json
{ "data": {}, "message": "...", "error": null }
```

## Authentication
- `POST /users/register`
- `POST /users/login`
- `POST /users/logout`
- `GET /users/profile`
- `PUT /users/profile`
- `GET /users` (admin)

## Categories
- `GET /categories`
- `GET /categories/{id}`
- `POST /categories` (admin)
- `PUT /categories/{id}` (admin)
- `DELETE /categories/{id}` (admin)

## Books
- `GET /books` supports `page`, `per_page`, `q`, `category_id`, `min_price`, `max_price`, `min_rating`, `language`, `sort`, `order`
- `GET /books/{id}`
- `POST /books` (admin)
- `PUT /books/{id}` (admin)
- `DELETE /books/{id}` (admin)

## Cart
- `GET /cart`
- `POST /cart/items`
- `PUT /cart/items/{id}`
- `DELETE /cart/items/{id}`

## Orders
- `POST /orders` (checkout)
- `GET /orders`
- `GET /orders/{id}`

## Reviews
- `GET /books/{id}/reviews`
- `POST /books/{id}/reviews`
- `PUT /reviews/{id}`
- `DELETE /reviews/{id}`

## Example Checkout Request
```json
{
  "shipping_address": "123 Main Street",
  "payment_method": "mock",
  "payment_token": "tok_test"
}
```
