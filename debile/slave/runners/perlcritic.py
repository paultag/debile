# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2013 Leo Cavaille <leo@cavaille.net>
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

from debile.slave.wrappers.perlcritic import parse_perlcritic
from debile.slave.utils import run_command, cd


def perlcritic(dsc, analysis):
    run_command(["dpkg-source", "-x", dsc, "source"])
    with cd('source'):
        out, err, ret = run_command([
            'perlcritic', '--brutal', '.', '--verbose',
            '%f:%l:%c %s    %p    %m\n'
        ])
        if ret == 1:
            raise Exception("Perlcritic had an internal error")

        failed = ret == 2
        for issue in parse_perlcritic(out.splitlines()):
            analysis.results.append(issue)

        return (analysis, out, failed, None)


def version():
    out, err, ret = run_command(['perlcritic', '--version'])
    if ret != 0:
        raise Exception("perlcritic is not installed")
    return ('perlcritic', out.strip())
