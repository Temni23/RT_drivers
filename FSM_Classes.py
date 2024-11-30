"""Классы для машины состояний."""
from aiogram.dispatcher.filters.state import StatesGroup, State


class DriverReport(StatesGroup):
    """Класс для отправки репорта."""
    waiting_for_zone = State()
    waiting_for_location = State()
    waiting_for_reason = State()
    waiting_for_photo = State()
    waiting_for_comment = State()
    confirmation = State()


class RegistrationStates(StatesGroup):
    """Класс для регистрации водителя."""
    waiting_for_full_name = State()
    waiting_for_phone_number = State()
    confirmation_application = State()
