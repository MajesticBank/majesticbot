"""
File defines a custom Router class to capture the various ways and contexts of interacting with the bot and process them
accordingly.
usually the handlers capture the message, prepare it a bit then send to router methods which route them accordingly
"""

from __future__ import annotations

import io
import re
from typing import List

import telegram
from PIL import Image
from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
)

import MajesticBank
from MajesticBank import Commands, Reply, Style, Conversation
from MajesticBank.Command import Command


class Router:
    def __init__(self, dispatcher):
        self.commands = Commands()

        start = Command("start", self.commands.start, parameter_counts=[1, 2])
        help = Command(
            "help",
            self.commands.help,
            docs={"description": "List of commands"},
            aliases=["support"],
        )
        rates = Command(
            "rates",
            self.commands.get_rates,
            docs={"description": "Current rates on all pairs"},
        )
        limits = Command(
            "limits",
            self.commands.get_limits,
            parameter_counts=[2],
            docs={
                "description": "Min & max trade amount for a currency",
                "usage": "[from currency]",
                "examples": "BTC",
            },
        )
        estimate = Command(
            "estimate",
            self.commands.calculate_order,
            aliases=["calculate"],
            parameter_counts=[1, 4],
            docs={
                "description": "Estimate a trade",
                "usage": "[from amount]? [from currency] [to amount]? [to currency]",
                "examples": ["", "1 BTC XMR", "BTC 1 XMR"],
            },
        )
        trade = Command(
            "trade",
            self.commands.create_order,
            aliases=["order", "swap"],
            parameter_counts=[1, 5],
            docs={
                "description": "Trade with a floating rate",
                "usage": "[from amount] [from currency] [to currency] [to currency address]",
                "examples": ["", "1 XMR BTC bc1..."],
            },
        )
        fixed = Command(
            "fixed",
            self.commands.create_fixed,
            aliases=["pay"],
            parameter_counts=[1, 5],
            docs={
                "description": "Trade with a fixed rate",
                "usage": "[from amount]? [from currency] [to amount]? [to currency] [to currency address]",
                "examples": ["", "1 XMR BTC bc1...", "XMR 0.1 BTC bc1..."],
            },
        )
        track = Command(
            "track",
            self.commands.track,
            aliases=["trades", "check", "orders"],
            parameter_counts=[1, 2],
            docs={
                "description": "Transaction status",
                "usage": "[Order#]?",
                "examples": ["", "#ABCDEFFG"],
            },
        )

        self.commands_assignment = {
            "start": start,
            "help": help,
            "rates": rates,
            "limits": limits,
            "estimate": estimate,
            "trade": trade,
            "fixed": fixed,
            "track": track,
        }

        # add commands to the dispatcher
        for command_name, command in self.commands_assignment.items():

            def command_interceptor(update: Update, context: CallbackContext):
                return self.command_handler(command_name, update, context)

            dispatcher.add_handler(CommandHandler(command_name, command_interceptor))

            if command.aliases:
                for alias in command.aliases:

                    def command_interceptor(update: Update, context: CallbackContext):
                        return self.command_handler(alias, update, context)

                    dispatcher.add_handler(CommandHandler(alias, command_interceptor))

        # callback handler
        dispatcher.add_handler(CallbackQueryHandler(self.callback_handler))

        # handle non commands & conversations & messages
        dispatcher.add_handler(
            MessageHandler(Filters.text & ~Filters.command, self.message_handler)
        )

        # photo handler
        dispatcher.add_handler(MessageHandler(Filters.photo, self.photo_handler))

        # handle invalid commands
        dispatcher.add_handler(
            MessageHandler(Filters.text & Filters.command, self.invalid_router)
        )

        # handle errors
        dispatcher.add_error_handler(self.error_router)

        self.commands.set_commands_assignment(
            self.commands_assignment, self.get_all_commands_help()
        )

        # register conversations
        self.trade_conversation = Conversation.trade_conversation
        trade_path_entry_regex = rf"^ */?({trade.name_and_aliases_regex()}|{fixed.name_and_aliases_regex()})$"
        self.trade_conversation.add_entry_regex(trade_path_entry_regex)
        Conversation.PATHS[Conversation.PATH_TRADE]["regex"] = trade_path_entry_regex

        estimate_path_entry_regex = rf"^ */?({estimate.name_and_aliases_regex()})$"
        self.trade_conversation.add_entry_regex(estimate_path_entry_regex)
        Conversation.PATHS[Conversation.PATH_ESTIMATE][
            "regex"
        ] = estimate_path_entry_regex

    def send_typing(self, chat_id):
        bot = telegram.Bot(MajesticBank.API_KEY)
        bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)

    def params(self, text: str) -> List[str]:

        if not text:
            return [""]

        # remove emoji from start of string
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002500-\U00002BEF"  # chinese char
            "\U00002702-\U000027B0"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001f926-\U0001f937"
            "\U00010000-\U0010ffff"
            "\u2640-\u2642"
            "\u2600-\u2B55"
            "\u200d"
            "\u23cf"
            "\u23e9"
            "\u231a"
            "\ufe0f"  # dingbats
            "\u3030"
            "]+",
            re.UNICODE,
        )
        text = re.sub(emoji_pattern, "", text)

        # strip whitespace at string start
        text = text.lstrip()

        # split into list
        if text[0] == "/":
            text = text[1:]
        params = text.split(" ")
        # Capitalize currency symbols
        for i in range(len(params)):
            if params[i].upper() in self.commands.supported_currencies:
                params[i] = params[i].upper()
        return params

    def get_all_commands_help(self) -> str:
        txt = ""
        for command_name, command in self.commands_assignment.items():
            txt += command.get_command_help()

        return txt

    def handle_missing_parameter(self, command_name: str) -> str:
        txt = Style.b("Missing parameters!") + "\n\n"
        txt += self.commands_assignment[command_name].get_command_help()
        return txt

    def get_command_by_name(self, needle_command_name: str) -> Command | bool:
        needle_command_name = needle_command_name.lower()
        for command_name, command_obj in self.commands_assignment.items():
            if needle_command_name in command_obj.name_and_aliases():
                return command_obj
        return False

    def callback_handler(self, update: Update, context: CallbackContext) -> int | None:
        context.user_data["chat_id"] = update.callback_query.message.chat_id

        query = update.callback_query
        query.answer(text="Loading...")
        callback_message = query.data

        return self.router(callback_message, context)

    def command_handler(
        self, command: str, update: Update, context: CallbackContext
    ) -> int | None:
        context.user_data["chat_id"] = update.message.chat_id
        message = update.message.text

        return self.router(message, context)

    def message_handler(self, update: Update, context: CallbackContext) -> int | None:

        chat_id = context.user_data["chat_id"] = update.message.chat_id
        self.send_typing(chat_id)

        message = update.message.text
        params = self.params(message)

        if "state" in context.user_data:
            # state is set, user is in conversation
            return self.trade_conversation.router(params, context)
        else:
            # no state
            if self.trade_conversation.check_entry_message(params):
                # no state -> conversation entry
                return self.trade_conversation.enter(params, context)
            else:
                # no state && not a conversation entry
                command_obj = self.get_command_by_name(params[0])
                if command_obj:
                    # a valid command without leading /
                    return self.router(message, context)
                else:
                    # not a valid command
                    return self.no_command_router(update, context)

    def photo_handler(self, update: Update, context: CallbackContext):
        photo_file = update.message.photo[-1].get_file()
        photo = photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo))

        context.user_data["photo"] = image
        self.message_handler(update, context)

    def no_command_router(self, update: Update, context: CallbackContext) -> None:
        chat_id = context.user_data["chat_id"] = update.message.chat_id
        self.send_typing(chat_id)
        reply = self.commands.none([], context)
        reply.add_navigation_keyboard()
        reply.send(chat_id)
        return None

    def invalid_router(self, update: Update, context: CallbackContext) -> None:
        chat_id = context.user_data["chat_id"] = update.message.chat_id
        self.send_typing(chat_id)
        reply = self.commands.invalid([], context)
        reply.add_navigation_keyboard()
        reply.send(chat_id)
        return None

    def error_router(self, update: Update, context: CallbackContext) -> None:
        chat_id = context.user_data["chat_id"] = update.message.chat_id
        self.send_typing(chat_id)
        reply = self.commands.error([], context)
        reply.add_navigation_keyboard()
        reply.send(chat_id)
        return None

    def router(self, message: str, context: CallbackContext) -> int | None:
        params = self.params(message)
        chat_id = context.user_data["chat_id"]
        self.send_typing(chat_id)

        command_obj = self.get_command_by_name(params[0])
        if (
            command_obj.parameter_counts
            and len(params) not in command_obj.parameter_counts
        ):
            # if invalid parameter count
            reply = Reply(command_obj.get_command_help())
            reply.send(chat_id)

        elif self.trade_conversation.check_entry_message(params):
            # if a starting point for a conversation
            self.trade_conversation.enter(params, context)

        else:

            if "state" in context.user_data:
                # if in the middle of a conversation then exit the conversation
                reply = Reply("Cancelled")
                reply.remove_reply_keyboard()
                reply.send(chat_id)
                context.user_data.clear()
                context.user_data["chat_id"] = chat_id

            reply = command_obj.callback(params, context)
            navigation_keyboard_sent = False
            if not reply.reply_markup:
                navigation_keyboard_sent = True
                reply.add_navigation_keyboard()
            reply.send(chat_id)

            if not navigation_keyboard_sent:
                Reply().send_navigation_keyboard_with_message(chat_id=chat_id)

        if "state" in context.user_data:
            return context.user_data["state"]
        else:
            return None
