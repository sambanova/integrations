import base64
import logging
import os
import re
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Generator, Match, Optional

import markdown
import weasyprint  # type: ignore
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@contextmanager
def st_capture(output_func: Callable[[Any], Any]) -> Generator[None, None, None]:
    """
    Context manager to catch `stdout` and send it to an output function.

    Args:
        output_func: Function to which the terminal output is written.

    Returns:
        A generator that redirects `stdout` to the `output_func`.
    """
    stdout = StringIO()
    with redirect_stdout(stdout):
        try:
            yield
        finally:
            output_func(stdout.getvalue())


def clean_markdown_content(content: str) -> str:
    """
    Clean Markdown content.

    Convert local Markdown references of the form ![alt text](local_path.png)
    into base64-embedded images so they can display inline.
    Then convert everything to HTML and make minor tidy-ups.
    """

    # Regex to find Markdown image references: ![alt text](image_path)
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'

    def to_base64(match: Match[str]) -> str:
        alt_text = match.group(1)
        img_path = match.group(2)

        # If it's already a URL (http/https/data), leave it as is.
        if any(img_path.lower().startswith(prefix) for prefix in ('http://', 'https://', 'data:')):
            return match.group(0)

        # If the file doesn't exist on disk, leave the reference as is (broken).
        if not os.path.isfile(img_path):
            return match.group(0)

        # Read and embed the image as base64
        with open(img_path, 'rb') as f:
            img_data = f.read()
        encoded = base64.b64encode(img_data).decode('utf-8')
        # Rebuild the Markdown image tag but with data URI
        return f'![{alt_text}](data:image/png;base64,{encoded})'

    # 1) Convert local images into base64 within the Markdown text
    content = re.sub(pattern, to_base64, content)

    # 2) Convert the entire Markdown to HTML
    html = markdown.markdown(content, extensions=['tables', 'fenced_code', 'toc', 'md_in_html'])

    # 3) Use BeautifulSoup to add classes or further tweak the HTML
    soup = BeautifulSoup(html, 'html.parser')

    # Render the tables
    for table in soup.find_all('table'):
        # Get whatever classes the table already has, or an empty list if none
        existing_classes = table.get('class') or list()

        # Use a set so we don't add duplicates
        updated_classes = set(existing_classes).union({'table', 'table-striped', 'table-bordered'})

        # Assign the updated classes back to the table
        table['class'] = list(updated_classes)

    return str(soup)


def convert_html_to_pdf(html_str: str, output_file: Optional[str | Path] = None) -> Any:
    """
    Convert HTML to PDF.

    Convert HTML to PDF while applying page and image scaling rules
    so that large images do not get cut off.
    """
    # Define CSS that scales images and applies basic page sizing
    style = """
    @page {
        size: A4;             /* Adjust if you'd like a different format */
        margin: 2cm;          /* Adjust margins as desired */
    }


    img {
        max-width: 100%;      /* Scale down images that exceed page width */
        height: auto;         /* Preserve aspect ratio */
        display: block;       /* Avoid text wrapping around large images */
    }

    /* Optional supplemental table styling in addition to Bootstrap classes */
    table {
        width: 100%;
        margin-bottom: 1em;   /* Nice spacing after tables */
        border-collapse: collapse;
    }

    table, th, td {
        border: 1px solid #dee2e6;  /* Lightweight border for tables in PDF */
        vertical-align: top;
        padding: 0.75rem;
    }

    /* Example: if you want consistent header background in PDF */
    thead th {
        background-color: #f8f9fa;
        border-bottom: 2px solid #dee2e6;
    }
    """
    # Create a WeasyPrint CSS object from the style string
    stylesheet = weasyprint.CSS(string=style)

    # Build the PDF in-memory, applying the custom stylesheet
    pdf_data = weasyprint.HTML(string=html_str).write_pdf(target=output_file, stylesheets=[stylesheet])

    return pdf_data
