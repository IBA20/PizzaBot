# Чат-боты на Python «Продаём рыбу в Telegram»

Учебный проект курса "От джуна до мидла" компании Devman.
[Пример работающего бота](https://t.me/suppservbot)  
![image](https://dvmn.org/media/filer_public/0a/5b/0a5b562c-7cb4-43e3-b51b-1b61721200fb/fish-shop.gif)

## Задание

Написать бота для Telegram, который позволяет оформлять закакзы в интернет-магазине с использованием API [Elasticpath](https://www.elasticpath.com/). 

## Установка и запуск

1. Клонируйте данный репозиторий.
2. Зарегистрируйтесь на [Elasticpath](https://www.elasticpath.com/) и создайте магазин с товарами.
3. Создайте следующие переменные окружения:  
* TGBOT_TOKEN - API ключ вашего телерам-бота. Создать бота и получить API ключ можно с помощью @BotFather.
* REDIS_URL - данные для доступа к базе Redis в формате redis://[[username]:[password]]@host:port/db_name
* CLIENT_ID, CLIENT_SECRET - ключи, предоставляемые зарегистрированным пользователям Elasticpath  
* DEFAULT_IMAGE_ID - id изображения по умолчанию, см. п.4.  
4. Выберите изображение по умолчанию (будет показываться для товаров, у которых нет изображений), загрузите его в любой товар и запишите ссылку на него. Она имеет вид `https://files-eu.epusercontent.com/client_id/file_id.jpg`. Сохраните file.id в переменную окружения DEFAULT_IMAGE_ID.
5. Телеграм-бот запускается командой
```
python tgbot.py
```  

## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).