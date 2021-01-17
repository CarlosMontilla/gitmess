#!/usr/bin/env python3

import termios, sys, tty
import inquirer
import textwrap
import subprocess

from collections import namedtuple

def main():

  parameters = readParameters()

  menuEntry = showMenu(parameters.menu)
  shortMessage = getShortMessage(menuEntry, underscores=parameters.maxLength)
  longMessage = getLongMessage()
  issueCode = getIssue()
  breakingChange = getBreakingChange()

  commitMessage = buildCommitMessage(shortMessage, longMessage, issueCode, breakingChange)

  commit(commitMessage)

def readParameters():
  params = {}
  params['maxLength'] = 80
  params['menu'] = [("feat", "A new feature"),
                    ("fix", "A bug fix"),
                    ("chore", "Build process or auxiliary tool change"),
                    ("docs", "Documentary only changes"),
                    ("refactor", "A code that neither changes or add a feature"),
                    ("style", "Markup, white-space, formatting..."),
                    ("perf", "A code change that improves performance"),
                    ("test", "Adding tests"),
                    ("release", "A new release version")]

  tupleConstructor = namedtuple('params', ' '.join(sorted(params.keys())))


  return tupleConstructor(**params)

def showMenu(menu):

  menuQuestions = [ (label + ":" + text, label) for (label, text) in menu ]

  questions = [
  inquirer.Checkbox('type',
                message="Select the type of change you are committing?",
                choices=menuQuestions,
                ),
  ]

  choices = inquirer.prompt(questions)['type']

  if len(choices) == 0:
    raise RuntimeError("Please choice a type")

  return ','.join(choices)

def unixGetCh():
    def _getch():
        fd = sys.stdin.fileno()
        oldSettings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, oldSettings)
        return ch
    return _getch()

def getLongMessage():
  print("Long message:")
  return input()

def getIssue():
  print("Issue code:")
  return input()

def getBreakingChange():
  print("Breaking change?:")
  return input()

def buildCommitMessage(shortMessage, longMessage, issue, breaking):

  cm = ""

  cm = shortMessage

  if longMessage:
    cm += '\n\n' +  '\n'.join(textwrap.wrap(longMessage, width=80))

  if issue:
    cm += "\n\n" + 'Issue: ' + issue

  if breaking:
    cm += "\n\n" + "BREAKING CHANGE: " + breaking

  return cm

def getShortMessage(prefix="", underscores=20, blankChar='_'):

    prefix += ": "

    word = ""

    try:
        import msvcrt
        func = msvcrt.getch
    except:
        func = unixGetCh

    print(prefix + (underscores - len(word) - len(prefix)) * blankChar, end='\r', flush=True)
    # Reprint prefix to move cursor
    print(prefix, end="", flush=True)

    escapeNext = 0
    while True:
        ch = func()
        ch = ch.encode("UTF-8")
        if ch in b'\x08\x7f':
            # Remove character if backspace
            word = word[:-1]
        elif ch in b'\r':
            # break if enter pressed
            break
        else:
            if len(word) + len(prefix) == underscores:
                continue
            try:
                char = str(ch.decode("utf-8"))
            except:
                continue

            if escapeNext > 0:
                escapeNext -= 1
                continue
            elif ord(char) > 30:
                word += str(char)
            elif ord(char) == 27:
                escapeNext = 2;
            elif ord(char) == 3:
              word = ""
              raise KeyboardInterrupt
        # Print `\r` to return to start of line and then print prefix, word and underscores.
        print('\r' + prefix + word + (underscores - len(word) - len(prefix)) * blankChar, end='\r', flush=True)
        # Reprint prefix and word to move cursor
        print(prefix + word, end="", flush=True)
    print()
    return prefix + word


def commit(message):
  subprocess.call(['git commit --message \"' + message + '\"'], shell=True)

if __name__ == "__main__":
  main()
