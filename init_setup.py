import json
import moltin
from tgbot import get_access_token


def main():
    with open('menu.json') as file:
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
        resp = moltin.set_main_image_relationship(get_access_token(), product_id, image_id)


if __name__ == '__main__':
    main()