"""

В модуле собраны функция формирующие клавиатуры для работы бота.

Также функция для отправки почты.

"""

from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardMarkup, KeyboardButton)

from dotenv import load_dotenv

from api_functions import (upload_and_get_link,
                           upload_information_to_gsheets)
from database_functions import get_user_by_id, save_driver_report
from gps_functions import (get_address_from_coordinates,
    parse_data_from_gps_dict)
from settings import (DEV_TG_ID, YANDEX_CLIENT, YA_DISK_FOLDER, GPS_API_KEY,
                      GOOGLE_CLIENT, GOOGLE_SHEET_NAME, database_path,
                      TIMEDELTA)

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


async def save_user_data(data: dict, tg_bot: Bot):
    gs_data = []
    address_dict = []
    try:
        gs_data = list(
            get_user_by_id(data.get('user_id'), database_path).values())
    except Exception as e:
        await tg_bot.send_message(DEV_TG_ID,
                                  f"Произошла ошибка {e} при поиске пользователя {data}.")
        return
    print(data)
    try:
        downloaded_file = await download_photo(data.get('photo'), tg_bot)
        ya_disk_file_name = upload_and_get_link(YANDEX_CLIENT, downloaded_file,
                                                YA_DISK_FOLDER)
        data.update({'ya_disk_file_name': ya_disk_file_name})
    except Exception as e:
        await tg_bot.send_message(DEV_TG_ID,
                                  f"Произошла ошибка {e} при загрузке фото {data}.")
        return
    try:
        address = get_address_from_coordinates(data.get('latitude'),
                                               data.get('longitude'),
                                               GPS_API_KEY)
        address_dict = parse_data_from_gps_dict(address)
    except Exception as e:
        await tg_bot.send_message(DEV_TG_ID,
                                  f"Произошла ошибка {e} при получении адреса {data}.")
        return
    try:
        del data['photo']
        gs_data.extend(list(data.values()))
        if address_dict:
            gs_data.extend(list(address_dict.values()))
        gs_data.insert(0, (datetime.now() + timedelta(hours=TIMEDELTA)).strftime(
        "%Y-%m-%d %H:%M:%S"))
        print(gs_data)
        upload_information_to_gsheets(GOOGLE_CLIENT, GOOGLE_SHEET_NAME,
                                      gs_data)
    except Exception as e:
        await tg_bot.send_message(DEV_TG_ID,
                                  f"Произошла ошибка {e} при загрузке ифнормации {gs_data}.")
        return
    try:
        save_driver_report(database_path, gs_data)
    except Exception as e:
        await tg_bot.send_message(DEV_TG_ID,
                                  f"Произошла ошибка {e} при сохраненнии в БД ифнормации {gs_data}.")
        return