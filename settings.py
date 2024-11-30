import os
import yadisk

from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from gspread import authorize

from app_functions.database_functions import init_db

load_dotenv()

# Настройка логирования
log_folder = 'logs'
log_file = os.path.join(log_folder, 'bot.log')

database_path = init_db('database', 'users.db')

API_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Создаем клиент яндекса
YANDEX_CLIENT = yadisk.Client(token=os.getenv('YA_DISK_TOKEN'))
YA_DISK_FOLDER = os.getenv('YA_DISK_FOLDER')

# Устанавливаем соединение с API Google
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    os.getenv('GSHEETS_KEY'), scope)
GOOGLE_CLIENT = authorize(credentials)
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME')

# Работа с GPS
GPS_API_KEY = os.getenv('GPS_API_KEY')

DEV_TG_ID = os.getenv('DEV_TG_ID')
TIMEDELTA = int(os.getenv('TIMEDELTA'))

text_message_answers = [
    'Я могу отвечать только на вопросы выбранные из меню. Воспользуйтесь им пожалуйста.',
    'Я не наделен искусственным интеллектом. Воспользуйтесь меню пожалуйста.',
    'Попробуйте найти Ваш вопрос в меню, оно закреплено под этим сообщением.',
    'Я был бы рад поболтать, но могу отвечать только на вопросы из меню. Воспользуйтесь меню пожалуйста.',
]

zones = ["Правобережная", "Левобережная", "Норильская", "Железногорская",
         "Зеленогорская", "Минусинская", "Таймырская"]

reasons = ['1. Нет баков', '2. Боковая загрузка(задняя загрузка)',
           '3. Заставлено машинами', '4. Закрыт шлагбаум, ворота',
           '5. Не по графику', '6. Не успел',
           '7. Пустые баки', '8. Дорожные условия(нет проезда)',
           '9. Бак сломан', '10. Нет потребителя на адресе',
           '11. Бак (к/ст) на замке', '12. Несуществующий адрес',
           '13. Потребитель "не отдает мусор"', '14. Не выкатили баки',
           '15. Вывез другой подрядчик', '16. Не подъемный бак',
           '17. Мусор тлеет (горит)', '18. Гололед',
           '19. Строит.мусор, шины, ветки и листья',
           '20. Не полный вывоз (замерз бак)']
