import os
import logging
import redis
import time
import moltin
import json

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from textwrap import dedent
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__file__)
_database = None


def get_config():
    with open('config.json') as file:
        return json.load(file)


def get_access_token():
    db = get_database_connection()
    expires = db.get('moltin_expires')
    if expires and int(expires.decode()) > time.time() + 60:
        return db.get('moltin_token').decode()
    token_data = moltin.get_token()
    db.set('moltin_expires', token_data['expires'])
    token = token_data['access_token']
    db.set('moltin_token', token)
    return token


def show_cart(bot, update):
    db = get_database_connection()
    query = update.callback_query
    cart_items = moltin.get_cart_items(
        get_access_token(), query.message.chat_id
    )
    total = cart_items['meta']['display_price']['with_tax']['formatted']
    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )
    cart_summary = dedent(
        ''.join(
            [f"""
            {n}. {el['name']}:
            in cart: {el['quantity']}
            sum: {el['meta']['display_price']['with_tax']['value']['formatted']}
            """
             for n, el in enumerate(cart_items['data'], 1)
             ]
        )
    )
    cart_summary += f'\nTotal: {total}'
    db.set(f'{query.message.chat_id}_cart_summary', cart_summary)
    keyboard = [
        [InlineKeyboardButton('В магазин', callback_data='menu')],
        [InlineKeyboardButton('Очистить корзину', callback_data='clear')],
        [InlineKeyboardButton('Оплатить', callback_data='pay')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(
        cart_summary,
        reply_markup=reply_markup,
    )


def show_menu(bot, update, callback=True):
    db = get_database_connection()
    if callback:
        query = update.callback_query
    else:
        query = update
    products = moltin.get_products(get_access_token())['data']
    pricelist = moltin.get_all_prices(get_access_token(), db.get('moltin_pricebook_id').decode())
    keyboard = [
        [
            InlineKeyboardButton(
                f"{product['attributes']['name']}: ${pricelist.get(product['attributes']['sku']):.2f}/kg",
                callback_data=f"{product['id']}:{pricelist.get(product['attributes']['sku']):.2f}"
            )
        ] for product in products 
        if product['attributes']['status'] == 'live' 
        and pricelist.get(product['attributes']['sku'])
    ]
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )
    query.message.reply_text(
        'Please choose:',
        reply_markup=reply_markup
    )


def start(bot, update):
    show_menu(bot, update, callback=False)
    return "HANDLE_MENU"


def handle_menu(bot, update):
    db = get_database_connection()
    query = update.callback_query
    if query.data == 'cart':
        show_cart(bot, update)
        return 'HANDLE_CART'
    product_id, product_price = query.data.split(':')
    product, stock = moltin.get_product(get_access_token(), product_id)
    main_image = product['relationships']['main_image']['data']
    if main_image:
        image_id = main_image['id']
    else:
        image_id = get_config()['default_image_id']
    image_url = moltin.get_image_url(get_access_token(), image_id)
    description = product['attributes'].get(
        'description',
        'no description for this product'
    )
    keyboard = [
        [InlineKeyboardButton('Назад', callback_data='menu')],
        [InlineKeyboardButton('Корзина', callback_data='cart')],
    ]
    if stock <= 0:
        description += '\nВРЕМЕННО НЕТ В ПРОДАЖЕ'
    else:
        db.set(f'{query.message.chat_id}_product_in_work_id', product['id'])
        db.set(
            f'{query.message.chat_id}_product_in_work_description', description
        )
        keyboard.insert(
            0,
            [InlineKeyboardButton('1kg', callback_data=1),
             InlineKeyboardButton('5kg', callback_data=5),
             InlineKeyboardButton('20kg', callback_data=20)]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )
    bot.send_photo(
        chat_id=query.message.chat_id,
        photo=image_url,
        caption=f'{description}\n${product_price}/kg',
        reply_markup=reply_markup,
    )
    return 'HANDLE_DESCRIPTION'


def handle_description(bot, update):
    db = get_database_connection()
    query = update.callback_query
    if query.data == 'menu':
        show_menu(bot, update)
        return "HANDLE_MENU"
    elif query.data == 'cart':
        show_cart(bot, update)
        return 'HANDLE_CART'
    else:
        quantity = int(query.data)
        product_id = db.get(
            f'{query.message.chat_id}_product_in_work_id'
        ).decode()
        description = db.get(
            f'{query.message.chat_id}_product_in_work_description'
        ).decode()

        cart_items = moltin.add_product_to_cart(
            get_access_token(), query.message.chat_id, product_id, quantity
        ).get('data')
        if not cart_items:
            bot.answer_callback_query(
                callback_query_id=query.id,
                text='Недостаточно товара на складе',
                show_alert=True
            )
            return 'HANDLE_DESCRIPTION'
        in_cart = 0
        for item in cart_items:
            if item['product_id'] == product_id:
                in_cart = item['quantity']
        keyboard = [
            [InlineKeyboardButton('1kg', callback_data=1),
             InlineKeyboardButton('5kg', callback_data=5),
             InlineKeyboardButton('20kg', callback_data=20)
             ],
            [InlineKeyboardButton('Назад', callback_data='menu')],
            [InlineKeyboardButton('Корзина', callback_data='cart')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.edit_message_caption(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            caption=f'{description}\n\nIn cart: {in_cart}',
            reply_markup=reply_markup,
        )
        return 'HANDLE_DESCRIPTION'


def handle_cart(bot, update):
    db = get_database_connection()
    query = update.callback_query
    if query.data == 'menu':
        show_menu(bot, update)
        return "HANDLE_MENU"
    elif query.data == 'clear':
        moltin.delete_cart_items(get_access_token(), query.message.chat_id)
        show_menu(bot, update)
        return "HANDLE_MENU"
    elif query.data == 'pay':
        cart_summary = db.get(f'{query.message.chat_id}_cart_summary').decode()
        bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=cart_summary,
        )
        update.callback_query.message.reply_text(
            'Сообщите, пожалуйста, email для связи с вами'
        )
        return 'WAITING_EMAIL'


def ask_email(bot, update):
    if not update.message:
        return 'WAITING_EMAIL'

    customers = moltin.get_customer_by_email(
        get_access_token(),
        update.message.text,
    ).get('data', [])
    message_text = 'Спасибо за заказ!'
    if not customers:
        create_code = moltin.create_customer(
            get_access_token(),
            update.message.chat_id,
            update.message.text,
        )
        if create_code == 201:
            message_text += f'\nПокупатель с email {update.message.text} ' \
                           f'успешно добавлен в базу'
        elif create_code == 422:
            update.message.reply_text('Некорректный email, повторите ввод')
            return 'WAITING_EMAIL'
    else:
        customer = customers[0]
        if customer['name'] != str(update.message.chat_id):
            update.message.reply_text('Такой email уже используется')
            return 'WAITING_EMAIL'

    update.message.reply_text(message_text)
    return 'START'


def handle_users_reply(bot, update):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start, 'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description, 'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': ask_email
    }
    state_handler = states_functions[user_state]
    # Если вы вдруг не заметите, что python-telegram-bot перехватывает ошибки.
    # Оставляю этот try...except, чтобы код не падал молча.
    # Этот фрагмент можно переписать.
    try:
        next_state = state_handler(bot, update)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis,
    либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        _database = redis.Redis(
            connection_pool=redis.ConnectionPool.from_url(
                os.environ['REDIS_URL']
            )
        )
    return _database


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    db = get_database_connection()
    pricebook_id = moltin.get_pricebook_id(get_access_token())
    db.set('moltin_pricebook_id', pricebook_id)
    
    updater = Updater(os.getenv("TGBOT_TOKEN"))
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
