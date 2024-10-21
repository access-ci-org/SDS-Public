import markdown2

def convert_markdown_to_html(markdown_text):

    html = markdown2.markdown(markdown_text, extras=['fenced-code-blocks', 'code-friendly'])

    html = f'<div class="markdown-content">{html}</div>'
    styles = ("""
            <style>
                .markdown-content body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
                .markdown-content pre { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; padding: 10px; margin: 10px 0; overflow-x: auto; }
                .markdown-content code { font-family: 'Consolas', 'Monaco', 'Lucida Console', monospace; font-size: 0.9em; }
                .markdown-content p code { background-color: #f0f0f0; padding: 2px 4px; border-radius: 4px; }
                .markdown-content h1 { font-size: 1.5em; }
                .markdown-content h2 { font-size: 1.3em; }
                .markdown-content h3 { font-size: 1.1em; }
            </style>
                """)
    
    full_html = html + styles

    return full_html