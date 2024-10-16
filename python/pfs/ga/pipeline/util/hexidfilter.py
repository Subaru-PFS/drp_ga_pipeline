from .idfilter import IDFilter

class HexIDFilter(IDFilter):
    """
    Implements an argument parser for hex ID filters and logic to match
    ranges of hex IDs within file names.
    """

    def __init__(self, *values, name=None, format=None, orig=None):

        format = format if format is not None else '0x{:x}'

        super().__init__(*values, name=name, format=format, orig=orig)

    def _parse_value(self, value):
        return int(value, 16)