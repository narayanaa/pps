import os
import re
import cv2
import pytesseract
import yaml
import easyocr
from ..data_element import DataElement
import numpy as np
from typing import List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def load_patterns_from_file(file_path: str = None) -> dict:
    """
    Loads OCR metadata patterns from a YAML file.

    Args:
        file_path (str): The path to the YAML file. If None, defaults to 'image_patterns.yaml' in the same directory.

    Returns:
        dict: Dictionary of patterns.
    """
    if file_path is None:
        # Get the directory of the current script (image.py)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, "image_patterns.yaml")

    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading pattern file {file_path}: {e}")
        return {}


class Image(DataElement):
    """
    An enhanced Image class that processes an image file, performs OCR, and extracts text.

    Attributes:
        file_path (str): Path to the image file.
        caption (str): Caption for the image.
        alt_text (str): Alternative text description.
        ocr_data (Any): Extracted text after OCR.
        patterns (dict): Patterns for extracting metadata from OCR text.
    """

    def __init__(self, file_path: str, caption: str = "", alt_text: str = None,
                 pattern_file: str = None):
        """
        Initializes the Image instance and immediately performs OCR.

        Args:
            file_path (str): Path to the image file.
            caption (str): Caption for the image.
            alt_text (str): Alternative text.
            pattern_file (str): YAML file containing regex patterns for metadata.
        """
        super().__init__()
        self.file_path = file_path
        self.caption = caption
        self.alt_text = alt_text
        self.patterns = self.load_patterns_from_file(pattern_file)
        # Preprocess the image and perform OCR
        self.ocr_data = self.perform_img_ocr()

    @staticmethod
    def load_patterns_from_file(file_path: str = None) -> dict:
        """
        Loads OCR metadata patterns from a YAML file.

        Args:
            file_path (str): The path to the YAML file.

        Returns:
            dict: Dictionary of patterns.
        """
        if file_path is None:
            # Get the directory of the current script (image.py)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, "image_patterns.yaml")

        try:
            with open(file_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Error loading pattern file: {e}")
            return {}

    @staticmethod
    def preprocess_image(image: np.ndarray) -> np.ndarray:
        """
        Applies preprocessing steps to enhance OCR accuracy.

        Args:
            image (np.ndarray): The original image.

        Returns:
            np.ndarray: The preprocessed image.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        # Apply thresholding to obtain binary image
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # (Optional) Deskewing can be added here if necessary
        return thresh

    def perform_img_ocr(self) -> Any:
        """
        Performs OCR on the image file after applying preprocessing steps.
        Uses EasyOCR primarily and falls back to Tesseract OCR if needed.

        Returns:
            Any: Extracted text data.
        """
        # logger.info("Starting OCR processing for image: %s", self.file_path)
        try:
            img = cv2.imread(self.file_path)
            if img is None:
                raise ValueError("Image could not be loaded.")
            # Preprocess the image for improved OCR accuracy
            processed_img = self.preprocess_image(img)
            # Define the model storage directory relative to image.py
            script_dir = os.path.dirname(os.path.abspath(__file__))
            model_storage_dir = os.path.join(script_dir, "ocr_dependents")
            # Initialize EasyOCR reader
            reader = easyocr.Reader(['en'], model_storage_directory=model_storage_dir)
            result = reader.readtext(processed_img, width_ths=0.8, decoder='wordbeamsearch')
            # logger.info("EasyOCR completed.")

            # Extract text using a grouping function (defined below)
            extracted_text = self.get_paragraph(result)
            if not extracted_text:
                # Fallback to Tesseract OCR if EasyOCR fails to extract text
                # logger.warning("EasyOCR failed to extract text, falling back to Tesseract.")
                tesseract_text = pytesseract.image_to_string(processed_img)
                extracted_text = [tesseract_text.strip()]
            return extracted_text
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return None

    @staticmethod
    def midpoint(x1: float, y1: float, x2: float, y2: float) -> (int, int):
        """
        Computes the midpoint between two points.

        Args:
            x1, y1, x2, y2 (float): Coordinates of the two points.

        Returns:
            (int, int): The midpoint coordinates.
        """
        return int((x1 + x2) / 2), int((y1 + y2) / 2)

    @staticmethod
    def get_paragraph(raw_result: List[Any], x_ths: float = 1, y_ths: float = 0.5, mode: str = 'ltr') -> List[
        List[str]]:
        """
        Clusters detected text boxes into paragraphs.

        Args:
            raw_result (List[Any]): OCR results containing bounding boxes and text.
            x_ths (float): Horizontal threshold multiplier.
            y_ths (float): Vertical threshold multiplier.
            mode (str): Text direction ('ltr' for left-to-right, 'rtl' for right-to-left).

        Returns:
            List[List[str]]: Grouped text as paragraphs.
        """
        box_group = []
        for box in raw_result:
            # Each box is a tuple: ([list of coordinates], text, confidence)
            coords = box[0]
            all_x = [int(pt[0]) for pt in coords]
            all_y = [int(pt[1]) for pt in coords]
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
            height = max_y - min_y
            # Append additional attributes for grouping
            box_group.append([box[1], min_x, max_x, min_y, max_y, height, 0.5 * (min_y + max_y), 0])

        current_group = 1
        # Group boxes based on spatial proximity
        while len([box for box in box_group if box[7] == 0]) > 0:
            ungrouped = [box for box in box_group if box[7] == 0]
            if not any(box[7] == current_group for box in box_group):
                ungrouped[0][7] = current_group
            else:
                current_group_boxes = [box for box in box_group if box[7] == current_group]
                mean_height = np.mean([box[5] for box in current_group_boxes])
                min_gx = min([box[1] for box in current_group_boxes]) - x_ths * mean_height
                max_gx = max([box[2] for box in current_group_boxes]) + x_ths * mean_height
                min_gy = min([box[3] for box in current_group_boxes]) - y_ths * mean_height
                max_gy = max([box[4] for box in current_group_boxes]) + y_ths * mean_height
                added = False
                for box in ungrouped:
                    same_horizontal = (min_gx <= box[1] <= max_gx) or (min_gx <= box[2] <= max_gx)
                    same_vertical = (min_gy <= box[3] <= max_gy) or (min_gy <= box[4] <= max_gy)
                    if same_horizontal and same_vertical:
                        box[7] = current_group
                        added = True
                        break
                if not added:
                    current_group += 1
        # Arrange grouped boxes into paragraphs
        result = []
        for group in set(box[7] for box in box_group):
            group_boxes = [box for box in box_group if box[7] == group]
            mean_height = np.mean([box[5] for box in group_boxes])
            text = ''
            while group_boxes:
                # Find boxes on the same horizontal line (using y position)
                current_line = min(group_boxes, key=lambda box: box[6])
                candidates = [box for box in group_boxes if box[6] < current_line[6] + 0.4 * mean_height]
                if mode == 'ltr':
                    best_box = min(candidates, key=lambda box: box[1])
                else:
                    best_box = max(candidates, key=lambda box: box[2])
                text += ' ' + best_box[0]
                group_boxes.remove(best_box)
            result.append([text.strip()])
        return result

    def extract_metadata(self, aspects: List[str] = None) -> dict:
        """
        Extracts metadata from the OCR text using predefined patterns.

        Args:
            aspects (List[str], optional): Specific metadata keys to extract.

        Returns:
            dict: Extracted metadata.
        """
        ocr_text = " ".join(self.ocr_data[0]) if self.ocr_data and isinstance(self.ocr_data, list) else ""
        metadata = {"header": {"keys": {}}, "data": {}}

        for key, pattern in self.patterns.items():
            match = re.search(pattern.get("pattern", ""), ocr_text)
            if match:
                metadata["header"]["keys"][key] = pattern.get("data_type", "str")
                metadata["data"][key] = match.group(1)
        metadata["caption"] = self.caption
        metadata["alt_text"] = self.alt_text
        logger.debug(f"Extracted image metadata: {metadata}")
        return metadata

    def to_text(self) -> str:
        """Returns the alt text or caption as plain text for the image."""
        return f"Image: {self.caption or self.alt_text}"

    def get_entities(self):
        """Extracts entities from the OCR data of the image."""
        if not self.ocr_data:
            return []
        
        # Handle different OCR data formats
        if isinstance(self.ocr_data, list):
            # Extract text from list format
            ocr_text = " ".join([" ".join(item) if isinstance(item, list) else str(item) for item in self.ocr_data])
        elif isinstance(self.ocr_data, dict) and "ocr_text" in self.ocr_data:
            ocr_text = self.ocr_data["ocr_text"]
        else:
            ocr_text = str(self.ocr_data)
        
        return [(word, "OCR_TEXT") for word in ocr_text.split() if word.strip()]

    def __repr__(self):
        return f"Image(caption='{self.caption}', file_path='{self.file_path}')"

    def to_dict(self):
        """Convert Image to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": "image",
            "file_path": self.file_path,
            "caption": self.caption,
            "alt_text": self.alt_text,
            "ocr_data": self.ocr_data,
            "patterns": self.patterns,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create Image instance from dictionary"""
        image = cls(
            file_path=data["file_path"],
            caption=data.get("caption", ""),
            alt_text=data.get("alt_text")
        )
        image.id = data["id"]
        image.ocr_data = data.get("ocr_data")
        image.patterns = data.get("patterns", {})
        image.references = data.get("references", [])
        image.cache = data.get("cache", {})
        image.footnotes = data.get("footnotes")
        return image


# Example usage
"""image = Image("/path/to/document.png")
metadata = image.metadata
print(metadata)


image_dict = image.to_dict()
new_image = Image.from_dict(image_dict)
print(new_image.metadata)"""
