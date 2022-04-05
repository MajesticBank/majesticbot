#!/usr/bin/env python

"""This server is written with Python3.10 in mind. Incompatibility with past Python versions is primarily in the type
hinting. """

import logging

from telegram.ext import Updater

import MajesticBank
from MajesticBank.Router import Router

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)


def main() -> None:
    updater = Updater(MajesticBank.API_KEY)
    dispatcher = updater.dispatcher
    # create a custom-router
    router = Router(dispatcher)

    # Start the Bot
    updater.start_polling()

    # stop bot on ctrl-c
    updater.idle()
    # the server is a 2 threaded app but the child self-terminates when parent is not found
    logging.info("Subprocesses will quit themselves in a few seconds.")


if __name__ == '__main__':
    main()
