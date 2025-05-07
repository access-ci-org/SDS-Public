from typing import List, Dict
from dataclasses import dataclass, field


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
        ]
    )
    column_names: Dict[str, str] = field(
        default_factory=lambda: {
            "software_name": "Software",
            "rp_name": "Resource",
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
            "ai_general_tags": "AI General Tags",
            "ai_example_use": "AI Example Use",
        }
    )
    column_order: List[str] = field(init=False)

def add_line_breaks_at_commas(text, max_length=50):
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

    return ",<br>".join(lines)