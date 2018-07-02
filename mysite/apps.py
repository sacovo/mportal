from suit.apps import DjangoSuitConfig
from suit.menu import ParentItem, ChildItem


class SuitConfig(DjangoSuitConfig):
    list_per_page = 100
