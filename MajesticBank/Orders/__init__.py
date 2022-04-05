"""
File defines a class which allows access to the orders.db file
The class also forks into a subprocess which auto updates the orders.db and send status change alerts to users
This design isn't very good, but it works well enough for the current use-case.
"""

import logging
import os
import sqlite3 as sl
import time

from telegram import Bot

import MajesticBank
from MajesticBank import MajesticBankAPI, Style
from MajesticBank.SignalCatcher import MajesticBankSignalCatcher

DB_NAME = "orders.db"

class MajesticBankOrders:
    def __init__(self, start_updater: bool = True):
        """
        :param start_updater: Whether to fork the process and start an updater of the statuses. Only ever have one
         instance initiated with this being true!
        """

        if start_updater:
            q = """CREATE TABLE IF NOT EXISTS statuses (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
            chat_id BIGINT NOT NULL,
            trx VARCHAR(64) NOT NULL,
            time_created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
            time_modified DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
            status TEXT NULL);"""
            self.__execute(q)

        self.API = MajesticBankAPI()
        if start_updater and os.fork() == 0:
            self.updater()

    def __cursor_fetch_all(self, query, parameters=None):
        con = sl.connect(DB_NAME, check_same_thread=False)
        con.row_factory = sl.Row

        cursor = con.cursor()
        if parameters:
            out = cursor.execute(query, parameters)
        else:
            out = cursor.execute(query)

        out = out.fetchall()
        con.commit()
        con.close()

        return out

    def __execute(self, query, parameters=None):
        con = sl.connect(DB_NAME, check_same_thread=False)
        con.row_factory = sl.Row

        if parameters:
            con.execute(query, parameters)
        else:
            con.execute(query)

        con.commit()
        con.close()

    def insert(self, new_row):
        if "status" not in new_row:
            # new_row["status"] = "Just created"  # todo comment out in PROD
            new_row["status"] = "Waiting for funds"

        q = f"""INSERT INTO statuses (chat_id, trx, status) VALUES (?,?,?);"""
        self.__execute(q, [new_row['chat_id'], new_row['trx'], new_row['status']])

    def select(self, chat_id):
        q = f"""SELECT * FROM statuses WHERE chat_id={chat_id};"""
        return self.__cursor_fetch_all(q)

    def updater(self):

        logger = logging.getLogger(__name__)
        logger.info("Status updater started")

        signal_catcher = MajesticBankSignalCatcher()

        seconds = 0
        while True:

            if signal_catcher.self_terminate():
                break

            if seconds % 30 == 0:
                # enter every 30 seconds
                try:
                    # statuses we know about: Not found, Waiting for funds, Completed

                    # only pick the non completed to update
                    q = """SELECT * FROM statuses WHERE status!='Completed' AND time_modified >= datetime('now', '-1 hours');"""
                    rows = self.__cursor_fetch_all(q)

                    statuses_updated_count = 0

                    for row in rows:

                        if signal_catcher.self_terminate():
                            break

                        data = self.API.track(row["trx"])

                        # logger.info(f"Data received: {data}")

                        if row["status"] != data["status"]:
                            q = """UPDATE statuses SET status=?,time_modified=datetime('now') WHERE chat_id=?"""
                            self.__execute(q, [data["status"], row["chat_id"]])
                            statuses_updated_count += 1

                            if data["status"] != "Not found":
                                reply = Style.b("🚨 STATUS CHANGE 🚨") + "\n\n"
                                reply += "Order " + Style.code("#" + row["trx"]) + " status changed.\n\n"
                                reply += Style.b(data["status"]) + "\n\n"
                                reply += "For more details type:\n"
                                reply += "/track " + Style.code("#" + row["trx"])
                                bot = Bot(MajesticBank.API_KEY)
                                bot.send_message(row["chat_id"], reply, parse_mode='HTML')

                    q = """DELETE FROM statuses WHERE status='Not found';"""
                    self.__execute(q)

                    q = """DELETE FROM statuses WHERE time_created <= datetime('now', '-2 weeks');"""
                    self.__execute(q)

                    if statuses_updated_count > 0:
                        logger.info(f"Updated {statuses_updated_count} status(es)")

                except Exception as e:
                    logger.error(e)

            # sleep for 1 second
            time.sleep(1)
            seconds = (seconds + 1) % 30

        # after breaking for the loop quit the process
        quit()
