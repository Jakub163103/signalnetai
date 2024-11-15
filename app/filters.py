from markupsafe import Markup, escape
import re

def nl2br(value):
    """
    Replace newlines with <br> tags.
    """
    escaped_value = escape(value)
    # Replace \n, \r\n, or \r with <br>
    result = re.sub(r'\r\n|\r|\n', '<br>', escaped_value)
    return Markup(result)
