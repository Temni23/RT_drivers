"""

В модуле собраны функция формирующие клавиатуры для работы бота.

Также функция для отправки почты.

"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, \
    ReplyKeyboardMarkup, KeyboardButton

from dotenv import load_dotenv

from app_functions.api_functions import upload_and_get_link, \
    upload_information_to_gsheets
from app_functions.database_functions import get_user_by_id
from app_functions.gps_functions import get_address_from_coordinates, \
    parse_data_from_gps_dict
from models import UserData
from settings import DEV_TG_ID, YANDEX_CLIENT, YA_DISK_FOLDER, GPS_API_KEY, \
    GOOGLE_CLIENT, GOOGLE_SHEET_NAME, database_path

load_dotenv()


async def download_photo(file_id: str, bot) -> bytes:
    """Получает file_id возвращает от телеграмма файл в bytes."""
    file = await bot.get_file(file_id)
    file_path = file.file_path
    # Загружаем файл в bytes
    photo_bytes = await bot.download_file(file_path)
    return photo_bytes


def get_cancel() -> InlineKeyboardMarkup:
    """Формирует и возвращает Inline клавиатуру с одной кнопкой Отмена."""
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text='Отмена', callback_data='cancel')
    keyboard.add(button)
    return keyboard


def get_main_menu() -> InlineKeyboardMarkup:
    """Формирует и возвращает Inline клавиатуру, главное меню.

    Направить обращение
    """
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text='Направить информацию о невывозе',
                                  callback_data='driver_report')
    keyboard.add(button)
    return keyboard


def get_zone_keyboard(zones: list[str]):
    keyboard = InlineKeyboardMarkup()
    for zone in zones:
        keyboard.add(
            InlineKeyboardButton(text=zone, callback_data=f"zone:{zone}"))
    return keyboard


def get_location_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True,
                                   one_time_keyboard=True)
    location_button = KeyboardButton("📍 Отправить геолокацию",
                                     request_location=True)
    keyboard.add(location_button)
    return keyboard


def get_reason_keyboard(reasons: list[str], page=0):
    reasons_per_page = 7
    start = page * reasons_per_page
    end = start + reasons_per_page
    reasons_page = reasons[start:end]

    keyboard = InlineKeyboardMarkup(row_width=1)
    for reason in reasons_page:
        reason.find('.')
        keyboard.add(
            InlineKeyboardButton(reason,
                                 callback_data=f"reason:{reason[:reason.find('.') + 1]}"))

    # Добавляем кнопки "⬅ Назад" и "➡ Далее"
    navigation_buttons = []
    if start > 0:
        navigation_buttons.append(
            InlineKeyboardButton("⬅ Назад", callback_data=f"page:{page - 1}"))
    if end < len(reasons):
        navigation_buttons.append(
            InlineKeyboardButton("➡ Далее", callback_data=f"page:{page + 1}"))

    if navigation_buttons:
        keyboard.row(*navigation_buttons)

    return keyboard


def get_reason_full_text(reasons: list, part: str) -> str | None:
    for reason in reasons:
        if reason.startswith(part):
            return reason
    return None


def get_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Подтвердить", callback_data="confirm"),
        InlineKeyboardButton("Отмена", callback_data="cancel")
    )
    return keyboard


async def send_email(message_text, target_email):
    """Отправляет письмо на заданную почту."""
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD_EMAIL")
    time = datetime.now()

    msg = MIMEMultipart()
    msg['From'] = email
    msg['To'] = target_email
    msg[
        'Subject'] = (f"Новое обращение принято ботом "
                      f"{time.strftime('%Y-%m-%d %H:%M')}")
    msg.attach(MIMEText(message_text))
    try:
        mailserver = smtplib.SMTP('smtp.yandex.ru', 587)

        mailserver.ehlo()
        # Защищаем соединение с помощью шифрования tls
        mailserver.starttls()
        # Повторно идентифицируем себя как зашифрованное соединение
        # перед аутентификацией.
        mailserver.ehlo()
        mailserver.login(email, password)

        mailserver.sendmail(email, target_email, msg.as_string())

        mailserver.quit()
    except smtplib.SMTPException:
        print("Ошибка: Невозможно отправить сообщение")


async def save_user_data(data: dict, tg_bot: Bot):
    gs_data = []
    address_dict = []
    try:
        gs_data = list(
            get_user_by_id(data.get('user_id'), database_path).values())
    except Exception as e:
        await tg_bot.send_message(DEV_TG_ID,
                                  f"Произошла ошибка {e} при поиске пользователя.")
        return
    print(data)
    try:
        downloaded_file = await download_photo(data.get('photo'), tg_bot)
        ya_disk_file_name = upload_and_get_link(YANDEX_CLIENT, downloaded_file,
                                                YA_DISK_FOLDER)
        data.update({'ya_disk_file_name': ya_disk_file_name})
    except Exception as e:
        await tg_bot.send_message(DEV_TG_ID,
                                  f"Произошла ошибка {e} при загрузке фото.")
        return
    try:
        address = get_address_from_coordinates(data.get('latitude'),
                                               data.get('longitude'),
                                               GPS_API_KEY)
        address_dict = parse_data_from_gps_dict(address)
    except Exception as e:
        await tg_bot.send_message(DEV_TG_ID,
                                  f"Произошла ошибка {e} при получении адреса.")
        return
    try:
        del data['photo']
        gs_data.extend(list(data.values()))
        if address_dict:
            gs_data.extend(list(address_dict.values()))
        print(gs_data)
        upload_information_to_gsheets(GOOGLE_CLIENT, GOOGLE_SHEET_NAME,
                                      gs_data)
    except Exception as e:
        await tg_bot.send_message(DEV_TG_ID,
                                  f"Произошла ошибка {e} при загрузке ифнормации.")
        return
