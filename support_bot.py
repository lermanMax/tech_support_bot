import logging
import typing

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils import callback_data
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Import modules of this project
from config import API_TOKEN, SUPPORT_CHAT_ID
from business_logic import Operator, SupportBot, TextMessage
from airtable_db import find_name_by_phone_test
from texts_for_replay import instruction_text, phone_found_text, \
    phone_not_found_text, help_text, instruction_how_use_support

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('support_bot')

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# Sructure of callback buttons
button_cb = callback_data.CallbackData(
    'btn', 'question_name', 'answer', 'data')

# Initialize business logic
support_bot = SupportBot()


#  -------------------------------------------------------------- ВХОД ТГ ЮЗЕРА
def get_empty_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    return keyboard


def get_phone_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        one_time_keyboard=True,
        resize_keyboard=True
    )
    keyboard.add(types.KeyboardButton(
        text='Отправить свой телефон 📞',
        request_contact=True)
    )
    return keyboard


class CustomerState(StatesGroup):
    waiting_for_contact = State()


@dp.message_handler(
    lambda message: message.chat.type == 'private',
    commands=['start'], state="*")
async def start_command(message: types.Message, state: FSMContext):
    log.info('start command from: %r', message.from_user.id)

    support_bot.add_tg_user(
        tg_id=message.from_user.id,
        tg_username=message.from_user.username
    )

    await CustomerState.waiting_for_contact.set()
    await message.answer(
        text=instruction_text,
        reply_markup=get_phone_keyboard())


@dp.message_handler(
    lambda message: message.chat.type == 'private',
    content_types=types.message.ContentType.CONTACT,
    state=CustomerState.waiting_for_contact)
async def new_contact(message: types.Message, state: FSMContext):
    log.info('new_contact from: %r', message.from_user.id)

    try:
        name = find_name_by_phone_test(phone=message.contact.phone_number)  # t
        customer = support_bot.add_customer(
            tg_id=message.from_user.id,
            phone=message.contact.phone_number
        )
        customer.change_first_name(name)
        await message.reply(
            text=phone_found_text,
            reply_markup=types.ReplyKeyboardRemove()
        )
        state.finish()
        await message.reply(
            text=instruction_how_use_support
        )
    except NameError:
        await message.answer(
            text=phone_not_found_text,
            reply_markup=get_phone_keyboard()
        )


@dp.message_handler(
    lambda message: message.chat.type == 'private',
    commands=['help'], state="*")
async def send_help(message: types.Message, state: FSMContext):
    log.info('help command from: %r', message.from_user.id)
    await message.answer(
        text=help_text,
        reply_markup=types.ReplyKeyboardRemove()
    )


#  ------------------------------------------------------------ ПРИЕМ ОБРАЩЕНИЙ
answered_button = 'Отвечено'
unanswered_button = 'Не отвечено'
ban_button = 'Бан'
unban_button = 'Забанен'


def make_inline_keyboard(
        question_name: str,
        answers: list,
        data=0) -> types.InlineKeyboardMarkup:
    """Возвращает клавиатуру для сообщений"""
    if not answers:
        return None

    keyboard = types.InlineKeyboardMarkup()
    row = []
    for answer in answers:  # make a botton for every answer
        cb_data = button_cb.new(
            question_name=question_name,
            answer=answer,
            data=data)
        row.append(types.InlineKeyboardButton(answer,
                                              callback_data=cb_data))
    if len(row) <= 2:
        keyboard.row(*row)
    else:
        for button in row:
            keyboard.row(button)

    return keyboard


def keyboard_for_message_in_support_chat(
        answers: list) -> types.InlineKeyboardMarkup:
    keyboard = make_inline_keyboard(
        question_name='customer_textmessage',
        answers=answers,
        data=0
    )
    return keyboard


@dp.message_handler(
    lambda message: message.chat.type == 'private',
    content_types=types.message.ContentType.TEXT)
async def new_text_message(message: types.Message, state: FSMContext):
    log.info('new_text_message_for_support from: %r', message.from_user.id)
    customer = support_bot.get_customer_by_tg_id(message.from_user.id)
    signature = (
        f'От: {customer.get_first_name()} {customer.get_last_name()}\n\n'
    )
    support_chat_msg = await bot.send_message(
        chat_id=SUPPORT_CHAT_ID,
        text=signature + message.text,
        reply_markup=keyboard_for_message_in_support_chat(
            [ban_button, unanswered_button])
    )
    support_bot.add_textmessage(
        tg_id=message.from_user.id,
        support_chat_message_id=support_chat_msg.message_id
    )


#  --------------------------------------------------------- ОТВЕТ НА ОБРАЩЕНИЕ
def get_keyboard_for_current_message(
        textmessage: TextMessage) -> types.InlineKeyboardMarkup:
    tg_user = textmessage.get_tg_user()

    if tg_user.is_banned():
        first_button = unban_button
    else:
        first_button = ban_button

    if textmessage.is_answered():
        second_button = answered_button
    else:
        second_button = unanswered_button

    keyboard = keyboard_for_message_in_support_chat(
        [first_button, second_button]
    )
    return keyboard


@dp.message_handler(
    lambda message: 'reply_to_message' in message,
    lambda message: message.chat.id == SUPPORT_CHAT_ID,
    content_types=types.message.ContentType.TEXT)
async def replay_on_message(message: types.Message, state: FSMContext):
    log.info('replay_on_message from: %r', message.from_user.id)
    msg_id = message.reply_to_message.message_id
    textmessage = support_bot.get_textmessage_by(
        support_chat_message_id=msg_id
    )

    # send answer to customer
    await bot.send_message(
        chat_id=textmessage.get_tg_id(),
        text=message.text
    )
    textmessage.mark_answered()

    # edit buttons under message in support chat
    await bot.edit_message_reply_markup(
        chat_id=SUPPORT_CHAT_ID,
        message_id=msg_id,
        reply_markup=get_keyboard_for_current_message(
            textmessage=textmessage
        )
    )


@dp.callback_query_handler(
    button_cb.filter(
        question_name=['customer_textmessage'],
        answer=[ban_button, unban_button]),
    state='*')
async def callback_ban(
        query: types.CallbackQuery,
        callback_data: typing.Dict[str, str],
        state: FSMContext):
    log.info('Got this callback data: %r', callback_data)

    textmessage = support_bot.get_textmessage_by(
        support_chat_message_id=query.message.message_id
    )
    tg_id = textmessage.get_tg_id()

    if callback_data['answer'] == ban_button:
        Operator.ban(tg_id=tg_id)
    elif callback_data['answer'] == unban_button:
        Operator.unban(tg_id=tg_id)

    await query.message.edit_reply_markup(
        reply_markup=get_keyboard_for_current_message(
            textmessage=textmessage
        )
    )


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)
