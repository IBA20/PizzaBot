import os
from requests import get, post, delete
from slugify import slugify


def get_token() -> dict:
    url = 'https://api.moltin.com/oauth/access_token'
    data = {
        'client_id': os.getenv('CLIENT_ID'),
        'client_secret': os.getenv('CLIENT_SECRET'),
        'grant_type': 'client_credentials'
    }
    response = post(url, data=data)
    response.raise_for_status()
    return response.json()


def get_products(access_token: str) -> dict:
    url = 'https://api.moltin.com/v2/products'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_product(access_token: str, product_id: str) -> dict:
    url = f'https://api.moltin.com/v2/products/{product_id}'
    headers = {'Authorization': f'Bearer {access_token}'}
    product_response = get(url, headers=headers)
    product_response.raise_for_status()
    return product_response.json()['data']


def get_image_url(access_token: str, file_id: str) -> str:
    print('file_id', file_id)
    url = f'https://api.moltin.com/v2/files/{file_id}'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = get(url, headers=headers)
    print(response.json())
    response.raise_for_status()
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
    if response.status_code != 400:  # Insufficient stock returns status 400
        response.raise_for_status()
    return response.json()


def get_cart_items(access_token: str, cart_ref: str) -> dict:
    url = f'https://api.moltin.com/v2/carts/{cart_ref}/items'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def delete_cart_items(access_token: str, cart_id: str) -> None:
    url = f'https://api.moltin.com/v2/carts/{cart_id}/items'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = delete(url, headers=headers)
    response.raise_for_status()


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
    if response.status_code != 422:  # Failed email validation returns code 422
        response.raise_for_status()
    return response.status_code


def get_customer_by_email(access_token: str, email: str) -> dict:
    url = 'https://api.moltin.com/v2/customers'
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'filter': f'eq(email,{email})'}
    response = get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def create_product(access_token: str, product_data: dict) -> str:
    url = 'https://api.moltin.com/v2/products'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'data': {
            "type": "product",
            "name": product_data.get('name'),
            "slug": product_data.get('slug', slugify(product_data.get('name'))),
            "sku": product_data.get('sku'),
            "description": product_data.get('description', 'no description available'),
            "manage_stock": False,
            "price": [
                {
                    "amount": product_data.get('price'),
                    "currency": "RUB",
                    "includes_tax": True
                }
            ],
            "status": "live",
            "commodity_type": "physical",
        },
    }
    response = post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['data']['id']


def create_file(access_token: str, file_url: str) -> str:
    url = 'https://api.moltin.com/v2/files'
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    files = {
        'file_location': (None, file_url),
    }
    response = post(url, headers=headers, files=files)
    response.raise_for_status()
    return response.json()['data']['id']


def set_main_image_relationship(access_token: str, product_id: str, image_id: str):
    url = f'https://api.moltin.com/v2/products/{product_id}/relationships/main-image'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'data': {
            "type": "main_image",
            "id": f'{image_id}'
        },
    }
    response = post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_flows(access_token: str):
    url = 'https://api.moltin.com/v2/flows'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = get(url, headers=headers)
    response.raise_for_status()
    print(response.json())
