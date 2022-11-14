import json
import moltin
from tgbot import get_access_token
from dotenv import load_dotenv


def import_products_from_json():
    with open('menu.json', encoding="utf-8") as file:
        menu = json.load(file)
    for item in menu:
        product_data = {
            "name": item.get('name'),
            "sku": str(item.get('id')),
            "description": f"{item.get('description', 'no description available')}, вес: {item.get('food_value').get('weight', '?')}г",
            "price": item.get('price'),
        }
        image_url = item.get('product_image').get('url')
        product_id = moltin.create_product(get_access_token(), product_data)
        image_id = moltin.create_file(get_access_token(), image_url)
        moltin.set_main_image_relationship(
            get_access_token(), product_id, image_id
        )


def import_addresses_from_json():
    with open('addresses.json', encoding="utf-8") as file:
        pizzerias = json.load(file)
    for pizzeria in pizzerias:
        pizzeria_data = {
            'address': pizzeria['address']['full'],
            'alias': pizzeria['alias'],
            'lat': float(pizzeria['coordinates']['lat']),
            'lon': float(pizzeria['coordinates']['lon']),
        }
        moltin.create_pizzeria(get_access_token(), pizzeria_data)


def main():
    import_products_from_json()
    import_addresses_from_json()


if __name__ == '__main__':
    load_dotenv()
    main()