from app.services.parsers.pingdom import PingdomParser
from app.services.parsers.esicia_monitor import ESICIAMonitorParser
from app.services.parsers.aos import AOSParser
from app.services.parsers.generic import GenericParser

PARSERS = [
    PingdomParser,
    ESICIAMonitorParser,
    AOSParser,
]


def get_parser(sender: str):
    sender = (sender or "").lower()
    for parser in PARSERS:
        if parser.matches(sender):
            return parser
    return GenericParser
