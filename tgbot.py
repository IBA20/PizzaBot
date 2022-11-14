import os
import logging
import redis
import time
import json

import requests
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, ReplyKeyboardRemove,
)
from telegram import ParseMode
from telegram.ext import Filters, Updater, PreCheckoutQueryHandler
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from textwrap import dedent
from dotenv import load_dotenv

import moltin
from geofunctions import fetch_coordinates, get_distance


logger = logging.getLogger(__file__)
_database = None


def token_generator():
    token_response = moltin.get_token()
    expires = token_response['expires']
    token = token_response['access_token']
    while True:
        if expires < time.time() + 60:
            print('new token acquired at', time.ctime())
            token_response = moltin.get_token()
            expires = token_response['expires']
            token = token_response['access_token']
        yield token


def get_access_token():
    return next(token_generator())


def show_cart(bot, update):
    db = get_database_connection()
    query = update.callback_query
    cart_items = moltin.get_cart_items(
        get_access_token(), query.message.chat_id
    )
    total = cart_items['meta']['display_price']['with_tax']['amount']
    cart_summary = dedent(
        ''.join(
            [f"""
            {number}. {cart_item['name']}:
            В корзине: {cart_item['quantity']}
            Сумма: {cart_item['meta']['display_price']['with_tax']['value']['formatted']}
            """
             for number, cart_item in enumerate(cart_items['data'], 1)
             ]
        )
    )
    cart_summary += f'\n*Всего: ₽{total}*'
    db.set(f'{query.message.chat_id}_cart_summary', cart_summary)
    keyboard = [[InlineKeyboardButton('В магазин', callback_data='menu')]]
    if total > 0:
        keyboard += [
            [InlineKeyboardButton('Изменить', callback_data='change')],
            [InlineKeyboardButton('Очистить корзину', callback_data='clear')],
            [InlineKeyboardButton('Оформить заказ', callback_data='checkout')],
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        cart_summary,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )


def show_menu(bot, update, callback=True, offset=0):
    if callback:
        query = update.callback_query
    else:
        query = update
    products = moltin.get_products(get_access_token(), offset=offset)
    keyboard = []
    for product in products['data']:
        price = product['price'][0]['amount']
        if price and product['status'] == 'live':
            keyboard.append(
                [InlineKeyboardButton(
                    f"{product['name']}: ₽{price:.2f}",
                    callback_data=f"{product['id']}:{price:.2f}"
                )]
            )
    page = products['meta']['page']
    if page['total'] > 1:
        if page['current'] == 1:
            keyboard.append([InlineKeyboardButton(
                '>>>', callback_data=page['offset'] + page['limit'],
            )])
        elif 1 < page['current'] < page['total']:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        '<<<',
                        callback_data=page['offset'] - page['limit'],
                    ),
                    InlineKeyboardButton(
                        '>>>',
                        callback_data=page['offset'] + page['limit']
                    ),
                ]
            )
        elif page['current'] == page['total']:
            keyboard.append([InlineKeyboardButton(
                '<<<', callback_data=page['offset'] - page['limit'],
            )])

    keyboard.append([InlineKeyboardButton('Корзина', callback_data='cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.message.reply_text(
        'Пожалуйста, выберите пиццу:',
        reply_markup=reply_markup
    )
    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )


def start(bot, update, job_queue):
    update.message.reply_text(
        'Добро пожаловать!',
        reply_markup=ReplyKeyboardRemove()
    )
    show_menu(bot, update, callback=False)
    return "HANDLE_MENU"


def handle_menu(bot, update, job_queue):
    db = get_database_connection()
    query = update.callback_query
    if query.data == 'cart':
        show_cart(bot, update)
        return 'HANDLE_CART'
    elif query.data.isdigit():
        show_menu(bot, update, offset=int(query.data))
        return "HANDLE_MENU"
    product_id, price = query.data.split(':')
    product = moltin.get_product(get_access_token(), product_id)
    main_image = product['relationships']['main_image']['data']
    if main_image:
        image_id = main_image['id']
    else:
        image_id = os.getenv('DEFAULT_IMAGE_ID')
    image_url = moltin.get_image_url(get_access_token(), image_id)
    description = f"{product.get('name')}\n" \
                  f"{product.get('description', 'нет описания')}"
    keyboard = [
        [InlineKeyboardButton('Купить', callback_data=1)],
        [InlineKeyboardButton('Назад', callback_data='menu')],
        [InlineKeyboardButton('Корзина', callback_data='cart')],
    ]
    product_context = {
        "id": product["id"], "description": description, "price": price
    }
    db.set(
        f'{query.message.chat_id}_product_context', json.dumps(product_context)
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_photo(
        chat_id=query.message.chat_id,
        photo=image_url,
        caption=f'{description}\n₽{price}',
        reply_markup=reply_markup,
    )
    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )
    return 'HANDLE_DESCRIPTION'


def handle_description(bot, update, job_queue):
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
        product = json.loads(
            db.get(f'{query.message.chat_id}_product_context').decode()
        )

        cart_items = moltin.add_product_to_cart(
            get_access_token(), query.message.chat_id, product['id'], quantity
        ).get('data')
        if not cart_items:
            bot.answer_callback_query(
                callback_query_id=query.id,
                text='Что-то пошло не так..',
                show_alert=True
            )
            return 'HANDLE_DESCRIPTION'
        in_cart = 0
        for item in cart_items:
            if item['product_id'] == product['id']:
                in_cart = item['quantity']
        keyboard = [
            [InlineKeyboardButton('Купить', callback_data=1)],
            [InlineKeyboardButton('Назад', callback_data='menu')],
            [InlineKeyboardButton('Корзина', callback_data='cart')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.edit_message_caption(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            caption=f'{product["description"]}\n₽{product["price"]}\n\nВ корзине: {in_cart}',
            reply_markup=reply_markup,
        )
        return 'HANDLE_DESCRIPTION'


def handle_cart(bot, update, job_queue):
    db = get_database_connection()
    query = update.callback_query
    if query.data == 'menu':
        show_menu(bot, update)
        return "HANDLE_MENU"
    elif query.data == 'change':
        show_change_cart(bot, update, job_queue)
        return "HANDLE_CHANGE_CART"
    elif query.data == 'clear':
        moltin.delete_cart_items(get_access_token(), query.message.chat_id)
        show_menu(bot, update)
        return "HANDLE_MENU"
    elif query.data == 'checkout':
        cart_summary = db.get(f'{query.message.chat_id}_cart_summary').decode()
        bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=cart_summary,
            parse_mode=ParseMode.MARKDOWN
        )
        update.callback_query.message.reply_text(
            'Сообщите, пожалуйста, ваш адрес или пришлите геолокацию'
        )
        return 'WAITING_ADDRESS'


def show_change_cart(bot, update, job_queue):
    query = update.callback_query
    cart_items = moltin.get_cart_items(
        get_access_token(), query.message.chat_id
    )
    total = cart_items['meta']['display_price']['with_tax']['formatted']
    keyboard = []
    for item in cart_items['data']:
        keyboard.append([InlineKeyboardButton(
            f"{item['name']}\n{item['quantity']} шт. на сумму "
            f"{item['meta']['display_price']['with_tax']['value']['formatted']}",
            callback_data='none'
        )])
        keyboard.append([
            InlineKeyboardButton(
                '-', callback_data=f"{item['quantity'] - 1}:{item['id']}"
            ),
            InlineKeyboardButton(
                '.............................', callback_data=' '
            ),
            InlineKeyboardButton(
                '+', callback_data=f"{item['quantity'] + 1}:{item['id']}"
            ),
        ])

    keyboard.append([InlineKeyboardButton('Готово', callback_data='cart')])

    cart_summary = f'\nВсего: {total}'
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(
        cart_summary,
        reply_markup=reply_markup,
    )
    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )


def handle_change_cart(bot, update, job_queue):
    query = update.callback_query
    if query.data[0].isdigit():
        quantity, item_id = query.data.split(':')
        moltin.update_cart_item(
            get_access_token(),
            query.message.chat_id,
            item_id,
            int(quantity),
        )
        show_change_cart(bot, update, job_queue)
    elif query.data == 'cart':
        show_cart(bot, update)
        return 'HANDLE_CART'
    
    return "HANDLE_CHANGE_CART"


def handle_address(bot, update, job_queue):
    db = get_database_connection()
    message = update.message
    delivery_data = {
        'cost': 0, 'address': 'not provided'
    }
    if message.location:
        current_pos = (message.location.latitude, message.location.longitude)
    else:
        try:
            current_pos = fetch_coordinates(
                message.text, os.getenv('YANDEX_GEOCODER_APIKEY')
            )
            assert current_pos != (None, None)
            delivery_data['address'] = message.text
        except requests.HTTPError:
            update.message.reply_text(
                'Ошибка определения координат. Попробуйте еще раз'
            )
            return 'WAITING_ADDRESS'
        except AssertionError:
            update.message.reply_text(
                'Адрес не найден. Попробуйте еще раз'
                )
            return 'WAITING_ADDRESS'

    pizzerias = moltin.get_pizzerias(get_access_token())['data']
    distances = [
        {
            'address': pizzeria['address'],
            'couriertg': pizzeria['couriertg'],
            'distance': get_distance(
                current_pos,
                (pizzeria['lat'], pizzeria['lon'])
            )
        } for pizzeria in pizzerias
    ]
    nearest = min(distances, key=lambda x: x['distance'])
    delivery_data['location'] = current_pos
    delivery_data['pizzeria'] = nearest
    msg = f"Ближайшая пиццерия находится по адресу: {nearest['address']}."
    keyboard = [[InlineKeyboardButton('Самовывоз', callback_data='pickup')]]
    if nearest['distance'] < 0.5:
        keyboard[0].append(
            InlineKeyboardButton('Доставка', callback_data='delivery:0')
        )
        msg += " Вы можете забрать заказ самостоятельно " \
            "или выбрать бесплатную доставку"
    elif nearest['distance'] < 5:
        keyboard[0].append(InlineKeyboardButton(
            'Доставка +100₽', callback_data=f'delivery:100'
        ))
        delivery_data['cost'] = 100
        msg += " Вы можете забрать заказ самостоятельно " \
            "или заказать доставку за 100₽."
    elif nearest['distance'] < 20:
        keyboard[0].append(
            InlineKeyboardButton('Доставка +300₽', callback_data='delivery:300')
        )
        delivery_data['cost'] = 300
        msg += " Вы можете забрать заказ самостоятельно " \
            "или заказать доставку за 300₽."
    else:
        keyboard[0].append(
            InlineKeyboardButton('Отмена', callback_data='cancel')
        )
        msg += " Возможен только самовывоз."

    db.set(f'delivery_data_{message.chat_id}', json.dumps(delivery_data))

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        msg,
        reply_markup=reply_markup,
    )

    return 'HANDLE_DELIVERY'


def handle_delivery(bot, update, job_queue):
    query = update.callback_query
    if query.data in ('cancel', 'pickup'):
        msg = 'Ждем вас!'
        if query.data == 'cancel':
            moltin.delete_cart_items(get_access_token(), query.message.chat_id)
            msg = 'Заказ отменен'
        reply_markup = ReplyKeyboardMarkup(
            [[KeyboardButton(text="/start")]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        query.message.reply_text(msg, reply_markup=reply_markup)
        bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
        return 'START'
    elif query.data.startswith('delivery'):
        delivery_cost = int(query.data.split(':')[1])
        cart_items = moltin.get_cart_items(
            get_access_token(), query.message.chat_id
        )
        prices = [LabeledPrice(
            f"{item['name']}, {item['quantity']}шт.",
            item['value']['amount'] * 100
        ) for item in cart_items['data']]
        if delivery_cost:
            prices.append(LabeledPrice('Доставка', delivery_cost * 100))
        bot.send_invoice(
            chat_id=query.message.chat_id,
            title='Заказ пиццы',
            description='Стоимость заказа',
            payload=query.message.chat_id,
            provider_token=os.getenv('PAYMENT_TOKEN'),
            start_parameter='test-payment',
            currency='RUB',
            prices=prices,
        )

        bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
        return 'HANDLE_PRECHECKOUT'


def ask_feedback(bot, job):
    keyboard = [[
        InlineKeyboardButton('Да', callback_data='yes'),
        InlineKeyboardButton('Нет', callback_data='no')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(
        job.context,
        'Сообщите, пожалуйста, вы получили заказ?',
        reply_markup=reply_markup,
    )


def handle_feedback(bot, update, job_queue):
    query = update.callback_query
    if query.data == 'yes':
        moltin.delete_cart_items(get_access_token(), query.message.chat_id)
        msg = 'Надеемся, что вам понравились наши пиццы!'
    elif query.data == 'no':
        msg = dedent(
            '''
            Приносим свои извинения за задержку! 
            В качестве компенсации данный заказ будет для вас бесплатным!
            '''
        )
    else:
        return 'HANDLE_FEEDBACK'
    query.message.reply_text(
        msg,
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(text="/start")]],
            resize_keyboard=True
        )
    )
    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )
    return 'START'


def handle_precheckout(bot, update, job_queue):
    query = update.pre_checkout_query
    if query.invoice_payload != str(query.from_user.id):
        bot.answer_pre_checkout_query(
            pre_checkout_query_id=query.id, ok=False,
            error_message="Something went wrong..."
            )
        return 'HANDLE_PRECHECKOUT'
    else:
        bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)
    return 'HANDLE_RECEIPT'


def handle_success_payment(bot, update, job_queue):
    db = get_database_connection()
    query = update
    delivery_data = json.loads(
        db.get(f'delivery_data_{query.message.chat_id}').decode("utf-8")
    )
    moltin.create_customer_address(
        get_access_token(),
        address=delivery_data['address'],
        lat=float(delivery_data['location'][0]),
        lon=float(delivery_data['location'][1]),
        tg_id=query.message.chat_id,
    )

    msg = db.get(
        f'{query.message.chat_id}_cart_summary'
    ).decode("utf-8")
    msg += f'\nСтоимость доставки: {delivery_data["cost"]}₽'
    msg += f'\n[Связаться с клиентом](tg://user?id={query.message.chat_id})'

    bot.send_message(
        delivery_data['pizzeria']['couriertg'],
        msg,
        parse_mode=ParseMode.MARKDOWN
    )
    bot.send_location(
        delivery_data['pizzeria']['couriertg'],
        latitude=float(delivery_data['location'][0]),
        longitude=float(delivery_data['location'][1]),

    )

    job_queue.run_once(ask_feedback, 3600, context=query.message.chat_id)
    query.message.reply_text(
        f'Оплата ₽{query.message.successful_payment.total_amount / 100:.2f} получена. '
        f'Спасибо за заказ! Ожидайте курьера в ближайшее время.'
    )
    return 'HANDLE_FEEDBACK'


def handle_users_reply(bot, update, job_queue):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    elif update.pre_checkout_query:
        user_reply = ''
        chat_id = update.pre_checkout_query.from_user.id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start, 'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description, 'HANDLE_CART': handle_cart,
        'HANDLE_CHANGE_CART': handle_change_cart,
        'WAITING_ADDRESS': handle_address, 'HANDLE_DELIVERY': handle_delivery,
        'HANDLE_FEEDBACK': handle_feedback, 'HANDLE_PRECHECKOUT': handle_precheckout,
        'HANDLE_RECEIPT': handle_success_payment,
    }
    state_handler = states_functions[user_state]
    # Если вы вдруг не заметите, что python-telegram-bot перехватывает ошибки.
    # Оставляю этот try...except, чтобы код не падал молча.
    # Этот фрагмент можно переписать.
    try:
        next_state = state_handler(bot, update, job_queue)
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

    updater = Updater(os.getenv("TGBOT_TOKEN"))
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CallbackQueryHandler(
        handle_users_reply, pass_job_queue=True
    ))
    dispatcher.add_handler(PreCheckoutQueryHandler(
            handle_users_reply, pass_job_queue=True
    ))
    dispatcher.add_handler(MessageHandler(
        Filters.successful_payment, handle_users_reply, pass_job_queue=True
    ))
    dispatcher.add_handler(MessageHandler(
        Filters.location, handle_users_reply, pass_job_queue=True
    ))
    dispatcher.add_handler(MessageHandler(
        Filters.text, handle_users_reply, pass_job_queue=True
    ))
    dispatcher.add_handler(CommandHandler(
        'start', handle_users_reply, pass_job_queue=True
    ))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    load_dotenv()
    main()
