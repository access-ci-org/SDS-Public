"""
Registry of admin-editable data fields.

Every consumer (edit panel, export, import, projection, app config, test
seeding) derives its field lists from these constants. Membership means the
field is override-able: it has a column on SoftwareEdit for the stored
override and a column on a live table (Software / AISoftwareInfo) that
displays it.
"""

SOFTWARE_FIELD_MAP = {
    # edit-field name -> Software column
    "description": "software_description",
    "web_page": "software_web_page",
    "documentation": "software_documentation",
    "use_link": "software_use_link",
}

# For AI fields the edit-field name and the AISoftwareInfo column match.
AI_FIELD_NAMES = (
    "ai_description",
    "ai_software_type",
    "ai_software_class",
    "ai_research_field",
    "ai_research_area",
    "ai_research_discipline",
    "ai_core_features",
    "ai_general_tags",
    "ai_example_use",
)

ALL_FIELDS = tuple(SOFTWARE_FIELD_MAP) + AI_FIELD_NAMES
