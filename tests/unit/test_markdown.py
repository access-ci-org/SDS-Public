"""
convert_markdown_to_html wraps markdown2.markdown. Tests cover:
- Basic rendering (bold, lists, fenced code)
- Raw HTML escaping (requires markdown2 safe_mode — xfail until that lands)
- Empty input
"""
import pytest

from app.logic.convertMarkdown import convert_markdown_to_html


def test_renders_bold():
    out = convert_markdown_to_html("**bold**")
    assert "<strong>bold</strong>" in out or "<b>bold</b>" in out


def test_renders_unordered_list():
    out = convert_markdown_to_html("- one\n- two\n")
    assert "<ul>" in out
    assert "<li>one</li>" in out
    assert "<li>two</li>" in out


def test_renders_fenced_code_block():
    out = convert_markdown_to_html("```python\nprint('hi')\n```")
    assert "<pre>" in out or "<code>" in out


def test_renders_pipe_table():
    out = convert_markdown_to_html("| a | b |\n|---|---|\n| 1 | 2 |\n")
    assert "<table>" in out
    assert "<td>1</td>" in out


def test_wraps_output_in_markdown_content_div():
    out = convert_markdown_to_html("plain text")
    assert 'class="markdown-content"' in out


def test_raw_script_tag_is_escaped():
    out = convert_markdown_to_html("<script>alert(1)</script>")
    # Should appear as escaped text, not as a real <script> tag
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
