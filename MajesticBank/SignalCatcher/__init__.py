"""
File defines a simple and tiny class to capture ctrl+c and other signals that the server should shut down so that they
can be handled gracefully
"""


import logging
import os
import signal


class MajesticBankSignalCatcher:
    kill_signal = False

    def __init__(self):
        signal.signal(signal.SIGABRT, self.received_kill_signal)
        signal.signal(signal.SIGINT, self.received_kill_signal)
        signal.signal(signal.SIGTERM, self.received_kill_signal)

    def received_kill_signal(self, *args):
        self.kill_signal = True

    def self_terminate(self):
        if self.kill_signal or os.getppid() == 1:
            logger = logging.getLogger(__name__)
            logger.info(f"Self-terminating.")
            return True
        return False
