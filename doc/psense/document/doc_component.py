# Abstract base class for Document Structure
from abc import ABC, abstractmethod
from typing import List, Union, Dict

from .image import Image
from .paragraph import Paragraph
from .table import Table


class DocumentComponent(ABC):
    @abstractmethod
    def get_content(self) -> List[Union[Paragraph, Image, Table]]:
        pass
