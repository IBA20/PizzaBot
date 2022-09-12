import os
from requests import get, post, delete


def get_token() -> dict:
    url = 'https://api.moltin.com/oauth/access_token'
    data = {
        'client_id': os.getenv('CLIENT_ID'),
        'client_secret': os.getenv('CLIENT_SECRET'),
        'grant_type': 'client_credentials'
    }
    response = post(url, data=data)
    return response.json()


def get_products(access_token: str) -> dict:
    url = 'https://api.moltin.com/pcm/products'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = get(url, headers=headers)
    return response.json()


def get_product(access_token: str, product_id: str) -> tuple:
    url = f'https://api.moltin.com/pcm/products/{product_id}'
    headers = {'Authorization': f'Bearer {access_token}'}
    product_response = get(url, headers=headers)

    url = f'https://api.moltin.com/v2/inventories/{product_id}'
    stock_response = get(url, headers=headers)
    if stock_response.status_code == 404:
        available = 0
    else:
        available = stock_response.json()['data']['available']
    return product_response.json()['data'], available


def get_image_url(access_token: str, file_id: str) -> str:
    url = f'https://api.moltin.com/v2/files/{file_id}'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = get(url, headers=headers)
    return response.json()['data']['link']['href']


def add_product_to_cart(
        access_token: str, cart_ref: str, product_id: str, quantity: int
) -> dict:
    url = f'https://api.moltin.com/v2/carts/{cart_ref}/items'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        "data": {
            "id": product_id,
            "type": "cart_item",
            "quantity": quantity,
        }
    }
    response = post(url, headers=headers, json=payload)
    return response.json()


def get_cart_items(access_token: str, cart_ref: str) -> dict:
    url = f'https://api.moltin.com/v2/carts/{cart_ref}/items'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = get(url, headers=headers)
    return response.json()


def delete_cart_items(access_token: str, cart_id: str) -> None:
    url = f'https://api.moltin.com/v2/carts/{cart_id}/items'
    headers = {'Authorization': f'Bearer {access_token}'}
    delete(url, headers=headers)


def create_customer(access_token: str, name: str, email: str) -> int:
    url = 'https://api.moltin.com/v2/customers'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'data': {
            'type': 'customer',
            'name': str(name),
            'email': email,
        },
    }
    response = post(url, headers=headers, json=payload)
    return response.status_code


def get_customer_by_email(access_token: str, email: str) -> dict:
    url = f'https://api.moltin.com/v2/customers?filter=eq(email,{email})'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = get(url, headers=headers)
    return response.json()


def get_pricebook_id(access_token: str) -> str:
    url = 'https://api.moltin.com/pcm/catalogs'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = get(url, headers=headers)
    return response.json()['data'][0]['attributes']['pricebook_id']


def get_all_prices(access_token: str, pricebook_id: str) -> dict:
    url = f'https://api.moltin.com/pcm/pricebooks/{pricebook_id}/prices'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = get(url, headers=headers)
    pricelist = {
        position['attributes']['sku']: position['attributes']['currencies']['USD']['amount'] / 100
        for position in response.json()['data']
    }
    return pricelist
    