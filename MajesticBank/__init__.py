from __future__ import annotations

import logging
import re

import qrcode
from PIL import Image
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import CallbackContext

import MajesticBank.Style as Style
from MajesticBank.API import MajesticBankAPI
from MajesticBank.Decimal import octa_deci, is_numeric
from MajesticBank.Orders import MajesticBankOrders
from MajesticBank.Reply import Reply

# API_KEY = "5134897341:AAEeBpjicYa_e4uG2PEmjq6bcBQLZnlJM7s"  # MajesticBank_TESTBOT
API_KEY = "5212679859:AAFaxTSKUx7itdl2jYr7jeuZNvNHjDhOKQQ"  # MajesticBank_BOT

DEFAULT_REFERRAL_CODE = "mgzySX"
SUPPORTED_CURRENCIES = ["BTC", "LTC", "XMR"]
SUPPORTED_CURRENCIES_REGEX = re.compile(
    f"^({'|'.join(SUPPORTED_CURRENCIES)})$", re.IGNORECASE
)


class Commands:
    def __init__(self, start_updater: bool = True):
        self.supported_currencies = SUPPORTED_CURRENCIES

        currencies_list = "|".join(self.supported_currencies)
        currencies_list = f"^({currencies_list})$"
        self.currencies_regex = re.compile(f"{currencies_list}", re.IGNORECASE)

        self.API = MajesticBankAPI()
        self.orders = MajesticBankOrders(start_updater=start_updater)

        self.commands_assignment = None
        self.all_commands_help = None

    def get_referral_code(self, context: CallbackContext):
        chat_id = context.user_data["chat_id"]
        return DEFAULT_REFERRAL_CODE

    def set_commands_assignment(self, commands_assignment, all_commands_help):
        self.commands_assignment = commands_assignment
        self.all_commands_help = all_commands_help

    def __parse_ambigious_ordering(self, params: list) -> dict:
        """
        Helper to parse parameters when multiple orderings are permissible
        :param params: list of parameters in the message
        :return: dict with numeric parameter, its index, the other parameter
        """
        params_by_type = {}
        """
            try-except to see if number was provided first or second
            
            try succeeds example:
                /command 1 BTC XMR 
            
            try fails -> except executed example:
                /command BTC 1 XMR
        """
        if is_numeric(params[1]):
            params_by_type["numeric"] = octa_deci(params[1])
            params_by_type["numeric_idx"] = 1
            params_by_type["other"] = params[2]
        else:
            params_by_type["other"] = params[1]
            params_by_type["numeric"] = octa_deci(params[2])
            params_by_type["numeric_idx"] = 2

        return params_by_type

    def __currency_url_qr(self, currency: str, address: str, amount: Decimal):
        """
        Helper to create a BIP21 compatible url and a qr code
        :param currency:
        :param address:
        :param amount:
        :return:
        """
        url = None
        if currency == "BTC":
            url = "bitcoin:"
        elif currency == "LTC":
            url = "litecoin:"
        elif currency == "XMR":
            url = "monero:"
        else:
            return False, False

        url += address
        url += f"?amount={amount}"

        qr = qrcode.make(url)

        """
        by default qr would be of size 410x410
        however Telegram adjusts image height according to their width
        for this reason we pad the qr width so that the image doesn't appear as tall in the chat
        """
        width, height = qr.size
        pad_width, pad_height = 200, 0
        new_width = width + pad_width
        new_height = height + pad_height

        padded_qr = Image.new(mode=qr.mode, size=(new_width, new_height), color=255)
        padded_qr.paste(qr, (pad_width // 2, pad_height // 2))

        return url, padded_qr

    def __inline_keyboard_button(self, text, callback_data):
        return InlineKeyboardButton(text, callback_data=callback_data)

    def __inline_keyboard(self, rows):
        keyboard = []
        for row in rows:
            keyboard_row = []
            for button in row:
                keyboard_row.append(button)

            keyboard.append(keyboard_row)

        return InlineKeyboardMarkup(keyboard)

    def __reply_keyboard_button(self, text, callback_data):
        return KeyboardButton(text, callback_data=callback_data)

    def __reply_keyboard(self, rows):
        keyboard = []
        for row in rows:
            keyboard_row = []
            for button in row:
                keyboard_row.append(button)

            keyboard.append(keyboard_row)

        return ReplyKeyboardMarkup(keyboard)

    def start(self, params: list, context: CallbackContext) -> Reply:
        reply = Style.b("🙋 WELCOME 👋") + "\n\n"

        reply += Style.b("Make your first trade:")
        reply += " /trade" + "\n\n"

        reply += Style.b("Preview a trade:")
        reply += " /estimate" + "\n\n"

        reply += Style.b("See all your trades:")
        reply += " /track" + "\n\n"

        reply += Style.b("Customer support & manual:")
        reply += " /help" + "\n\n"

        if len(params) > 1:
            # activated when bot is added via link with trx such as:
            # https://t.me/majesticbank_bot?start=ABCDEF
            self.orders.insert(
                {
                    "chat_id": context.user_data["chat_id"],
                    "trx": params[1],
                    "status": "Just subscribed",
                }
            )
            reply += Style.b("🔔 UPDATES 🔔") + "\n\n"
            reply += (
                "Subscribed to updates for order: #" + Style.code(params[1]) + "\n\n"
            )

        reply_obj = Reply(reply)
        return reply_obj

    def help(self, params: list, context: CallbackContext) -> Reply:
        reply = Style.b("ℹ️️ HELP ℹ️️") + "\n\n"

        reply += Style.b("🪙 SUPPORTED CURRENCIES 🪙️️") + "\n"
        reply += ", ".join(self.supported_currencies) + "\n\n"

        reply += self.all_commands_help

        reply += Style.a("⛑️️️ CUSTOMER SUPPORT ⛑", "https://t.me/majesticsupport")

        return Reply(reply)

    def get_rates(self, params: list, context: CallbackContext) -> Reply:
        data = self.API.get_rates()
        del data["limits"]

        reply = Style.b("📈 RATES 📉") + "\n\n"
        for pair, rate in data.items():
            pair = pair.split("-")

            lhs = Style.code(f"1 {pair[0]}")
            rhs = Style.code(f"{rate} {pair[1]}")

            reply += f"{lhs} ➡️ {rhs}\n"
        return Reply(reply)

    def get_limits(self, params: list, context: CallbackContext) -> Reply:
        """
        Expecting: /get_limits BTC
        """
        from_currency = params[1]

        data = self.API.get_limits(from_currency)

        reply = Style.b("🤏 LIMITS 📏") + "\n\n"
        min_str = Style.code(f"{data['min']} {from_currency}")
        max_str = Style.code(f"{data['max']} {from_currency}")
        reply += f"Trades from {from_currency} to other currencies must be between {min_str} and {max_str}."

        return Reply(reply)

    def calculate_order(self, params: list, context: CallbackContext) -> Reply:
        """
        Expecting: /calculate_order 1 BTC XMR
            -or-
        Expecting: /calculate_order BTC 1 XMR

        """
        from_amount, from_currency, receive_amount = [None, None, None]
        receive_currency = params[3]

        params_by_type = self.__parse_ambigious_ordering(params)
        if params_by_type["numeric_idx"] == 1:
            from_amount = params_by_type["numeric"]
            from_currency = params_by_type["other"]

            data = self.API.calculate_order(
                from_currency=from_currency,
                receive_currency=receive_currency,
                from_amount=from_amount,
            )
            receive_amount = data["receive_amount"]

        elif params_by_type["numeric_idx"] == 2:
            from_currency = params_by_type["other"]
            receive_amount = params_by_type["numeric"]

            data = self.API.calculate_order(
                from_currency=from_currency,
                receive_currency=receive_currency,
                receive_amount=receive_amount,
            )
            from_amount = data["from_amount"]

        reply = Style.b("🧮 ESTIMATE 🧮") + "\n\n"
        lhs = Style.code(f"{from_amount} {from_currency}")
        rhs = Style.code(f"{receive_amount} {receive_currency}")
        reply += f"{lhs} ➡ {rhs}"

        recheck_button = self.__inline_keyboard_button(
            "🔄 Recheck", f"/estimate {from_amount} {from_currency} {receive_currency}"
        )
        keyboard = self.__inline_keyboard([[recheck_button]])
        return Reply(reply, reply_markup=keyboard)

    def create_order(self, params: list, context: CallbackContext) -> Reply:
        """
        Expecting: /create_order 1 BTC XMR [Monero_address]
        """
        from_amount = octa_deci(params[1])
        from_currency = params[2]
        receive_currency = params[3]
        receive_address = params[4]

        data = self.API.create_order(
            from_currency=from_currency,
            receive_currency=receive_currency,
            from_amount=from_amount,
            receive_address=receive_address,
            referral_code=self.get_referral_code(context),
        )
        receive_amount = data["receive_amount"]
        trx = data["trx"]
        address = data["address"]
        expiration = data["expiration"]

        reply = Style.b(f"⚖ ORDER #") + Style.code(trx) + "\n\n"

        lhs = Style.code(from_amount) + " " + Style.code(from_currency)
        rhs = Style.code(f"{receive_amount} {receive_currency}")
        reply += f"{lhs} ➡ {rhs}\n\n"

        reply += f"Send {lhs} to {Style.code(address)}\n\n"
        reply += f"Expires in {expiration} minutes\n\n"
        reply += f"You'll receive {rhs} at {Style.code(receive_address)}"

        url, qr = self.__currency_url_qr(from_currency, address, from_amount)

        check_button = self.__inline_keyboard_button("👀 Check status", f"/track {trx}")
        keyboard = self.__inline_keyboard([[check_button]])

        self.orders.insert({"chat_id": context.user_data["chat_id"], "trx": trx})
        return Reply(reply, reply_markup=keyboard, photo=qr)

    def create_fixed(self, params: list, context: CallbackContext) -> Reply:
        """
        Expecting: /create_fixed 1 BTC XMR [Monero_address]
            -or-
        Expecting: /create_fixed BTC 1 XMR [Monero_address]
        """
        from_amount, from_currency, receive_amount = [None, None, None]
        receive_currency = params[3]
        receive_address = params[4]

        data = {}
        params_by_type = self.__parse_ambigious_ordering(params)
        if params_by_type["numeric_idx"] == 1:
            from_amount = params_by_type["numeric"]
            from_currency = params_by_type["other"]

            data = self.API.create_fixed(
                from_currency=from_currency,
                receive_currency=receive_currency,
                from_amount=from_amount,
                receive_address=receive_address,
                referral_code=self.get_referral_code(context),
            )
            receive_amount = data["receive_amount"]

        elif params_by_type["numeric_idx"] == 2:
            from_currency = params_by_type["other"]
            receive_amount = params_by_type["numeric"]

            data = self.API.create_fixed(
                from_currency=from_currency,
                receive_currency=receive_currency,
                receive_amount=receive_amount,
                receive_address=receive_address,
                referral_code=self.get_referral_code(context),
            )
            from_amount = data["from_amount"]

        trx = data["trx"]
        address = data["address"]
        expiration = data["expiration"]

        reply = Style.b(f"🔒 FIXED ORDER #") + Style.code(trx) + "\n\n"

        lhs = Style.code(from_amount) + " " + Style.code(from_currency)
        rhs = Style.code(receive_amount) + " " + Style.code(receive_currency)
        reply += f"{lhs} ➡ {rhs}\n\n"

        reply += f"Send {lhs} to {Style.code(address)}\n\n"
        reply += f"Expires in {expiration} minutes\n\n"
        reply += f"You'll receive {rhs} at {Style.code(receive_address)}"

        url, qr = self.__currency_url_qr(from_currency, address, from_amount)

        check_button = self.__inline_keyboard_button("👀 Check status", f"/track {trx}")
        keyboard = self.__inline_keyboard([[check_button]])

        self.orders.insert({"chat_id": context.user_data["chat_id"], "trx": trx})
        return Reply(reply, reply_markup=keyboard, photo=qr)

    def track(self, params: list, context: CallbackContext) -> Reply:
        """
        Expecting: /track trx
        """

        if len(params) < 2:

            chat_id = context.user_data["chat_id"]
            orders = self.orders.select(chat_id)
            reply = Style.b(f"🧾 ORDERS 🧾") + "\n\n"

            if not orders:
                reply += "You don't have any open orders at the moment."
            else:
                for order in orders:
                    reply += Style.code(order["trx"]) + " " + order["status"]
                    reply += "\n"

                reply += "\n" + Style.b("For more details type:") + "\n"
                reply += "/track " + Style.code("[ORDER#]")

            return Reply(reply)

        else:
            trx = params[1]
            if trx[0] == "#":
                trx = trx[1:]

            data = self.API.track(trx=trx)

            status = data["status"]
            from_currency = data["from_currency"]
            from_amount = data["from_amount"]
            receive_currency = data["receive_currency"]
            receive_amount = data["receive_amount"]
            address = data["address"]
            received = data["received"]
            confirmed = data["confirmed"]

            reply = Style.b(f"ORDER #") + Style.code(trx) + "\n\n"
            reply += status + "\n\n"

            lhs = Style.code(from_amount) + " " + Style.code(from_currency)
            rhs = Style.code(receive_amount) + " " + Style.code(receive_currency)
            reply += f"{lhs} ➡ {rhs}\n\n"

            reply += f"Send {lhs} to {Style.code(address)}"

            qr = False
            url = ""
            if received == 0:
                url, qr = self.__currency_url_qr(from_currency, address, from_amount)

            all_button = self.__inline_keyboard_button("🧾 All orders", f"/track")
            keyboard = self.__inline_keyboard([[all_button]])
            return Reply(reply, reply_markup=keyboard, photo=qr)

    def none(self, params: list, context: CallbackContext) -> Reply:
        reply = Style.b("Message not understood!") + "\n\n"
        reply += f"Only messages beginning with {Style.code('/')} are understood by the bot.\n\n"
        reply += "Type /help to get the full list of supported commands."
        return Reply(reply)

    def invalid(self, params: list, context: CallbackContext) -> Reply:
        reply = Style.b("Command not found!") + "\n\n"
        reply += "Type /help to get the full list of supported commands."
        return Reply(reply)

    def error(self, params: list, context: CallbackContext) -> Reply:
        logger = logging.getLogger(__name__)
        logger.error(msg="Exception while handling an update:", exc_info=context.error)

        reply = Style.b("Something went wrong!") + "\n\n"
        reply += "Please try again later."
        return Reply(reply)
