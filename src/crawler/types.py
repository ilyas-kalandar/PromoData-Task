from typing import Self, List

from dataclasses import dataclass


@dataclass
class Category:
    name: str
    url: str
    parent: Self | None


@dataclass
class Shop:
    address: str
    availability: str


@dataclass
class Offer:
    code: str
    price: float
    discount_price: float
    size: str
    shops: List[Shop]


@dataclass
class Product:
    id: int
    name: str
    offers: List[Offer]
