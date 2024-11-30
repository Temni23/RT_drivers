"""

В модуле собраны функция формирующие клавиатуры для работы бота.

Также функция для отправки почты.

"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, \
    ReplyKeyboardMarkup, KeyboardButton

from dotenv import load_dotenv

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
        keyboard.add(InlineKeyboardButton(text=zone, callback_data=f"zone:{zone}"))
    return keyboard


def get_location_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    location_button = KeyboardButton("📍 Отправить геолокацию", request_location=True)
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
            InlineKeyboardButton(reason, callback_data=f"reason:{reason[:reason.find('.')+1]}"))

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
