#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moodle Development Kit

Copyright (c) 2013 Frédéric Massart - FMCorz.net

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

http://github.com/FMCorz/mdk
"""

import re
import os
import logging
from datetime import datetime
from .. import tools, jira, fetch
from ..command import Command
from ..tools import question, ProcessInThread
from subprocess import Popen, PIPE, STDOUT
import os


class MeerkatCommand(Command):

    _arguments = [
        (
            ['-s', '--syntax'],
            {
                'action': 'store_true',
                'dest': 'syntax',
                'help': 'syntax mode. Will give an overview of any syntax errors added'
            }
        ),
        (
            ['-t', '--test'],
            {
                'action': 'store_true',
                'dest': 'test',
                'help': 'test mode. Will give you commands to run to test this patch, or run the commands automatically with -r'
            }
        ),
        (
            ['-r', '--run'],
            {
                'action': 'store_true',
                'help': 'run the tests (used with t).'
            }
        ),
        (
            ['-a', '--all'],
            {
                'action': 'store_true',
                'dest': 'all',
                'help': 'run all Meerkat utilities'
            }
        ),
        (
            ['-b', '--branch'],
            {
                'action': 'store',
                'default': 'master', # TODO this should be MOODLE_XX_STABLE if need be
                'help': 'the main branch to which we should compare this branch'
            }
        ),
        (
            ['-m', '--mode'],
            {
                'action': 'store',
                'choices': ['syntax', 'test', 'all'],
                'default': 'syntax',
                'help': 'define the mode to use'
            }
        ),
    ]
    _description = 'Tools to help you peer review an issue, or automatically check your issue before submitting for peer review'

    def run(self, args):

        M = self.Wp.resolve()
        if not M:
            raise Exception('This is not a Moodle instance')

        # Get the mode.
        mode = args.mode
        if args.syntax:
            mode = 'syntax'
        elif args.test:
            mode = 'test'
        elif args.all:
            mode = 'all'

        run = args.run
        branch = args.branch

        git = M.git()

        # TODO if codechecker is not installed, then mdk plugin install local_codechecker
        # TODO if moodlecheck is not installed, then mdk plugin install local_moodlecheck

        after = ''
        before = ''
        modifiedFiles = git.patchedFiles(branch)

        if mode in ('syntax', 'all'):

            for modifiedFile in modifiedFiles:
                after += '\n=====\n(After) File: %s\n=====\n' % modifiedFile
                after += self.syntaxCheck(modifiedFile)

            git.checkout(branch)

            stashed = git.stash()

            for modifiedFile in modifiedFiles:
                before += '\n=====\n(Before) File: %s\n=====\n' % modifiedFile
                before += self.syntaxCheck(modifiedFile)
            
            git.checkout('@{-1}')

            if (stashed):
                git.stash(command='pop')

            print before
            print after

        if mode in ('test', 'all'):

            testDirectory = None

            for modifiedFile in modifiedFiles:

                currentPath = modifiedFile adfsdfasdas

                while not testDirectory and currentPath:

                    print currentPath
                    try:
                        currentPath = currentPath[:currentPath.rindex('/')]
                    except ValueError as e:
                        currentPath = ""


                print currentPath


    def syntaxCheck(self, file):

        codechecker = Popen(['php', 'local/codechecker/run.php', file], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        diagnosis = codechecker.communicate()[0];

        mooodlecheck = Popen(['php', 'local/moodlecheck/cli/moodlecheck.php', '-p=%s' % file], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        diagnosis += mooodlecheck.communicate()[0];

        return diagnosis
