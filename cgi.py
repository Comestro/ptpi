"""Minimal compatibility shim for packages expecting the removed stdlib cgi module.

Python 3.13 removed ``cgi``. This project still depends on an older ``httpx``
version through ``googletrans`` that imports ``cgi.parse_header``.
"""

from email.message import Message


def parse_header(line):
    message = Message()
    message["content-type"] = line
    params = message.get_params() or []
    if not params:
        return line, {}

    main_value = params[0][0]
    parsed_params = {key: value for key, value in params[1:]}
    return main_value, parsed_params
