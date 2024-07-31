import logging
import csv
import pathlib
import time
import pickle
import itertools
from typing import List

from redis import Redis
from typer import Typer
import threading

from crawler.configurator import settings
from crawler.exceptions import PageNotFound
from crawler.parser import Parser
from crawler.types import Product, Category

app = Typer(name="Crawler", help="A parser for https://bethowen.ru")
logger = logging.getLogger("main")


def prepare_csv():
    """Prepares .csv file"""
    with open(settings.output_file, "w") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "Название продукта",
                "Код",
                "Размер",
                "Цена",
                "Цена со скидкой",
                "ТТ",
                "Доступность",
            ]
        )


def put_products_to_csv(products: List[Product]):
    """Puts data to .csv file"""

    # if file does not exits, create it and put some headers
    if not pathlib.Path(settings.output_file).exists():
        prepare_csv()

    with open(settings.output_file, "a") as file:
        writer = csv.writer(file)

        for product in products:
            for offer in product.offers:
                for shop in offer.shops:
                    writer.writerow(
                        [
                            product.name,
                            offer.code,
                            offer.size,
                            offer.price,
                            offer.discount_price,
                            shop.address,
                            shop.availability,
                        ]
                    )


def parse_page(category: Category, page: str, parser: Parser):
    """Parses concrete page"""
    redis = get_redis()

    # If page is parsed, we don't parse it again, BTW
    if bool(redis.get(category.url + f"_{page}")):
        logging.info(f"Skipped {category.url} (already exists)")
        return

    products = parser.parse_products(
        category,
        page,
    )

    put_products_to_csv(
        products,
    )

    # Mark page as parsed.
    redis.set(category.url + f"_{page}", 1)


def get_redis() -> Redis:
    """Builds & returns `Redis`"""
    return Redis(
        host=settings.redis.host,
        port=settings.redis.port,
    )


def parse_products(category: Category, parser: Parser):
    """Parses products with some category"""
    page = 1

    while True:
        try:
            parse_page(category, str(page), parser)
        except PageNotFound:
            # For stopping pagination, LOL)
            break

        page += 1


@app.command("clean")
def clean():
    """For cleanup cache & output file."""

    # Cleanup .csv
    prepare_csv()

    # Cleanup redis
    redis = get_redis()
    redis.flushdb()

    with open("dump.dat", "wb") as file:
        pickle.dump([], file)


@app.command("run")
def run_parser():
    """Runs project"""

    logging.basicConfig(level=logging.INFO)

    parser = Parser(
        settings.base_url,
        settings.proxies,
        settings.requests_to_delay,
        settings.delay,
    )

    # Try load categories from cache (Better use redis)
    try:
        with open("dump.dat", "br") as f:
            categories = pickle.load(f)
    except FileNotFoundError:
        categories = []

    if not categories:
        categories = parser.parse_categories()

        # Cache categories, yes, very dump
        with open("dump.dat", "bw") as f:
            pickle.dump(categories, file=f)

    for batch in itertools.batched(categories, settings.threads):
        for category in batch:
            t = threading.Thread(
                target=parse_products,
                args=(category, parser),
            )
            t.start()

        time.sleep(100)
