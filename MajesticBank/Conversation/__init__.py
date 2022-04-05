"""
This file defines the State and Conversation classes.
It also creates a trade_conversation instance of the Conversation class
"""

from __future__ import annotations

import copy
import logging
import re
from re import Pattern
from typing import List, Dict
from urllib.parse import urlparse

from pyzbar.pyzbar import decode
from telegram.ext import CallbackContext

import MajesticBank
from MajesticBank import Reply, Decimal, Style


class State:
    def __init__(self,
                 message: str,
                 context: CallbackContext,

                 reply_text: str = "",
                 reply_parameters: list = None,

                 next_state: int = None,

                 response_validation: str | Pattern = None,
                 response_set_key: str = None,
                 ):

        # the message received - reply to the previous state
        self.message = message
        # context variable
        self.context = context
        # chat_id to respond to
        self.chat_id = self.get("chat_id")

        # reply class containing the text, parameters and a Reply class with formatted text
        self.reply = type('reply', (object,), {})
        self.reply.text = reply_text
        self.reply.parameters = reply_parameters
        self.reply.object = None

        # next state after current one
        self.next_state = next_state

        # regex to validate the reply to this state in the future state
        self.future_state_validation = response_validation
        self.current_state_validation = self.get("future_state_validation")
        self.set("future_state_validation", self.future_state_validation)

        # key in context[key] to set the reply to this state to
        self.future_state_set_key = response_set_key
        self.current_state_set_key = self.get("future_state_set_key")
        self.set("future_state_set_key", self.future_state_set_key)

        # flag to communicate success or failure
        self.success = True
        # Commands class to reuse code
        self.commands = MajesticBank.Commands(start_updater=False)

    def set(self, key, value):
        """
        Sets data in the context variable
        :param key: key for the new value
        :param value: new value
        :return: value
        """
        self.context.user_data[key] = value
        return value

    def get(self, key):
        """
        Gets data in the context variable
        :param key: key for the variable
        :return: context[key] or None
        """
        if key in self.context.user_data:
            return self.context.user_data[key]
        return None

    def message_valid(self):
        """
        :return: Returns if the message is of the expected kind (for ex. a number)
        """
        if self.current_state_validation:
            return re.match(self.current_state_validation, self.message)
        return True

    def set_response(self, value=None):
        if self.message_valid():
            if value:
                self.set(self.current_state_set_key, value)
            else:
                self.set(self.current_state_set_key, self.message)

    def reply_compile(self):
        """
        Formats reply.text with reply.parameters.
        Sets Reply obj into reply.object
        :return: Reply object with formatted text
        """

        text = self.reply.text

        if self.reply.parameters:
            parameters = []
            for p in self.reply.parameters:
                parameters.append(self.get(p))

            text = text.format(*parameters)

        self.reply.object = Reply(text)
        return self.reply.object

    def reply_keyboard_currencies_row(self, exclude_key_values: List[str] = None):
        """
        Creates a row of currency buttons with ability to exclude a list of symbols
        :param exclude_key_values: Currency to be excluded from keyboard
        :return: Row of buttons
        """
        row = []

        excluded_currencies = []
        if exclude_key_values:
            for exclusion in exclude_key_values:
                excluded_currencies.append(self.get(exclusion))

        for currency in MajesticBank.SUPPORTED_CURRENCIES:
            if currency in excluded_currencies:
                continue
            row.append({
                "text": currency,
            })
        return row

    def reply_keyboard_control_row(self, back_button: bool = True):
        """
        Creates a keyboard row with control buttons (back, cancel)
        :param back_button: Whether to add a back button True by default
        :return: Row of control buttons
        """
        row = []
        if back_button:
            row.append({
                "text": "↩ Back",
            })
        row.append({
            "text": "❌ Cancel",
        })
        return row

    def set_next_state(self):
        """
        Sets the next state based on the path the user is on
        :return: The next state
        """
        current_state = self.get("state")
        path_states = PATHS[self.get("path")]["states"]
        current_state_index = path_states.index(current_state)

        next_state_index = current_state_index + 1

        if next_state_index < len(path_states):
            self.next_state = path_states[next_state_index]
        else:
            self.next_state = None


REQUEST_FROM_CURRENCY, \
REQUEST_RECEIVE_CURRENCY, \
REQUEST_EXCHANGE_TYPE, \
REQUEST_AMOUNT, \
PREVIEW_ESTIMATE, \
REQUEST_RECEIVE_ADDRESS, \
CREATE_ORDER = range(7)

STATES = {}

PATH_ESTIMATE, PATH_TRADE = range(2)
PATHS = {PATH_ESTIMATE: {}, PATH_TRADE: {}}

# order of states to take the user through depending on the path selected
PATHS[PATH_TRADE]["states"] = [REQUEST_FROM_CURRENCY, REQUEST_RECEIVE_CURRENCY, REQUEST_EXCHANGE_TYPE, REQUEST_AMOUNT,
                               REQUEST_RECEIVE_ADDRESS, CREATE_ORDER]
PATHS[PATH_ESTIMATE]["states"] = [REQUEST_FROM_CURRENCY, REQUEST_RECEIVE_CURRENCY, REQUEST_AMOUNT, PREVIEW_ESTIMATE,
                                  REQUEST_RECEIVE_ADDRESS, CREATE_ORDER]

"""
Every state is its own class which inherits from the generic State class
They differ only in the constructor
All constructors end with setting the self.reply.object which the Conversation class will send
"""


class FromCurrency(State):
    def __init__(self, message: str, context: CallbackContext):
        super().__init__(message,
                         context,
                         reply_text="What currency do you want to sell?",

                         response_validation=MajesticBank.SUPPORTED_CURRENCIES_REGEX,
                         response_set_key="from_currency",
                         )

        self.set_next_state()
        self.reply_compile()

        keyboard = [
            self.reply_keyboard_currencies_row(),
            self.reply_keyboard_control_row(back_button=False)
        ]
        self.reply.object.set_reply_keyboard(keyboard)

"""
After the state class is defined we assign it (not its instance!) to the States dict on the key corresponding to the state
"""
STATES[REQUEST_FROM_CURRENCY] = FromCurrency


class ReceiveCurrency(State):
    def __init__(self, message: str, context: CallbackContext):
        super().__init__(message,
                         context,
                         reply_text="What currency do you want to buy with {}?",
                         reply_parameters=["from_currency"],

                         response_validation=MajesticBank.SUPPORTED_CURRENCIES_REGEX,
                         response_set_key="receive_currency",
                         )

        if not self.message_valid():
            self.success = False
        self.set_response()

        self.set_next_state()
        if self.get("path") == PATH_ESTIMATE:
            self.set("fixed", "No")

        self.reply_compile()

        keyboard = [
            self.reply_keyboard_currencies_row(["from_currency"]),
            self.reply_keyboard_control_row()
        ]
        self.reply.object.set_reply_keyboard(keyboard)


STATES[REQUEST_RECEIVE_CURRENCY] = ReceiveCurrency


class ExchangeType(State):
    def __init__(self, message: str, context: CallbackContext):
        super().__init__(message,
                         context,
                         reply_text=f"Do you want to receive a specific amount of {{}}?\n\nPick {Style.i('Yes')} to "
                                    f"select how much {{}} you want to get.\n\nPick {Style.i('No')} to select how "
                                    f"much {{}} you want to sell.",
                         reply_parameters=["receive_currency", "receive_currency", "from_currency"],

                         response_set_key="fixed",
                         )

        if not self.message_valid():
            self.success = False
        self.set_response()
        self.set_next_state()

        self.reply_compile()

        keyboard = [
            [{"text": "Yes"}, {"text": "No"}],
            self.reply_keyboard_control_row()
        ]
        self.reply.object.set_reply_keyboard(keyboard)


STATES[REQUEST_EXCHANGE_TYPE] = ExchangeType


class Amount(State):
    def __init__(self, message: str, context: CallbackContext):
        super().__init__(message,
                         context,

                         response_validation=Decimal.REGEX,
                         response_set_key="amount",
                         )

        if not self.message_valid():
            self.success = False
        self.set_response()

        if self.get("fixed") == "Yes":
            self.set("fixed", True)
            self.reply.text = "How much {} do you want to buy?"
            self.reply.parameters = ["receive_currency"]
        else:
            self.set("fixed", False)
            self.reply.text = "How much {} do you want to sell?"
            self.reply.parameters = ["from_currency"]

        self.set_next_state()

        self.reply_compile()

        self.reply.object.remove_reply_keyboard()


STATES[REQUEST_AMOUNT] = Amount


class PreviewEstimate(State):
    def __init__(self, message: str, context: CallbackContext):
        super().__init__(message,
                         context,

                         response_set_key="continue",
                         )

        if not self.message_valid():
            self.success = False
        self.set("amount", Decimal(message))
        self.set_next_state()

        amount = self.get("amount")
        from_currency = self.get("from_currency")
        receive_currency = self.get("receive_currency")

        self.reply.object = self.commands.calculate_order(["", amount, from_currency, receive_currency], context)

        keyboard = [
            [{"text": "Continue"}],
            self.reply_keyboard_control_row()
        ]
        self.reply.object.set_reply_keyboard(keyboard)


STATES[PREVIEW_ESTIMATE] = PreviewEstimate


class ReceiveAddress(State):
    def __init__(self, message: str, context: CallbackContext):
        super().__init__(message,
                         context,

                         reply_text="What {} address do you want to receive {} to?\n\nPaste the address or send a photo of the QR code 📸.",
                         reply_parameters=["receive_currency", "receive_currency"],

                         response_set_key="receive_address",
                         )

        if not self.message_valid():
            self.success = False

        if self.get("path") == PATH_TRADE:
            self.set("amount", Decimal(message))

        self.set_next_state()
        self.reply_compile()

        estimate_reply = ""
        if not self.get("fixed") and self.get("path") == PATH_TRADE:
            amount = self.get("amount")
            from_currency = self.get("from_currency")
            receive_currency = self.get("receive_currency")
            estimate_reply = self.commands.calculate_order(["", amount, from_currency, receive_currency], context)

        self.reply.object.append(estimate_reply)
        self.reply.object.remove_reply_keyboard()


STATES[REQUEST_RECEIVE_ADDRESS] = ReceiveAddress


class PhotoDecodeRetry(Exception):
    pass


class CreateOrder(State):
    def __init__(self, message: str, context: CallbackContext):
        super().__init__(
            message,
            context,
        )
        if self.get("photo"):
            try:
                qr = decode(self.get("photo"))
                decoded = qr[0].data.decode('ascii')
                self.message = urlparse(decoded).path
            except:
                raise PhotoDecodeRetry()

        self.set_response()
        self.set_next_state()

        from_currency = self.get("from_currency")
        receive_currency = self.get("receive_currency")
        amount = self.get("amount")
        fixed = self.get("fixed")
        receive_address = self.get("receive_address")

        if fixed:
            reply = self.commands.create_fixed(["", from_currency, amount, receive_currency, receive_address], context)
        else:
            reply = self.commands.create_order(["", amount, from_currency, receive_currency, receive_address], context)

        self.reply.object = reply


STATES[CREATE_ORDER] = CreateOrder


class Conversation:
    def __init__(self, states_dict: Dict[int, State], entry_state: int, exit_state: int):

        self.states = states_dict
        self.entry_regex = None
        self.entry_state = entry_state
        self.exit_state = exit_state

        self.past_states = []

    def clear(self, context: CallbackContext):
        """
        Clears the context variable and past_states, preserves chat_id
        :param context: context variable
        :return: None
        """
        chat_id = context.user_data["chat_id"]
        context.user_data.clear()
        context.user_data["chat_id"] = chat_id
        self.past_states = []

    def fallback(self, params: List[str], context: CallbackContext) -> Reply:
        """
        Method to create a Reply() in case anything goes wrong at any point in the conversation
        :param params: not used, available for future use
        :param context: context variable
        :return: fallback Reply() ready to send
        """
        self.clear(context)
        reply = Reply("Cancelled")
        reply.add_navigation_keyboard()
        return reply

    def add_entry_regex(self, entry_regex: str):
        """
        Entry regex is set depending on the conversation and path so it's done outside of the class via this setter
        :param entry_regex: regex to add to entry regexes for the class instance
        :return: None
        """
        if self.entry_regex:
            self.entry_regex = '|'.join([self.entry_regex, entry_regex])
        else:
            self.entry_regex = entry_regex

    def check_entry_message(self, params: List[str]):
        """
        Check if the params list can be an entry point to the conversation
        :param params: Message to check
        :return: Bool indicating if matches entry regexes and param length
        """
        return re.match(self.entry_regex, params[0], re.IGNORECASE) and len(params) == 1

    def enter(self, params: List[str], context: CallbackContext) -> int | None:
        # entry point into conversation
        context.user_data["state"] = self.entry_state

        for path_number, path_dict in PATHS.items():
            if re.match(path_dict["regex"], params[0], re.IGNORECASE):
                context.user_data["path"] = path_number
                break

        return self.router(params, context)

    def router(self, params: List[str], context: CallbackContext) -> int | None:
        """
        Except the entry into the conversation all messages are routed through here. They are sent to the right state
        and processed
        :param params: List of words in message
        :param context: context variable
        :return: int of next state or None if no next state
        """
        message = " ".join(params)
        chat_id = context.user_data["chat_id"]

        # define exceptions
        class Cancel(Exception):
            pass

        class StateNotFound(Exception):
            pass

        class StateInitFail(Exception):
            pass

        try_again = False

        for i in range(2):
            try:
                self.past_states.append(
                    copy.deepcopy({"state": context.user_data["state"], "data": context.user_data, "params": params}))

                if try_again or re.match(r"^ *↩? */?back", message, re.IGNORECASE):
                    # go back a step in the conversation. either the user pressed to go back or is forced to retry an
                    # input
                    try_again = False

                    self.past_states.pop()
                    self.past_states.pop()
                    past_state = self.past_states[-1]

                    state_class = self.states[past_state["state"]]
                    params = past_state["params"]

                    context.user_data.clear()
                    context.user_data.update(past_state["data"])

                elif re.match(r"^ *❌? */?cancel", message, re.IGNORECASE):
                    # cancel conversation
                    raise Cancel()

                else:
                    state_class = self.states[context.user_data["state"]]

                if not state_class:
                    raise StateNotFound()

                state = state_class(params[0], context)

                if not state.success:
                    # if something went wrong in the init then raise here
                    raise StateInitFail()

                state.reply.object.send(chat_id)

                if context.user_data["state"] == self.exit_state:
                    # if that was the last state quit the conversation
                    self.clear(context)
                    Reply().send_navigation_keyboard_with_message(chat_id=chat_id)
                    return None
                else:
                    context.user_data["state"] = state.next_state
                    return state.next_state

            except Cancel:
                self.fallback(params, context).send(chat_id)
                return None

            except PhotoDecodeRetry:

                Reply("Failed to decode photo!").send(chat_id)
                try_again = True
                # no return because he enters the loop again to resend the request for a photo

            except (StateNotFound, StateInitFail, Exception) as e:
                logger = logging.getLogger(__name__)
                logger.error(e)
                self.fallback(params, context).send(chat_id)
                return None


trade_conversation = Conversation(
    states_dict=STATES,
    entry_state=REQUEST_FROM_CURRENCY,
    exit_state=CREATE_ORDER,
)
