import logging
import time
import typing
import string
import random

import requests
from bs4 import BeautifulSoup

from crawler.exceptions import PageNotFound, IPAddressBlocked
from crawler.types import Category, Product, Offer, Shop


def gen_random_ua():
    """Generates super random user-agent"""
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    size = random.randint(1, 10)
    return "".join(random.choice(chars) for x in range(size))


class Parser:
    """
    Parser for https://bethowen.ru/
    """

    def __init__(
        self, base_url: str, proxies: list, requests_to_delay: int, delay: int
    ):
        """
        Initializes `self`
        :param base_url: A base url
        :param proxies: A list of proxies
        :param requests_to_delay: A count of requests to delay
        :param delay: A delay
        """
        self._proxies = proxies
        self._sleep_time = 5
        self._logger = logging.getLogger("parser")
        self._base_url = base_url
        self._requests_count = 0
        self._delay = delay
        self._requests_to_delay = requests_to_delay
        self._current_proxy_idx = 0

    def _get_cur_proxy(self) -> str:
        return self._proxies[self._current_proxy_idx]

    def _make_request(
        self,
        method: typing.Literal["GET", "POST"],
        endpoint: str,
        params: typing.Dict[str, str] | None = None,
    ) -> requests.Response:
        """
        Makes request to the server
        :param method: A method
        :param endpoint: An endpoint
        :param params: A query-parameters
        :return:
        """
        self._requests_count += 1

        # Delay for every `N` requests
        if self._requests_count % self._requests_to_delay == 0:
            delay = random.randint(30, 60)
            self._logger.info("Waiting %d seconds, for avoiding blocking.", delay)
            time.sleep(delay)

        if params is None:
            params = {}

        self._requests_count += 1

        # Fake user-agent, works for bethowen.ru
        headers = {"User-Agent": gen_random_ua()}

        retries = 0

        while True:
            retries += 1

            if retries == 10:
                raise IPAddressBlocked("Too many retries, can't parse.")

            try:
                response = requests.request(
                    method,
                    url=f"{self._base_url}/{endpoint}",
                    headers=headers,
                    params=params,
                    timeout=10,
                    proxies={
                        "https": self._get_cur_proxy(),
                    } if self._get_cur_proxy() else None
                )
            except (requests.exceptions.Timeout, requests.exceptions.ProxyError):
                self._current_proxy_idx += 1

                if len(self._proxies) == self._current_proxy_idx:
                    raise IPAddressBlocked("Blocked.")

                self._logger.info(
                    "Timeout, changing proxy to %s",
                    self._get_cur_proxy(),
                )
                continue

            if response.status_code == 404:
                raise PageNotFound(f"Not found, url: {response.request.url}")

            # IWAF in `response` stands for captcha, we can use another `User-Agent` to avoiding this
            if "IWAF" in response.text:
                retries = 0
                continue

            return response

    def _make_rest_request(
        self, method, endpoint, params: typing.Dict[str, str] = None
    ) -> dict:
        """
        Makes request and returns json-response
        :param method: A method
        :param endpoint: Endpoint
        :param params: A dictionary with query-parameters
        """
        resp = self._make_request(
            method,
            endpoint,
            params,
        )

        return resp.json()

    def get_offer(self, off_id: int) -> Offer:
        """
        Returns `Offer` from REST
        :param off_id: Offer's identifier
        :return:
        """
        raw = self._make_rest_request(
            "GET", f"api/local/v1/catalog/offers/{off_id}/details"
        )

        shops = []

        for shop in raw["availability_info"]["offer_store_amount"]:
            shops.append(
                Shop(
                    address=shop.get("address"),
                    availability=shop.get("availability").get("text"),
                )
            )

        return Offer(
            code=raw.get("code"),
            size=raw.get("size"),
            shops=shops,
            price=raw.get("retail_price"),
            discount_price=raw.get("discount_price"),
        )

    def get_product(self, product_id: str) -> Product:
        """Loads `Product` and its `Offer`'s"""

        self._logger.info("Getting product %s", product_id)

        raw = self._make_rest_request(
            "GET",
            f"api/local/v1/catalog/products/{product_id}/details",
        )

        offers = []

        for offer in raw.get("offers"):
            offers.append(self.get_offer(offer.get("id")))

        return Product(
            name=raw.get("name"),
            id=raw.get("id"),
            offers=offers,
        )

    def _get_soup(
        self,
        method: typing.Literal["GET", "POST"],
        endpoint: str,
        params: typing.Dict[str, str] | None = None,
    ):
        """Makes request & returns `BeautifulSoup` object."""
        resp = self._make_request(
            method,
            endpoint,
            params,
        )

        return BeautifulSoup(resp.content, features="html.parser")

    def parse_categories(self) -> typing.List[Category]:
        """Parses all categories from https://bethowen.ru/"""

        categories = []
        soup = self._get_soup("GET", "/catalogue")

        # Firstly, get all section-information divs
        first_level_categories = soup.select(".section_info")

        for first_level_category in first_level_categories:
            # Construct batya :D
            name = first_level_category.select_one(".name").get_text(strip=True)
            link = first_level_category.select_one("a").attrs.get("href")

            batya = Category(
                name=name,
                parent=None,
                url=link,
            )

            # Collect all second-level categories, related to batya
            for second_level_category in first_level_category.select(".sect"):
                categories.append(
                    Category(
                        parent=batya,
                        name=second_level_category.get_text(strip=True, separator=" "),
                        url=second_level_category.select_one("a").attrs.get("href"),
                    )
                )

        return categories

    def parse_products(
        self,
        category: Category,
        page: str | int,
    ) -> typing.List[Product]:
        """Parses products, collects IDs from html and loads offers from REST API"""
        self._logger.info(
            "Getting products with category %s and page %s", category.name, page
        )

        # Get page with list of products
        soup = self._get_soup(
            "GET",
            category.url,
            params={
                "PAGEN_1": str(page),
            },
        )

        # Select only identifiers
        ids = [s.attrs["data-product-id"] for s in soup.select(".bth-card-element")]

        # Return `Product` objects collected from `REST`
        return [self.get_product(product_id) for product_id in ids]
