# Чат-боты на Python «Принимаем платежи за пиццу»

Учебный проект курса "От джуна до мидла" компании Devman.
[Пример работающего бота](https://t.me/suppservbot)  
![image](https://dvmn.org/media/filer_public/cd/20/cd20bd5b-d9f0-4e48-97df-0fd22c0e9921/pizza-bot.gif)

## Задание

Написать бота для Telegram, который позволяет оформлять заказы в интернет-магазине с использованием API [Elasticpath](https://www.elasticpath.com/) и принимать платежи.

## Установка и запуск

1. Клонируйте данный репозиторий.
2. Зарегистрируйтесь на [Elasticpath](https://www.elasticpath.com/) и создайте магазин с товарами.
3. Создайте следующие переменные окружения:  
* TGBOT_TOKEN - API ключ вашего телерам-бота. Создать бота и получить API ключ можно с помощью @BotFather.
* REDIS_URL - данные для доступа к базе Redis в формате redis://[[username]:[password]]@host:port/db_name
* CLIENT_ID, CLIENT_SECRET - ключи, предоставляемые зарегистрированным пользователям Elasticpath  
* DEFAULT_IMAGE_ID - id изображения по умолчанию, см. п.4. 
* COURIER_TG_ID - Telegram-ID курьера по умолчанию
* YANDEX_GEOCODER_APIKEY - см. [Документацию](https://yandex.ru/dev/maps/geocoder/)  
* PAYMENT_TOKEN - получить в меню Payments у @BotFather 
4. Выберите изображение по умолчанию (будет показываться для товаров, у которых нет изображений), загрузите его в любой товар и запишите ссылку на него. Она имеет вид `https://files-eu.epusercontent.com/client_id/file_id.jpg`. Сохраните file.id в переменную окружения DEFAULT_IMAGE_ID.
5. Настройте ваш интернет-магазин командой `python init_setup.py`  
6. Для тестирования загрузите тестовые данные командой `python load_test_data.py`  
7. Телеграм-бот запускается командой `python tgbot.py`  

## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).