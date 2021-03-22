#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
JPEG codestream-parser (All-JPEG Codestream/File Format Parser Tools)
See LICENCE.txt for copyright and licensing conditions.
"""
from __future__ import print_function, division
import string

from jp2utils import print_indent, version, flags, print_hex, ordb, ordl, ordq, UnexpectedEOF, InvalidBoxLength


class JP2Box:
    def __init__(self, box, infile, offs=0):
        self.infile = infile
        if box is None:
            self.indent = 0
            self.offset = 0
            self.end = 0
        else:
            self.indent = box.indent
            self.offset = box.offset + offs
            self.end = box.target
        self.hdrsize = 0
        self.boxsize = 0
        self.target = 0
        self.bodysize = 0

    def print_indent(self, buf, nl=True):
        print_indent(buf, self.indent, nl)

    def print_versflags(self, buf):
        self.print_indent("Version         : %d" % version(buf))
        self.print_indent("Flags           : 0x%06x" % flags(buf))

    def new_box(self, description):
        if self.indent == 0:
            self.print_indent("%-8s: New Box: %s " % (str(self.offset - self.hdrsize), description), False)
        else:
            self.print_indent("%-8s: Sub Box: %s " % (str(self.offset - self.hdrsize), description), False)
        self.indent += 1

    def end_box(self):
        self.indent -= 1
        print("")

    def print_hex(self, buf):
        print_hex(buf, self.indent)

    def boxname(self, id):
        try:
            for i in range(4):
                string.index(string.letters + string.digits, id[i])
            return id
        except ValueError:
            return "0x%02x%02x%02x%02x" % (ordb(id[0]), ordb(id[1]), ordb(id[2]), ordb(id[3]))

    def parse_string_header(self, buf):
        length = ordl(buf)
        id = buf[4:8]
        buf = buf[8:len(buf)]

        # Read XLBox (extra box length, if any)
        if length == 1:
            xlength = buf[0:8]
            buf = buf[8:len(buf)]
            if len(xlength) < 8:
                raise UnexpectedEOF
            length = ordq(xlength)
            if length < 16:
                raise InvalidBoxLength(self.boxname(id))
            else:
                length -= 16
        elif 0 < length < 8:
            raise InvalidBoxLength(self.boxname(id))
        elif length > 0:
            length -= 8

        return buf, length, id

    def parse_header(self):
        if self.end > 0:
            if self.infile.tell() == self.end:
                return []
            elif self.infile.tell() > self.end:
                raise InvalidBoxLength("unknown box")
        length = self.infile.read(4)
        if len(length) == 0:
            return []
        elif len(length) < 4:
            raise UnexpectedEOF()
        length = ordl(length)
        id = self.infile.read(4).decode('ascii')
        if len(id) < 4:
            raise UnexpectedEOF
        self.offset += 8
        self.hdrsize = 8

        # Read XLBox (extra box length, if any)
        if length == 1:
            xlength = self.infile.read(8)
            self.offset += 8
            self.hdrsize = 16
            if len(xlength) < 8:
                raise UnexpectedEOF
            length = ordq(xlength)
            if length < 16:
                raise InvalidBoxLength(self.boxname(id))
            else:
                length -= 16
        elif 0 < length < 8:
            raise InvalidBoxLength(self.boxname(id))
        elif length > 0:
            length -= 8
        elif length == 0:
            return id,

        self.boxsize = length
        return length, id

    def readbody(self):
        """Read Box Content"""
        if self.bodysize > 0:
            buf = self.infile.read(self.bodysize)
        else:
            buf = self.infile.read()
        return buf

    def parse(self, hook):
        """Parse a container box and call the hook for each sub-box."""
        while True:
            # Read LBox (box length)
            header = self.parse_header()
            if len(header) == 0:
                return
            if len(header) == 1:
                id = header[0]
                self.new_box('"%s"' % id)
                hook(self, id, "all up to EOF")
                self.end_box()
                continue

            length = header[0]
            id = header[1]
            self.bodysize = length
            self.target = self.infile.tell() + length

            # Call hook
            self.new_box('"%s"' % id)
            hook(self, id, "%d" % length)

            self.infile.seek(self.target)

            self.offset += length
            self.end_box()
