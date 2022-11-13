import moltin
import os
from tgbot import get_access_token


def create_pizzeria_flow():
    flow_id = moltin.create_flow(
        get_access_token(),
        name='Pizzeria',
        slug='pizzeria',
        description='Stores pizzeria data',
    )
    fields = [
        {'name': 'Address', 'slug': 'address', 'type': 'string'},
        {'name': 'Alias', 'slug': 'alias', 'type': 'string'},
        {'name': 'Latitude', 'slug': 'lat', 'type': 'float'},
        {'name': 'Longitude', 'slug': 'lon', 'type': 'float'},
        {'name': 'Courier Telegram ID', 'slug': 'couriertg', 'type': 'string'},
    ]
    for field in fields:
        moltin.create_field(
            get_access_token(),
            name=field['name'],
            slug=field['slug'],
            type=field['type'],
            flow_id=flow_id,
        )
    moltin.create_field(
        get_access_token(),
        name='Courier Telegram ID',
        slug='couriertg',
        type='string',
        flow_id=flow_id,
        default=os.getenv("COURIER_TG_ID"),
    )


def create_customer_address_flow():
    flow_id = moltin.create_flow(
        get_access_token(),
        name='CustomerAddress',
        slug='customer_address',
        description='Stores customer delivery addresses',
    )
    fields = [
        {'name': 'Telegram ID', 'slug': 'tg_id', 'type': 'string'},
        {'name': 'Address', 'slug': 'address', 'type': 'string'},
        {'name': 'Latitude', 'slug': 'lat', 'type': 'float'},
        {'name': 'Longitude', 'slug': 'lon', 'type': 'float'},
    ]
    for field in fields:
        moltin.create_field(
            get_access_token(),
            name=field['name'],
            slug=field['slug'],
            type=field['type'],
            flow_id=flow_id,
        )


def main():
    create_pizzeria_flow()
    create_customer_address_flow()


if __name__ == '__main__':
    main()