from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

new_user = ("Добро пожаловать! Похоже, вы новый пользователь. "
            "Нажмите кнопку ниже для регистрации. "
            "Это не займет много времени \U0001F64F\U0001F64F\U0001F64F")
reg_keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton(
    "Зарегистрироваться",
    callback_data="register"))
start_process = ("Начнем! \nОтветным сообщением направляйте"
                 " мне нужную "
                 "информацию, а я ее обработаю. "
                 "\nПожалуйста, вводите "
                 "верные данные, это очень важно для "
                 "эффективность моей работы. \n\n")
