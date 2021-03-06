# -*- coding: utf-8 -*-
#
#   changes.py — .changes file handling class
#
#   This file was originally part of debexpo
#    https://alioth.debian.org/projects/debexpo/
#
#   Copyright © 2008 Jonny Lamb <jonny@debian.org>
#   Copyright © 2010 Jan Dittberner <jandd@debian.org>
#   Copyright © 2012 Arno Töll <arno@debian.org>
#   Copyright © 2012 Paul Tagliamonte <paultag@debian.org>
#
#   Permission is hereby granted, free of charge, to any person
#   obtaining a copy of this software and associated documentation
#   files (the "Software"), to deal in the Software without
#   restriction, including without limitation the rights to use,
#   copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the
#   Software is furnished to do so, subject to the following
#   conditions:
#
#   The above copyright notice and this permission notice shall be
#   included in all copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#   EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#   OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#   NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#   HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#   WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#   FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#   OTHER DEALINGS IN THE SOFTWARE.
# -*- coding: utf-8 -*-

from debile.utils import run_command
from debile import __version__
from debian import deb822
import firehose.model
import hashlib
import os.path
import sys

from email.Utils import formatdate


class Dud_(deb822.Changes):
    def add_file(self, fp):
        statinfo = os.stat(fp)
        size = statinfo.st_size

        algos = {
            "Files": "md5",
            "Checksums-Sha1": "sha1",
            "Checksums-Sha256": "sha256",
        }

        for key, algo in algos.items():
            if key not in self:
                self[key] = []

            m = hashlib.new(algo)
            with open(fp, "rb") as fd:
                for chunk in iter((lambda: fd.read(128 * m.block_size)), b''):
                    m.update(chunk)

            if key != "Files":
                self[key].append({
                    algo: m.hexdigest(),
                    "size": size,
                    "name": fp
                })
            else:
                self[key].append({
                    "md5sum": m.hexdigest(),
                    "size": size,
                    "section": 'debile',
                    "priority": 'debile',
                    "name": fp
                })


class DudFileException(Exception):
    pass


class Dud(object):
    def __init__(self, filename=None, string=None):
        if (filename and string) or (not filename and not string):
            raise TypeError

        if filename:
            self._absfile = os.path.abspath(filename)
            self._data = Dud_(open(filename))
        else:
            self._data = Dud_(string)

        if len(self._data) == 0:
            raise DudFileException('dud file could not be parsed.')
        if filename:
            self.basename = os.path.basename(filename)
        else:
            self.basename = None
        self._directory = ""

        self.is_python3 = False
        if sys.version_info[0] >= 3:
            self.is_python3 = True

    def get_filename(self):
        """
        Returns the filename from which the changes file was generated from.
        Please do note this is just the basename, not the entire full path, or
        even a relative path. For the absolute path to the changes file, please
        see :meth:`get_changes_file`.
        """
        return self.basename

    def get_firehose(self):
        return firehose.model.Analysis.from_xml(
            open(self.get_firehose_file(), 'r'))

    def get_firehose_file(self):
        for item in self.get_files():
            if item.endswith('.firehose.xml'):
                return item

    def get_log_file(self):
        for item in self.get_files():
            if item.endswith('.log.txt'):
                return item

    def get_dud_file(self):
        """
        Return the full, absolute path to the changes file. For just the
        filename, please see :meth:`get_filename`.
        """
        return os.path.join(self._directory, self.get_filename())

    def get_files(self):
        """
        """
        return [os.path.join(self._directory, z['name'])
                for z in self._data['Files']]

    def __getitem__(self, key):
        """
        Returns the value of the rfc822 key specified.

        ``key``
            Key of data to request.
        """
        return self._data[key]

    def __contains__(self, key):
        """
        Returns whether the specified RFC822 key exists.

        ``key``
            Key of data to check for existence.
        """
        return key in self._data

    def get(self, key, default=None):
        """
        Returns the value of the rfc822 key specified, but defaults
        to a specific value if not found in the rfc822 file.

        ``key``
            Key of data to request.

        ``default``
            Default return value if ``key`` does not exist.
        """
        return self._data.get(key, default)

    def validate(self, check_hash="md5", check_signature=True):
        self.validate_checksums(check_hash)
        if check_signature:
            self.validate_signature(check_signature)

    def validate_signature(self, check_signature=True):
        """
        Validate the GPG signature of a .changes file.
        """
        gpg_path = "gpg"

        (gpg_output, gpg_output_stderr, exit_status) = run_command([
            gpg_path, "--status-fd", "1", "--verify",
            "--batch", self.get_dud_file(),
        ])

        if exit_status == -1:
            raise DudFileException(
                "Unknown problem while verifying signature")

        # contains verbose human readable GPG information
        if self.is_python3:
            gpg_output_stderr = str(gpg_output_stderr, encoding='utf8')

        if self.is_python3:
            gpg_output = gpg_output.decode(encoding='UTF-8')

        if gpg_output.count('[GNUPG:] GOODSIG'):
            pass
        elif gpg_output.count('[GNUPG:] BADSIG'):
            raise DudFileException("Bad signature")
        elif gpg_output.count('[GNUPG:] ERRSIG'):
            raise DudFileException("Error verifying signature")
        elif gpg_output.count('[GNUPG:] NODATA'):
            raise DudFileException("No signature on")
        else:
            raise DudFileException(
                "Unknown problem while verifying signature"
            )

        key = None
        for line in gpg_output.split("\n"):
            if line.startswith('[GNUPG:] VALIDSIG'):
                key = line.split()[2]
        return key

    def validate_checksums(self, check_hash="md5"):
        """
        Validate checksums for a package, using ``check_hack``'s type
        to validate the package.

        Valid ``check_hash`` types:

            * sha1
            * sha256
            * md5
            * md5sum
        """
        for filename in self.get_files():
            if check_hash == "sha1":
                hash_type = hashlib.sha1()
                checksums = self.get("Checksums-Sha1")
                field_name = "sha1"
            elif check_hash == "sha256":
                hash_type = hashlib.sha256()
                checksums = self.get("Checksums-Sha256")
                field_name = "sha256"
            elif check_hash == "md5":
                hash_type = hashlib.md5()
                checksums = self.get("Files")
                field_name = "md5sum"

            for changed_files in checksums:
                if changed_files['name'] == os.path.basename(filename):
                    break
            else:
                assert(
                    "get_files() returns different files than Files: knows?!")

            with open(filename, "rb") as fc:
                for chunk in iter(
                    (lambda: fc.read(128 * hash_type.block_size)),
                    b''
                ):
                    hash_type.update(chunk)

            if not hash_type.hexdigest() == changed_files[field_name]:
                raise DudFileException(
                    "Checksum mismatch for file %s: %s != %s" % (
                        filename,
                        hash_type.hexdigest(),
                        changed_files[field_name]
                    ))


def parse_dud_file(filename, directory=None):
    """
    Parse a .changes file and return a dput.changes.Change instance with
    parsed changes file data. The optional directory argument refers to the
    base directory where the referred files from the changes file are expected
    to be located.
    """
    _c = Dud(filename=filename)
    _c.set_directory(directory)
    return(_c)
