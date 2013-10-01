# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import os
import fnmatch

from debile.master.utils import session
from debile.master.orm import People

from sqlalchemy.orm.exc import NoResultFound

from debile.utils.changes import parse_changes_file, ChangesFileException


def process_directory(path):
    abspath = os.path.abspath(path)
    for fp in os.listdir(abspath):
        path = os.path.join(abspath, fp)
        for glob, handler in DELEGATE.items():
            if fnmatch.fnmatch(path, glob):
                handler(path)
                break


def process_changes(path):
    changes = parse_changes_file(path)
    try:
        changes.validate()
    except ChangesFileException as e:
        return reject_changes(changes, "invalid-upload")

    key = changes.validate_signature()

    if changes.is_source_only_upload():
        try:
            with session() as s:
                who = s.query(People).filter_by(key=key).one()
        except NoResultFound:
            return reject_changes(changes, "invalid-user")

        return accept_source_changes(changes, who)

    if changes.is_binary_only_upload():
        return accept_binary_changes(changes, who)

    raise Exception

def process_dud(path):
    pass


def reject_dud():
    pass


def accept_dud():
    pass


def reject_changes(changes, tag):
    print "REJECT: {source} because {tag}".format(
        tag=tag, source=changes.get_package_name())

    for fp in [changes.get_filename()] + changes.get_files():
        os.unlink(fp)
    # Note this in the log.


def accept_source_changes(changes, user):
    pass


def accept_binary_changes(changes, user):
    pass


DELEGATE = {
    "*.changes": process_changes,
    "*.dud": process_dud,
}
