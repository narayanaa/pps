import csv
import json
import re
from io import StringIO
from typing import List

from ..data_element import DataElement
from .unique_id import generate_unique_id


def infer_data_type(value: str) -> str:
    try:
        float(value)
        return "numeric"
    except ValueError:
        if re.match(r'\d{4}-\d{2}-\d{2}', value):
            return "date"
        return "text"


class Table(DataElement):
    def __init__(self, data: List[List[str]], caption: str = "", headers: List[str] = None,
                 subheaders: List[List[str]] = None, source: str = None, table_format: str = "simple"):
        super().__init__()
        self.id = generate_unique_id()
        self.data = data
        self.caption = caption
        self.headers = headers if headers else []
        self.subheaders = subheaders if subheaders else []
        self.source = source  # Optional link to external data source (e.g., database, CSV)
        self.table_format = table_format  # Simple, merged cells, pivot, etc.

    def extract_metadata(self, aspects: list = None):
        # Extracting metadata including number of rows, columns, headers, and table format
        metadata = {
            "header": {
                "keys": {header: "string" for header in self.headers},  # Assuming all headers as strings for now
                "subheaders": self.subheaders if self.subheaders else []
            },
            "data": {
                "rows": len(self.data),
                "columns": len(self.headers),
                "sample_row": self.data[0] if self.data else []
            },
            "table_format": self.table_format,
            "source": self.source
        }

        # Inferring data types for each column (basic: numeric, text, date)
        if self.data:
            sample_row = self.data[0]
            metadata["column_data_types"] = [infer_data_type(value) for value in sample_row]

        return metadata

    def to_dict(self) -> dict:
        """Convert Table to dictionary with enhanced structure for interoperability"""
        # Calculate dimensions
        num_rows = len(self.data)
        num_cols = len(self.headers) if self.headers else (len(self.data[0]) if self.data else 0)
        
        # Create column-oriented data structure for better dataframe compatibility
        columns_data = {}
        if self.headers:
            for i, header in enumerate(self.headers):
                columns_data[header] = [row[i] if i < len(row) else None for row in self.data]
        else:
            # Create generic column names if no headers
            for i in range(num_cols):
                col_name = f"column_{i+1}"
                columns_data[col_name] = [row[i] if i < len(row) else None for row in self.data]
        
        # Infer data types for each column
        column_types = {}
        for col_name, col_data in columns_data.items():
            if col_data:
                # Sample non-None values to infer type
                sample_values = [v for v in col_data[:5] if v is not None]
                if sample_values:
                    column_types[col_name] = infer_data_type(str(sample_values[0]))
                else:
                    column_types[col_name] = "text"
            else:
                column_types[col_name] = "text"
        
        return {
            "id": self.id,
            "type": "table",
            "caption": self.caption,
            "source": self.source,
            "table_format": self.table_format,
            # Core table structure
            "dimensions": {
                "rows": num_rows,
                "columns": num_cols
            },
            # Headers and structure
            "headers": self.headers,
            "subheaders": self.subheaders,
            # Data in multiple formats for different use cases
            "data": {
                # Row-oriented (original format)
                "rows": self.data,
                # Column-oriented (dataframe-friendly)
                "columns": columns_data,
                # Flat list for simple processing
                "flat": [cell for row in self.data for cell in row]
            },
            # Schema information for interoperability
            "schema": {
                "column_names": list(columns_data.keys()),
                "column_types": column_types,
                "has_headers": bool(self.headers),
                "has_subheaders": bool(self.subheaders)
            },
            # DataElement inherited properties
            "caption": self.caption,
            "references": self.references,
            "cache": self.cache,
            "footnotes": self.footnotes
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create Table instance from dictionary with backward compatibility"""
        # Handle both old and new formats
        if "data" in data and isinstance(data["data"], dict):
            # New format with enhanced structure
            table_data = data["data"].get("rows", [])
        else:
            # Old format or direct data array
            table_data = data.get("data", [])
        
        table = cls(
            data=table_data,
            caption=data.get("caption", ""),
            headers=data.get("headers", []),
            subheaders=data.get("subheaders", []),
            source=data.get("source"),
            table_format=data.get("table_format", "simple")
        )
        
        # Restore DataElement properties
        table.id = data.get("id", table.id)
        table.references = data.get("references", [])
        table.cache = data.get("cache", {})
        table.footnotes = data.get("footnotes")
        
        return table

    def to_dataframe_dict(self) -> dict:
        """Convert to pandas DataFrame-compatible dictionary format"""
        columns_data = {}
        if self.headers:
            for i, header in enumerate(self.headers):
                columns_data[header] = [row[i] if i < len(row) else None for row in self.data]
        else:
            # Create generic column names
            for i in range(len(self.data[0]) if self.data else 0):
                col_name = f"column_{i+1}"
                columns_data[col_name] = [row[i] if i < len(row) else None for row in self.data]
        return columns_data

    def to_records(self) -> List[dict]:
        """Convert to list of dictionaries (record format)"""
        if not self.data:
            return []
        
        headers = self.headers if self.headers else [f"column_{i+1}" for i in range(len(self.data[0]))]
        records = []
        
        for row in self.data:
            record = {}
            for i, header in enumerate(headers):
                record[header] = row[i] if i < len(row) else None
            records.append(record)
        
        return records

    def get_column(self, column_name: str) -> List:
        """Get a specific column by name"""
        if not self.headers or column_name not in self.headers:
            return []
        
        col_index = self.headers.index(column_name)
        return [row[col_index] if col_index < len(row) else None for row in self.data]

    def get_row(self, row_index: int) -> List:
        """Get a specific row by index"""
        if 0 <= row_index < len(self.data):
            return self.data[row_index].copy()
        return []

    def get_cell(self, row_index: int, column_name: str):
        """Get a specific cell value"""
        if not self.headers or column_name not in self.headers:
            return None
        
        col_index = self.headers.index(column_name)
        if 0 <= row_index < len(self.data) and col_index < len(self.data[row_index]):
            return self.data[row_index][col_index]
        return None

    def to_csv(self) -> str:
        """Export table as CSV format"""
        output = StringIO()
        writer = csv.writer(output)

        # Write headers and subheaders if available
        if self.headers:
            writer.writerow(self.headers)
        if self.subheaders:
            for subheader_row in self.subheaders:
                writer.writerow(subheader_row)

        # Write data rows
        writer.writerows(self.data)

        return output.getvalue()

    def to_json(self) -> str:
        """Export table as JSON format (enhanced structure)"""
        return json.dumps(self.to_dict(), indent=2)

    def to_html(self) -> str:
        """Export table as HTML format"""
        html = ['<table>']
        
        # Add caption if available
        if self.caption:
            html.append(f'<caption>{self.caption}</caption>')
        
        # Add headers
        if self.headers:
            html.append('<thead><tr>')
            for header in self.headers:
                html.append(f'<th>{header}</th>')
            html.append('</tr></thead>')
        
        # Add data rows
        html.append('<tbody>')
        for row in self.data:
            html.append('<tr>')
            for cell in row:
                html.append(f'<td>{cell}</td>')
            html.append('</tr>')
        html.append('</tbody>')
        
        html.append('</table>')
        return ''.join(html)

    def to_excel_data(self) -> dict:
        """Export table data in Excel-compatible format"""
        excel_data = {
            'worksheet_name': self.caption or 'Table',
            'headers': self.headers,
            'data': self.data,
            'metadata': {
                'source': self.source,
                'format': self.table_format,
                'created_by': 'Web Scraper',
                'dimensions': f"{len(self.data)}x{len(self.headers) if self.headers else 0}"
            }
        }
        return excel_data

    def to_text(self):
        """Converts table data to plain text, including headers and ALL rows."""
        table_text = f"Table: {self.caption}\n"
        if self.headers:
            table_text += " | ".join(self.headers) + "\n"

        for row in self.data:
            table_text += " | ".join(row) + "\n"

        return table_text.strip()

    def get_entities(self):
        """Extracts entities from table headers and data."""
        entities = []
        for row in self.data:
            entities.extend([(cell, "TABLE_DATA") for cell in row])
        return entities

    def __repr__(self):
        return f"Table(caption='{self.caption}', rows={len(self.data)}, columns={len(self.headers)})"
