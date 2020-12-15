# -*- coding: utf-8 -*-
"""
JPEG codestream-parser (All-JPEG Codestream/File Format Parser Tools)
See LICENCE.txt for copyright and licensing conditions.
"""
from __future__ import print_function
import struct
import sys


class JP2Error(Exception):
    def __init__(self, reason):
        super(JP2Error, self).__init__(reason)


class InvalidMarker(JP2Error):
    def __init__(self, marker):
        super(InvalidMarker, self).__init__("marker 0xff{} can't appear here".format(marker))
        self.marker = marker


class InvalidSizedMarker(JP2Error):
    def __init__(self, marker):
        super(InvalidSizedMarker, self).__init__("invalid sized marker {}".format(marker))
        self.marker = marker


class InvalidMarkerField(JP2Error):
    def __init__(self, marker, field):
        super(InvalidMarkerField, self).__init__("invalid field {} in marker {}".format(field, marker))
        self.marker = marker
        self.field = field


class RequiredMarkerMissing(JP2Error):
    def __init__(self, marker):
        super(RequiredMarkerMissing, self).__init__("required marker 0xff{} missing".format(marker))
        self.marker = marker


class UnexpectedEOC(JP2Error):
    def __init__(self):
        super(UnexpectedEOC, self).__init__("unexpected end of codestream")


class UnexpectedEOF(JP2Error):
    def __init__(self):
        super(UnexpectedEOF, self).__init__("unexpected end of file")


class MisplacedData(JP2Error):
    def __init__(self):
        super(MisplacedData, self).__init__("marker expected")


class InvalidBoxSize(JP2Error):
    def __init__(self):
        super(InvalidBoxSize, self).__init__("invalid sized box")


class InvalidBoxLength(JP2Error):
    def __init__(self, box):
        super(InvalidBoxLength, self).__init__("box {} has invalid length".format(box))
        self.box = box


class BoxSizesInconsistent(JP2Error):
    def __init__(self):
        super(BoxSizesInconsistent, self).__init__("box sizes are not consistent over box segments")


class BaseCodestream(object):
    def __init__(self, indent=0):
        self._indent = indent
        self._headers = []
        self._markerpos = 0

    def _print_indent(self, buf):
        print_indent(buf, self._indent)

    def _new_marker(self, name, description):
        self._print_indent("%-8s: New marker: %s (%s)" %
                           (str(self._markerpos), name, description))
        print("")
        self._indent += 1
        self._headers = []

    def _end_marker(self):
        self._flush_marker()
        self._indent -= 1
        print("")

    def _flush_marker(self):
        if len(self._headers) > 0:
            maxlen = 0
            for header in self._headers:
                maxlen = max(maxlen, len(header[0]))
            for header in self._headers:
                s = " " * (maxlen - len(header[0]))
                self._print_indent("%s%s : %s" % (header[0], s, header[1]))
            print("")
            self._headers = []


def convert_hex(buf, indent=0, sec_indent=-1, plain_text=False, single_line=True):
    if sec_indent == -1:
        sec_indent = indent
    lines = []
    line = ""
    buff = "  "
    for i in range(len(buf)):
        if i % 16 == 0:
            if i != 0:
                if plain_text:
                    line += buff
                lines.append(line)
                indent = sec_indent
                line = ""
                buff = "  "
            line += " " * indent
        buff += chrb(buf[i]) if 32 <= ordb(buf[i]) < 127 else "."
        line += "%02x " % (ordb(buf[i]))
    if plain_text:
        line += "   " * ((16 - (len(buf) % 16)) % 16) + buff
    lines.append(line)
    if single_line:
        return " ".join(lines)
    return lines


def print_hex(buf, indent=0, sec_indent=-1, plain_text=True):
    lines = convert_hex(buf, indent=indent, sec_indent=sec_indent, plain_text=plain_text, single_line=False)
    for line in lines:
        print(line)


def print_indent(buf, indent=0, nl=True):
    print(" " * indent + buf, end='\n' if nl else '')


def ieee_float_to_float(data):
    if data != 0:
        sign = data >> 31
        exponent = (data >> 23) & 0xff
        mantissa = data & ((1 << 23) - 1)
        if exponent == 255:
            return NotImplemented
        elif exponent != 0:
            mantissa += 1 << 23
        else:
            exponent += 1
        number = 0.0 + mantissa
        exponent -= 127 + 23
        if exponent > 0:
            number *= 2.0 ** exponent
        elif exponent < 0:
            number /= 2.0 ** (-exponent)
        if sign != 0:
            number = -number
        return number
    else:
        return 0.0


def ieee_double_to_float(data):
    if data != 0:
        sign = data >> 63
        exponent = (data >> 51) & ((1 << 11) - 1)
        mantissa = data & ((1 << 52) - 1)
        if exponent == 0x7ff:
            return NotImplemented
        elif exponent != 0:
            mantissa += 1 << 52
        else:
            exponent += 1
        number = 0.0 + mantissa
        exponent -= 1023 + 52
        if exponent > 0:
            number *= 2.0 ** exponent
        elif exponent < 0:
            number /= 2.0 ** (-exponent)
        if sign != 0:
            number = -number
        return number
    else:
        return 0.0


# This is a fake substitution for the file class that operates on a memory
# buffer.

class Buffer:
    def __init__(self, buf):
        self.offset = 0
        self.buffer = buf

    def eof_reached(self):
        return self.offset >= len(self.buffer)

    def rest_len(self):
        return len(self.buffer) - self.offset

    def __len__(self):
        return len(self.buffer)

    def __getitem__(self, offset):
        return self.buffer[offset]

    def read(self, length=-1):
        if self.eof_reached():
            return ""
        if length == -1 or length > self.rest_len():
            length = self.rest_len()
        ret = self.buffer[self.offset:self.offset + length]
        self.offset = self.offset + length
        return ret

    def tell(self):
        return self.offset

    def seek(self, where):
        self.offset = where


if sys.version_info < (3,):
    def ordb(buf):
        return struct.unpack('B', buf)[0]

    def chrb(i):
        return i
else:
    def ordb(buf):
        return buf

    def chrb(i):
        return struct.pack('B', i)


def ordw(buf):
    return struct.unpack('>H', buf)[0]


def ordl(buf):
    return struct.unpack('>L', buf)[0]


def ordq(buf):
    return struct.unpack('>Q', buf)[0]


def lordw(buf):
    return struct.unpack('<H', buf)[0]


def lordl(buf):
    return struct.unpack('<L', buf)[0]


def lordq(buf):
    return struct.unpack('<Q', buf)[0]


def chrl(i):
    return struct.pack('>L', i)


def chrq(i):
    return struct.pack('>Q', i)


def version(buf):
    return ordb(buf[0])


def flags(buf):
    return (ordb(buf[1]) << 16) + \
           (ordb(buf[2]) << 8) + \
           (ordb(buf[3]) << 0)


def fromCString(buf):
    res = ""
    for i in range(len(buf)):
        ch = ordb(buf[i])
        if ch == 0:
            return res
        elif ch < 32 or ch > 127:
            res = "%s\\%03o" % (res, ch)
        else:
            res = "%s%c" % (res, ch)
    return res


def secsToTime(total):
    seconds = total % 60
    total = total / 60
    minutes = total % 60
    total = total / 60
    hours = total % 24
    total = total / 24
    year = 1904
    while True:
        leap = False
        if year % 400 == 0:
            leap = True
        elif leap % 100 == 0:
            leap = False
        elif leap % 4 == 0:
            leap = True
        daysperyear = 365
        if leap:
            daysperyear = 366
        if total < daysperyear:
            break
        total = total - daysperyear
        year = year + 1
    dayspermonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    monthnames = ["Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dez"]
    if leap:
        dayspermonth[1] = 29
    month = 0
    for t in dayspermonth:
        if total < t:
            break
        total = total - t
        month = month + 1
    return "%02d:%02d:%02d %2d-%s-%4d" % \
           (hours, minutes, seconds, total + 1, monthnames[month], year)
