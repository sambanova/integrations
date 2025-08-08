import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def get_current_time(tz_identifier: str) -> dict:
    """Returns the current time in a specified timezone.

    Args:
        tz_identifier (str): The time zone identifier if not specified use America/New_York"

    Returns:
        dict: status and result or error msg.
    """
    try:
        tz = ZoneInfo(tz_identifier)
        now = datetime.datetime.now(tz)
        report = f'The current time in {tz_identifier} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
        return {'status': 'success', 'report': report}

    except:
        return {
            'status': 'error',
            'error_message': (f"Sorry, I don't have timezone information for {tz_identifier}."),
        }


# Mock tool
def load_user_preferences() -> dict:
    """
    Returns user-level preferences to guide the raw HTML/CSS/JS generation.
    No framework assumed. No input is required.
    """
    return {
        'theme': 'dark',  # dark or light
        'language': 'en',  # output text language
        'accessibility': False,  # follow WCAG-ish good practices
        'font_family': 'sans-serif',  # safe font families only
        'max_width': '1200px',  # layout max width
    }


# mock tool
def load_brand_colors() -> dict:
    """
    Returns brand colors to be used as inline CSS variables or in styles directly.
    """
    return {
        'primary': '#1E40AF',  # used for main actions / headers
        'secondary': '#64748B',  # supporting text or background
        'accent': '#0BF52A',  # highlights or CTAs
        'background': '#C5C8CF',  # full page background
        'text': '#000000',  # main text color
    }


def save_html_file(content: str, filename: str = 'generated_page.html', output_dir: str = './output') -> str:
    """
    Saves the generated HTML content to a file.

    Args:
        content (str): The full HTML content including inline CSS/JS.
        filename (str): The name of the output HTML file should include .html.
        output_dir (str): The directory to save the file in.

    Returns:
        str: Path to the saved HTML file.
    """

    base_dir = Path(__file__).resolve().parent.parent
    output_dir = base_dir / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = Path(output_dir) / filename

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return f'file saved in {str(file_path)}'
