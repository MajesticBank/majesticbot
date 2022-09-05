"""
File defines a class which allows access to the orders.db file
The class also forks into a subprocess which auto updates the orders.db and send status change alerts to users
This design isn't very good, but it works well enough for the current use-case.
"""

import logging
import os
import sqlite3 as sl
import sqlalchemy as sa
import time

from telegram import Bot

import MajesticBank
from MajesticBank import MajesticBankAPI, Style
from MajesticBank.SignalCatcher import MajesticBankSignalCatcher

DB_NAME_ALCHEMY = "sqlite:///orders.db"
DB_NAME = "orders.db"


class MajesticBankOrders:
    def __init__(self, start_updater: bool = True):
        """
        :param start_updater: Whether to fork the process and start an updater of the statuses. Only ever have one
         instance initiated with this being true!
        """

        self.engine = sa.create_engine(
            DB_NAME_ALCHEMY, connect_args={"check_same_thread": False}
        )
        self.con = self.engine.connect()

        meta = sa.MetaData(bind=self.con)

        if start_updater:
            self.statuses = sa.Table(
                "statuses",
                meta,
                sa.Column(
                    "id",
                    sa.Integer,
                    primary_key=True,
                    autoincrement=True,
                    nullable=False,
                ),
                sa.Column("chat_id", sa.BIGINT, nullable=False),
                sa.Column("trx", sa.VARCHAR(64), nullable=False),
                sa.Column(
                    "time_created",
                    sa.DateTime,
                    nullable=False,
                    server_default=sa.func.now(),
                ),
                sa.Column(
                    "time_modified",
                    sa.DateTime,
                    nullable=False,
                    server_default=sa.func.now(),
                ),
                sa.Column("status", sa.Text, nullable=True),
            )
            meta.create_all(self.engine)
        else:
            sa.MetaData.reflect(meta)
            self.statuses = meta.tables["statuses"]

        self.API = MajesticBankAPI()
        if start_updater and os.fork() == 0:
            self.updater()

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

        insert = sa.insert(self.statuses).values(
            chat_id=new_row["chat_id"], trx=new_row["trx"], status=new_row["status"]
        )
        self.con.execute(insert)

    def select(self, chat_id):
        q = self.statuses.select().where(self.statuses.c.chat_id == chat_id)

        return self.con.execute(q).fetchall()

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
                    q = self.statuses.select().where(
                        sa.and_(
                            self.statuses.c.status != "Completed",
                            self.statuses.c.time_modified
                            >= sa.func.datetime("now", "-1 hours"),
                        )
                    )
                    rows = self.con.execute(q).fetchall()

                    statuses_updated_count = 0

                    for row in rows:

                        if signal_catcher.self_terminate():
                            break

                        data = self.API.track(row["trx"])

                        # logger.info(f"Data received: {data}")

                        if row["status"] != data["status"]:

                            q = (
                                self.statuses.update()
                                .where(self.statuses.c.chat_id == row["chat_id"])
                                .values(
                                    status=data["status"],
                                    time_modified=sa.func.datetime("now"),
                                )
                            )

                            self.con.execute(q)

                            statuses_updated_count += 1

                            if data["status"] != "Not found":
                                reply = Style.b("🚨 STATUS CHANGE 🚨") + "\n\n"
                                reply += (
                                    "Order "
                                    + Style.code("#" + row["trx"])
                                    + " status changed.\n\n"
                                )
                                reply += Style.b(data["status"]) + "\n\n"
                                reply += "For more details type:\n"
                                reply += "/track " + Style.code("#" + row["trx"])
                                bot = Bot(MajesticBank.API_KEY)
                                bot.send_message(
                                    row["chat_id"], reply, parse_mode="HTML"
                                )

                    q = self.statuses.delete().where(
                        self.statuses.c.status == "Not found"
                    )
                    self.con.execute(q)

                    q = self.statuses.delete().where(
                        self.statuses.c.time_created
                        <= sa.func.datetime("now", "-2 weeks")
                    )
                    self.con.execute(q)

                    if statuses_updated_count > 0:
                        logger.info(f"Updated {statuses_updated_count} status(es)")

                except Exception as e:
                    logger.error(e)

            # sleep for 1 second
            time.sleep(1)
            seconds = (seconds + 1) % 30

        # after breaking for the loop quit the process
        quit()
