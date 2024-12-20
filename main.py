import logging
from random import choice

from aiogram import Bot, Dispatcher, types
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup)
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv

from FSM_Classes import RegistrationStates, DriverReport
from bots_func import (get_main_menu, get_cancel,
                       get_location_keyboard,
                       get_confirmation_keyboard,
                       get_reason_keyboard,
                       get_zone_keyboard, get_reason_full_text,
                       save_user_data)
from database_functions import is_user_registered, register_user, is_admin, \
    ban_user, is_user_banned
from regexpes import gos_number_re, phone_number_re

from settings import (text_message_answers, DEV_TG_ID, database_path, log_file,
                      zones, reasons, API_TOKEN)
from textes_for_messages import new_user, reg_keyboard, start_process

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
        await message.reply(new_user, reply_markup=reg_keyboard)


@dp.message_handler(lambda message: message.text.startswith('ban'))
async def message_ban_user(message: types.Message):
    """
    Отрабатывает команду ban user_id.
    """
    user_id = message.from_user.id
    banned_id = int(message.text.split(' ')[1])
    if is_admin(database_path, user_id):
        ban_result = ban_user(database_path, banned_id)
        await message.reply(
            f"user {banned_id} ban result {ban_result}"
        )
    else:
        await message.reply("Неизвестная команда")


@dp.callback_query_handler(Text(equals="cancel"), state="*")
async def cancel_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает отмену через callback-кнопку."""
    await process_cancel(event=callback_query, state=state)


@dp.message_handler(Command("cancel"), state="*")
async def cancel_command(message: types.Message, state: FSMContext):
    """Обрабатывает отмену через команду /cancel."""
    await process_cancel(event=message, state=state)


async def process_cancel(event: types.CallbackQuery | types.Message, state: FSMContext):
    """Общая логика для обработки отмены."""
    current_state = await state.get_state()
    if current_state is not None:
        await state.finish()
        text = "Вы отменили текущую операцию. Давайте начнем заново."
    else:
        text = "Сейчас нечего отменять. Попробуйте использовать главное меню."

    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, reply_markup=get_main_menu())
        await event.answer()
    elif isinstance(event, types.Message):
        await event.answer(text, reply_markup=get_main_menu())



@dp.message_handler(commands=['reg'])
async def start_registration_command(message: types.Message):
    """Обработка команды /reg"""
    await process_registration(event=message)


###############################################################################
################# Машина состояний регистрация ################################
###############################################################################
@dp.callback_query_handler(Text(equals="register"))
async def start_registration_callback(callback_query: types.CallbackQuery):
    """Обработка нажатия кнопки с callback_data="register"."""
    await process_registration(event=callback_query)


async def process_registration(event: types.CallbackQuery | types.Message):
    """Общая логика регистрации для CallbackQuery и Message."""
    if isinstance(event, types.CallbackQuery):
        user_id = event.from_user.id
        message = event.message
    elif isinstance(event, types.Message):
        user_id = event.from_user.id
        message = event
    else:
        logging.warning("Unknown event type")
        return
    if is_user_banned(database_path, user_id):
        await message.answer("Ваш  ID  заблокирован.")
        return

    if is_user_registered(database_path, user_id):
        await message.answer("Вы уже зарегистрированы! "
                             "Воспользуйтесь меню \U0001F69B",
                             reply_markup=get_main_menu())
        return
    else:
        await message.answer(text=start_process +
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
                    regexp=phone_number_re)
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
    user_id = callback.from_user.id
    if is_user_registered(database_path, user_id):
        await callback.message.answer("Выберите Технологическую зону:",
                                      reply_markup=get_zone_keyboard(zones))
        await DriverReport.waiting_for_zone.set()
    else:
        await callback.message.answer(new_user,
                                      reply_markup=reg_keyboard)


@dp.callback_query_handler(state=DriverReport.waiting_for_zone)
async def process_zone(callback: types.CallbackQuery, state: FSMContext):
    zone = callback.data.split(":")[1]
    await state.update_data(user_id=callback.from_user.id)
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
        "Напишите госномер мусоровоза без пробелов тире и других лишних "
        "символов. Пример: Е777КХ124",
        reply_markup=get_cancel())
    await DriverReport.waiting_for_gos_number.set()


@dp.message_handler(state=DriverReport.waiting_for_gos_number,
                    regexp=gos_number_re)
async def get_gos_number(message: types.Message, state: FSMContext):
    await state.update_data(gos_number=message.text.upper())

    # Получаем все данные
    user_data = await state.get_data()
    confirmation_text = (
        f"Техзона: {user_data['zone']}\n"
        f"Геолокация: {user_data['latitude']}, {user_data['longitude']}\n"
        f"Причина: {user_data['reason']}\n"
        f"Госномер: {user_data.get('gos_number')}"
    )
    await message.answer_photo(photo=user_data['photo'],
                               caption=confirmation_text,
                               reply_markup=get_confirmation_keyboard())
    await DriverReport.confirmation.set()


@dp.message_handler(state=DriverReport.waiting_for_gos_number)
async def check_get_gos_number(message: types.Message):
    """Отрабатывает если госномер не соответствует паттерну"""
    await message.answer(
        "Русскими буквами напишите госномер мусоровоза "
        "без пробелов тире и других лишних символов. Пример: В414ТЕ124",
        reply_markup=get_cancel())


@dp.callback_query_handler(lambda callback: callback.data == "confirm",
                           state=DriverReport.confirmation)
async def confirm_data(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Информация принята. Спасибо!")
    user_data = await state.get_data()
    await state.finish()
    await save_user_data(user_data, bot)


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


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
