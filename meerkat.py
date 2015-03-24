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
import difflib


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
            ['-o', '--old-syntax'],
            {
                'action': 'store_true',
                'dest': 'oldSyntax',
                'help': 'Also show the old syntax errors so that you can compare'
            }
        ),
        (
            ['-t', '--test'],
            {
                'action': 'store_true',
                'dest': 'test',
                'help': 'test mode. Will give you commands to unit test and behat test this patch, or run the commands automatically with -r'
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
        (
            ['-u', '--unit'],
            {
                'action': 'store_true',
                'help': 'Run unit tests only'
            }
        ),
        (
            ['--behat'],
            {
                'action': 'store_true',
                'help': 'Run behat tests only'
            }
        ),
        (
            ['-l', '--commands-on-lines'],
            {
                'action': 'store_true',
                'dest': 'linify',
                'help': 'Print out test commands on seperate lines'
            }
        ),
    ]
    _description = 'Tools to help you peer review an issue, or automatically check your issue before submitting for peer review'

    def run(self, args):

        M = self.Wp.resolve()
        if not M:
            raise Exception('This is not a Moodle instance')

        # Get the mode.
        if args.syntax:
            mode = 'syntax'
        elif args.test:
            mode = 'test'
        elif args.all:
            mode = 'all'
        else:
            if args.behat or args.unit:
                mode = 'test'
            elif args.mode:
                mode = args.mode

        git = M.git()

        # TODO if codechecker is not installed, then mdk plugin install local_codechecker
        # TODO if moodlecheck is not installed, then mdk plugin install local_moodlecheck

        modifiedFiles = git.modifiedFiles(args.branch)

        if mode in ('syntax', 'all'):

            for modifiedFile in modifiedFiles:

                print '%s:' % modifiedFile
                
                diff = self.runCommand("git diff %s %s" % (args.branch, modifiedFile))

                changedLineNums = []
                ranges = re.findall(r'@@.*-(.*),(.*)\+(.*),(.*)@@.*\n(.*\n([^@].*\n)*^)', diff, re.MULTILINE)

                for lineRange in ranges:
                    start = int(lineRange[2])
                    lineNo = start

                    thisDiff = lineRange[4].splitlines()
                    for diffLine in thisDiff:
                        if re.match(r'\s*\+', diffLine):
                            changedLineNums.append(lineNo)
                        if re.match(r'\s*\-', diffLine):
                            lineNo -= 1
                        lineNo += 1

                changedLinesRegex = '|'.join([str(x) for x in changedLineNums])

                syntaxResults = self.syntaxCheck(modifiedFile)
                changedLines = re.findall('(^\s*(' + changedLinesRegex + ')\s+\|\s*([^\s]*)\s+\|\s+(.*$.*(\n\s*\|.*$)*))', syntaxResults, re.MULTILINE)
                for changedLine in changedLines:
                    print changedLine[1] + ' (codechecker ' + changedLine[2].lower() + '): ' + re.sub(r'\n\s*\|\s*\| ', ' ', changedLine[3], 0, re.MULTILINE)

                docsResults = self.docsCheck(modifiedFile)
                changedLines = re.findall('(.*\sline="(' + changedLinesRegex + ')"\sseverity="([^"]*)"\smessage="([^"]*)".*)', docsResults, re.MULTILINE)
                for changedLine in changedLines:
                    print changedLine[1] + ' (moodlecheck ' + changedLine[2].lower() + '): ' + changedLine[3]

        if mode in ('test', 'all'):

            testDirectories = []

            for modifiedFile in modifiedFiles:

                testDirectory = None

                currentPath = modifiedFile

                while not testDirectory and currentPath:

                    candidate = '%s/tests' % currentPath
                    if os.path.isdir(candidate):
                        testDirectory = candidate

                    try:
                        currentPath = currentPath[:currentPath.rindex('/')]
                    except ValueError as e:
                        currentPath = ''

                testDirectories.append(testDirectory)

            testDirectories = list(set(testDirectories))

            for testDirectory in testDirectories:

                unitTests = []
                behatTests = []


                unitTests.extend(self.getSubfilesWithExtension(testDirectory, '_test.php'))

                if os.path.isdir('%s/behat' % testDirectory):

                    behatTests.extend(self.getSubfilesWithExtension('%s/behat' % testDirectory, '.feature'))

                commands = []

                if (not args.behat or args.unit):
                    commands.extend(['mdk phpunit -r -u %s' % s for s in unitTests])

                if (args.behat or not args.unit):
                    commands.extend(['mdk behat -r -f %s' % s for s in behatTests])

                for command in commands:
                    if (args.run):
                        print self.runCommand(command)
                    elif (args.linify):
                        print '%s\n' % command,
                    else:
                        print '%s &&' % command,

    def syntaxCheck(self, file):
        codechecker = Popen(['php', 'local/codechecker/run.php', file], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        return codechecker.communicate()[0]

    def docsCheck(self, file):
        mooodlecheck = Popen(['php', 'local/moodlecheck/cli/moodlecheck.php', '-p=%s' % file], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        return mooodlecheck.communicate()[0]

    def getSubfilesWithExtension(self, folder, extension):

        subfilesWithExtension = []

        if folder is None:
            return []

        subfiles = os.listdir(folder)

        for file in subfiles:

            fileWithPath = folder + '/' + file

            try:

                file.index(extension)
                subfilesWithExtension.append(fileWithPath)

            except ValueError as e:
                pass

        return subfilesWithExtension

    def runCommand(self, command):

        program = Popen(command.split(' '), stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        return program.communicate()[0]
