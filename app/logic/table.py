from typing import List, Dict
from dataclasses import dataclass, field
import pandas as pd

@dataclass
class TableInfo:
    default_column_order: List[str] = field(
        default_factory=lambda: [
            "software_name",
            "rp_name",
            "rp_group_id",
            "software_description",
            "ai_description",
            "software_versions",
            "ai_software_type",
            "ai_software_class",
            "ai_research_field",
            "ai_research_area",
            "ai_research_discipline",
            "ai_core_features",
            "ai_general_tags",
            "software_web_page",
            "software_documentation",
            "software_use_link",
            "rp_software_documentation",
            "ai_example_use",
            "more_info"
        ]
    )
    column_names: Dict[str, str] = field(
        default_factory=lambda: {
            "software_name": "Software",
            "Software": "Software",
            "rp_name": "Installed on",
            "Resource": "Installed on",
            "rp_group_id": "RP Group ID",
            "software_description": "Description",
            "software_versions": "Versions",
            "software_web_page": "Software's Web Page",
            "software_documentation": "Software Documentation",
            "software_use_link": "Example Software Use",
            "rp_software_documentation": "RP Software Documentation",
            "ai_description": "AI Description",
            "ai_software_type": "AI Software Type",
            "ai_software_class": "AI Software Class",
            "ai_research_field": "AI Research Field",
            "ai_research_area": "AI Research Area",
            "ai_research_discipline": "AI Research Discipline",
            "ai_core_features": "AI Core Features",
            "ai_general_tags": "AI Tags",
            "ai_example_use": "AI Example Use",
            "more_info": "Documentation, Uses, and more"
        }
    )
    column_order: List[str] = field(init=False)

def combine_columns(df: pd.DataFrame, columns: list[tuple[str, str]], combine_data: bool = False, separator: str = ", "):
    """
    Merges two columns. Data is added ot the first column in the tuple

    Args:
        df: Input DataFrame
        columns: List of tuples containing (primary_column, secondary_column) names
        combine_data: If False, just fills missing values. If True, combines both columns and removes duplicates.
        separator: String to use when combining values (default: ", ")

    Returns:
        pd.DataFrame: Modified DataFrame
    """
    df_result = df.copy()

    for col1, col2 in columns:
        if col1 not in df_result.columns or col2 not in df_result.columns:
            continue
        # Convert NaN/None to empty strings for string operations
        df_result[col1] = df_result[col1].fillna("").astype(str)
        df_result[col2] = df_result[col2].fillna("").astype(str)

        if combine_data:
            # Combine both columns and remove duplicates
            def merge_row(row):
                val1, val2 = row[col1].strip(), row[col2].strip()

                # If both are empty, return empty string
                if not val1 and not val2:
                    return ""
                elif not val1:
                    return val2
                elif not val2:
                    return val1

                # Both exist - combine and deduplicate
                items1 = [item.strip() for item in val1.split(separator) if item.strip()]
                items2 = [item.strip() for item in val2.split(separator) if item.strip()]

                # Remove duplicates while preserving order
                combined = []
                for item in items1 + items2:
                    if item and item not in combined:
                        combined.append(item)

                return separator.join(combined)

            df_result[col1] = df_result.apply(merge_row, axis=1)
        else:
            # Simple fillna approach - fill empty strings in col1 with values from col2
            df_result[col1] = df_result[col1].replace("", pd.NA).fillna(df_result[col2]).fillna("")

    return df_result

def get_display_table() -> pd.DataFrame:
    """
    Returns a pandas DataFrame of the data to show to users. Some columns are combined together.
    """
    software_csv = "app/data/final.csv"
    table_info = TableInfo()
    df = pd.read_csv(software_csv, keep_default_na=False)
    df.rename(columns=table_info.column_names, inplace=True)
    df = combine_columns(df, [
        ('AI Description', 'Description'),
    ])
    df = combine_columns(df, [
        ('AI Research Discipline', 'AI Research Field')
    ], combine_data=True)

    return df

def add_char_at_commas(text,char=",<br>", max_length=50):
    """
    Add line breaks to comma-separated text, keeping each line under max_length
    characters where possible, breaking at commas.
    """
    if not isinstance(text, str) or len(text) <= max_length:
        return text

    parts = text.split(',')
    lines = []
    current_line = ""

    for i, part in enumerate(parts):
        # Clean up the part
        clean_part = part.strip()

        # Add comma back except for first item in a new line
        prefix = "," if current_line else ""

        # If adding this part would exceed max_length, start a new line
        if len(current_line) + len(prefix + clean_part) > max_length and current_line:
            lines.append(current_line)
            current_line = clean_part
        else:
            current_line += prefix + clean_part

    # Add the last line if there's anything left
    if current_line:
        lines.append(current_line)

    return f"{char}".join(lines)