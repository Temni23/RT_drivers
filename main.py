import logging
import os
from random import choice

from aiogram import Bot, Dispatcher, types
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardRemove)
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
from datetime import datetime, timedelta

from FSM_Classes import RegistrationStates, DriverReport
from bots_func import (get_main_menu, get_cancel, get_location_keyboard,
                       get_confirmation_keyboard, get_reason_keyboard,
                       get_zone_keyboard, get_reason_full_text)
from database_functions import is_user_registered, register_user
from gps_functions import get_address_from_coordinates

from settings import (text_message_answers, YANDEX_CLIENT, YA_DISK_FOLDER,
                      DEV_TG_ID, GOOGLE_CLIENT, GOOGLE_SHEET_NAME,
                      database_path, log_file, TIMEDELTA, zones, reasons,
                      GPS_API_KEY)

load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # Формат записи
    handlers=[
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        # Логи в файл
        logging.StreamHandler()  # Логи в консоль
    ]
)

logger = logging.getLogger(__name__)  # Создаём объект логгера
logger.info("Логи будут сохраняться в файл: %s", log_file)

API_TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

dp.middleware.setup(LoggingMiddleware())


###############################################################################
################# Обработка команд ############################################
###############################################################################

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """
    Отрабатывает команду start.
    """
    user_id = message.from_user.id
    if is_user_registered(database_path, user_id):
        await message.reply("Добро пожаловать! "
                            "Воспользуйтесь меню \U0001F69B",
                            reply_markup=get_main_menu())
    else:
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Зарегистрироваться",
                                 callback_data="register")
        )
        await message.reply(
            "Добро пожаловать! Похоже, вы новый пользователь. "
            "Нажмите кнопку ниже для регистрации. "
            "Это не займет много времени \U0001F64F\U0001F64F\U0001F64F",
            reply_markup=keyboard
        )


@dp.callback_query_handler(lambda callback: callback.data == 'cancel',
                           state="*")
async def cmd_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    """
    Отрабатывает команду cancel и завершает текущее состояние.
    """
    current_state = await state.get_state()

    if current_state is not None:
        await state.finish()
        await callback.message.answer("Вы отменили текущую операцию. "
                                      "Давайте начнем заново",
                                      reply_markup=get_main_menu())
    else:
        await callback.message.answer(
            "Сейчас нечего отменять. Попробуйте использовать главное меню.",
            reply_markup=get_main_menu())

    await callback.answer()


##############################################################################
##################### Работа с сообщениями ####################################
##############################################################################

@dp.message_handler()
async def random_text_message_answer(message: types.Message) -> None:
    """
    Функция отправляет случайный ответ из предустановленного списка.

    На текстовое сообщение пользователя.
    """
    text = choice(text_message_answers)
    await message.reply(text=text, reply_markup=get_main_menu())


###############################################################################
################# Машина состояний регистрация ################################
###############################################################################

@dp.callback_query_handler(Text(equals="register"))
@dp.message_handler(Command("reg"))
async def start_registration(event: types.CallbackQuery | types.Message):
    if isinstance(event, types.CallbackQuery):
        user_id = event.from_user.id
        message = event.message
    elif isinstance(event, types.Message):
        user_id = event.from_user.id
        message = event
    else:
        # Если `event` не является `CallbackQuery` или `Message`
        logging.warning("Unknown event type")
        return

    if is_user_registered(database_path, user_id):
        await message.answer("Вы уже зарегистрированы! "
                             "Воспользуйтесь меню \U0001F69B",
                             reply_markup=get_main_menu())
    else:
        await message.answer(text="Начнем! \nОтветным сообщением направляйте"
                                  " мне нужную "
                                  "информацию, а я ее обработаю. "
                                  "\nПожалуйста, вводите "
                                  "верные данные, это очень важно для "
                                  "эффективность моей работы. \n\n"
                                  "1/2 Напишите Вашу Фамилию Имя и Отчество",
                             reply_markup=get_cancel())
    await RegistrationStates.waiting_for_full_name.set()


@dp.message_handler(lambda message: len(message.text) < 10,
                    state=RegistrationStates.waiting_for_full_name)
async def check_name(message: types.Message) -> None:
    """Проверяет ФИО на количество символов."""
    await message.answer(
        "Введите реальные ФИО в формате \n \U00002757 Фамилия Имя Отчество "
        "Это чрезвычайно важно.",
        reply_markup=get_cancel())


@dp.message_handler(state=RegistrationStates.waiting_for_full_name)
async def get_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer(
        '2/2 \U0000260E Введите номер своего контактного телефона через "8" без '
        'пробелов, тире и прочих лишних знаков. Например "89231234567"',
        reply_markup=get_cancel())
    await RegistrationStates.waiting_for_phone_number.set()


@dp.message_handler(state=RegistrationStates.waiting_for_phone_number,
                    regexp=r'^(8|\+7)[\- ]?\(?\d{3}\)?[\- ]?\d{3}[\- ]?\d{2}[\- ]?\d{2}$')
async def get_conformation(message: types.Message, state: FSMContext):
    await state.update_data(phone_number=message.text)
    user_data = await state.get_data()
    full_name = user_data['full_name']
    phone_number = user_data['phone_number']

    # Подтверждение данных перед регистрацией
    keyboad = get_cancel()
    keyboad.add(InlineKeyboardButton(text='ВСЕ ВЕРНО!', callback_data='Верно'))
    await message.answer(
        f"Проверьте информацию:\n"
        f"ФИО: {full_name}\n"
        f"Номер телефона: {phone_number}\n"
        f"Если все верно, нажмите 'ВСЕ ВЕРНО!'.", reply_markup=keyboad
    )
    await RegistrationStates.confirmation_application.set()


@dp.message_handler(state=RegistrationStates.waiting_for_phone_number)
async def check_phone(message: types.Message) -> None:
    """Проверяет номер телефона введенный пользователем."""
    await message.answer(
        "Введите корректный номер телефона без пробелов, скобок и тире."
        "Например: 89081234567",
        reply_markup=get_cancel())


@dp.callback_query_handler(lambda callback: callback.data == 'Верно',
                           state=RegistrationStates.confirmation_application)
async def confirm_registration(callback_query: types.CallbackQuery,
                               state: FSMContext):
    user_id = callback_query.from_user.id
    user_data = await state.get_data()
    full_name = user_data['full_name']
    phone_number = user_data['phone_number']
    username = callback_query.from_user.username

    try:
        register_user(database_path, user_id, full_name, phone_number,
                      username)
    except Exception as e:
        logging.error(e)
        await bot.send_message(DEV_TG_ID,
                               f"Произошла ошибка при регистрации пользователя "
                               f"{user_id}, {full_name}, {phone_number}, "
                               f"{username}")

    await callback_query.message.answer(
        "Вы успешно зарегистрированы и теперь можете пользоваться ботом!",
        reply_markup=get_main_menu()
    )
    await state.finish()
    await callback_query.answer("Регистрация завершена!")


##############################################################################
####################### Машина состояний заявка ##############################
##############################################################################

@dp.callback_query_handler(lambda callback: callback.data == "driver_report")
async def start_report(callback: types.CallbackQuery):
    await callback.message.answer("Выберите Технологическую зону:",
                                  reply_markup=get_zone_keyboard(zones))
    await DriverReport.waiting_for_zone.set()


@dp.callback_query_handler(state=DriverReport.waiting_for_zone)
async def process_zone(callback: types.CallbackQuery, state: FSMContext):
    zone = callback.data.split(":")[1]
    await state.update_data(zone=zone)
    await callback.message.answer("Отправьте геолокацию",
                                  reply_markup=get_location_keyboard())
    await DriverReport.waiting_for_location.set()


@dp.message_handler(content_types=['location'],
                    state=DriverReport.waiting_for_location)
async def process_location(message: types.Message, state: FSMContext):
    latitude = message.location.latitude
    longitude = message.location.longitude
    await state.update_data(latitude=latitude)
    await state.update_data(longitude=longitude)
    await message.answer("Идем дальше",
                         reply_markup=types.ReplyKeyboardRemove())
    try:
        await message.answer("Выберите причину:",
                             reply_markup=get_reason_keyboard(reasons=reasons))
    except Exception as e:
        print(e)
    await DriverReport.waiting_for_reason.set()


@dp.callback_query_handler(
    lambda callback: callback.data.startswith("reason:"),
    state=DriverReport.waiting_for_reason)
async def process_reason(callback: types.CallbackQuery, state: FSMContext):
    reason_callback = callback.data.split(":")[1]
    reason = get_reason_full_text(reasons, reason_callback)
    await state.update_data(reason=reason)
    await callback.message.answer("Пришлите фото:", reply_markup=get_cancel())
    await DriverReport.waiting_for_photo.set()


@dp.callback_query_handler(lambda callback: callback.data.startswith("page:"),
                           state=DriverReport.waiting_for_reason)
async def change_reason_page(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup(
        reply_markup=get_reason_keyboard(reasons=reasons, page=page))


@dp.message_handler(content_types=['photo'],
                    state=DriverReport.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await message.answer(
        "Добавьте комментарий или отправьте 'Нет' для пропуска:",
        reply_markup=get_cancel())
    await DriverReport.waiting_for_comment.set()


@dp.message_handler(state=DriverReport.waiting_for_comment)
async def process_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)

    # Получаем все данные
    user_data = await state.get_data()
    confirmation_text = (
        f"Техзона: {user_data['zone']}\n"
        f"Геолокация: {user_data['latitude']}, {user_data['longitude']}\n"
        f"Причина: {user_data['reason']}\n"
        f"Комментарий: {user_data.get('comment', 'Нет')}"
    )
    await message.answer_photo(photo=user_data['photo'],
                               caption=confirmation_text,
                               reply_markup=get_confirmation_keyboard())
    await DriverReport.confirmation.set()


@dp.callback_query_handler(lambda callback: callback.data == "confirm",
                           state=DriverReport.confirmation)
async def confirm_data(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Информация принята. Спасибо!")
    user_data = await state.get_data()
    address = get_address_from_coordinates(user_data['latitude'],
                                          user_data['longitude'], GPS_API_KEY)
    await callback.message.answer(f"Адрес: {address}")
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
