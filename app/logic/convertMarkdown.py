import markdown2


def convert_markdown_to_html(markdown_text: str) -> str:

    html = markdown2.markdown(
        markdown_text,
        extras=["fenced-code-blocks", "code-friendly", "tables"],
        safe_mode="escape",
    )
    html = f'<div class="markdown-content">{html}</div>'

    return html
