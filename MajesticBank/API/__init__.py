"""
This file defines a class which serves a wrapper to the original MajesticBank API
"""
import logging

import requests

from MajesticBank.Decimal import Decimal


class MajesticBankAPI:
    def __init__(self):
        # host is host name for easy switching between TLDs in the future
        self.host = "https://majesticbank.sc"
        # api_endpoint is the path on the host that all api requests begin with
        self.api_endpoint = "/api/v1/"

    def __api_full_path(self, method_path: str) -> str:
        """
        :param method_path: path to reach the method on the api endpoint
        :return: the combined full path for the method provided
        """
        return f"{self.host}{self.api_endpoint}{method_path}"

    def __call(self, url: str, payload: dict = None) -> dict:
        """
        Helper to make the call to the API server and return the response after parsing the JSON and broadcasting the types
        :param url: the full path to make the request to
        :param payload: a dict containing the data to be sent to the server
        :return: a dict from with response
        """
        response = requests.get(url, params=payload)
        if response.ok:
            return self.__broadcast(response.json())
        else:
            logger = logging.getLogger(__name__)
            logger.error(f"API response: {response.text}")
            raise TypeError("API response is not valid JSON")

    def __broadcast(self, response: dict) -> dict:

        # fields to be broadcast into Decimal()
        decimal_fields = ["from_amount", "receive_amount", "min", "max"]
        # fields to be broadcast into int
        int_fields = ["received", "confirmed"]

        for field in decimal_fields:
            if field in response:
                response[field] = Decimal(response[field])

        for field in int_fields:
            if field in response:
                response[field] = int(response[field])

        return response

    def get_rates(self) -> dict:
        """
        Native API method
        :return: API response converted to a dict
        """
        endpoint = self.__api_full_path("rates")
        response = self.__call(endpoint)
        return response

    def get_limits(self, from_currency: str) -> dict:
        """
        Native API method
        :return: API response converted to a dict
        """
        endpoint = self.__api_full_path("limits")

        payload = {
            "from_currency": from_currency
        }

        response = self.__call(endpoint, payload)
        return response

    def calculate_order(self, from_currency: str, receive_currency: str, from_amount: Decimal = None,
                        receive_amount: Decimal = None):
        """
        Native API method
        :return: API response converted to a dict
        """
        endpoint = self.__api_full_path("calculate")

        payload = {
            "from_currency": from_currency,
            "receive_currency": receive_currency,
        }
        if from_amount:
            payload["from_amount"] = from_amount
        elif receive_amount:
            payload["receive_amount"] = receive_amount

        response = self.__call(endpoint, payload)
        return response

    def create_order(self, from_amount: Decimal, from_currency: str, receive_currency: str,
                     receive_address: str, referral_code: str) -> dict:
        """
        Native API method
        :return: API response converted to a dict
        """
        endpoint = self.__api_full_path("exchange")

        payload = {
            "from_amount": from_amount,
            "from_currency": from_currency,
            "receive_currency": receive_currency,
            "receive_address": receive_address,
            "referral_code": referral_code
        }

        response = self.__call(endpoint, payload)
        return response

    def create_fixed(self, from_currency: str, receive_currency: str, receive_address: str, referral_code: str,
                     from_amount: Decimal = None, receive_amount: Decimal = None) -> dict:
        """
        Native API method
        :return: API response converted to a dict
        """
        endpoint = self.__api_full_path("pay")

        payload = {
            "from_currency": from_currency,
            "receive_currency": receive_currency,
            "receive_address": receive_address,
            "referral_code": referral_code
        }

        if from_amount:
            payload["from_amount"] = from_amount
        elif receive_amount:
            payload["receive_amount"] = receive_amount

        response = self.__call(endpoint, payload)
        return response

    def track(self, trx: str) -> dict:
        """
        Native API method
        :return: API response converted to a dict
        """
        endpoint = self.__api_full_path("track")

        payload = {
            "trx": trx,
        }

        response = self.__call(endpoint, payload)
        return response
