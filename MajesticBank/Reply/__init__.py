"""
File defines a Reply class the instances of which are used to pass a Reply with its state, photos etc all around the app

"""

from __future__ import annotations

import io

import telegram
from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import MajesticBank


class Reply:
    def __init__(
        self, html_reply: str = None, photo=None, reply_markup=None, state=None
    ):
        self.html_reply = html_reply
        self.photo = photo
        self.reply_markup = reply_markup
        self.state = state
        self.bot = telegram.Bot(MajesticBank.API_KEY)

    def send(self, chat_id: int) -> None:

        if self.photo:
            with io.BytesIO() as output:
                self.photo.save(output, format="PNG")
                contents = output.getvalue()
                self.bot.send_photo(
                    photo=contents,
                    chat_id=chat_id,
                    caption=self.html_reply,
                    reply_markup=self.reply_markup,
                    parse_mode="HTML",
                )
        else:
            self.bot.send_message(
                chat_id=chat_id,
                text=self.html_reply,
                reply_markup=self.reply_markup,
                parse_mode="HTML",
            )

    def set_reply_keyboard(self, rows: list = ReplyKeyboardRemove()):

        if rows == ReplyKeyboardRemove():
            self.reply_markup = rows
            return None
        keyboard = []
        for row in rows:
            keyboard_row = []
            for button in row:
                if isinstance(button, str):
                    keyboard_row.append(
                        KeyboardButton(
                            text=button,
                        )
                    )
                elif isinstance(button, dict):
                    keyboard_row.append(
                        KeyboardButton(
                            text=button["text"],
                        )
                    )

            keyboard.append(keyboard_row)
        self.reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def add_navigation_keyboard(self):
        self.set_reply_keyboard(
            [["🧮 Estimate", "⚖ Trade"], ["⛑ Help", "🧾 Orders", "📈 Rates"]]
        )

    def send_navigation_keyboard_with_message(self, chat_id: int):
        self.html_reply = "Navigate with buttons ↘️"
        self.add_navigation_keyboard()
        self.send(chat_id=chat_id)

    def remove_reply_keyboard(self):
        self.reply_markup = ReplyKeyboardRemove()

    def append(self, addition: str | Reply, new_line_count: int = 2):
        if isinstance(addition, str):
            self.html_reply += new_line_count * "\n" + addition
        elif isinstance(addition, Reply):
            self.html_reply += new_line_count * "\n" + addition.html_reply

    def __str__(self):
        return self.html_reply
