#!/usr/bin/env python3

import termios, sys, tty
import inquirer
import textwrap
import subprocess

from collections import namedtuple

def main():

  if not somethingToCommit():
    print("There is nothing staged to commit")
    return

  parameters = readParameters()

  menuEntry = showMenu(parameters.menu)

  shortMessage = getShortMessage(menuEntry,
                                 underscores=parameters.maxLength)

  longMessage = getInput("Longer description: ")

  issueCode = getInput("Issue code: ")

  breakingChange = getInput("Breaking change: ")

  commitMessage = buildCommitMessage(shortMessage,
                                     longMessage,
                                     issueCode,
                                     breakingChange)

  commit(commitMessage)

  return 0


## ----------------------------------------------------------------------------

def somethingToCommit():
  return subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 1

def readParameters():
  """
  Read the parameters configuration file in current project

  This function will read the .gitmess file located in the root folder of the
  git project and use it to set up the commit message style.

  If not file is presented then default values are used

  Returns all the parameters in a namedtuple structure

  """
  params = {}
  params['maxLength'] = 80
  params['menu'] = [("feat", "New feature"),
                    ("fix", "Bug fix"),
                    ("chore", "Build process or auxiliary tool change"),
                    ("docs", "Documentary only changes"),
                    ("refactor", "Code that neither changes or add a feature"),
                    ("style", "Markup, white-space, formatting..."),
                    ("perf", "Code change that improves performance"),
                    ("test", "Adding tests"),
                    ("release", "Release version")]

  tupleConstructor = namedtuple('params', ' '.join(sorted(params.keys())))

  return tupleConstructor(**params)


def showMenu(menu):
  """

  Shows the menu checkbox list to choose the commit type

  A menu checkbox list is built and prompted from the menu attribute of the
  parameters.

  The function returns a string with the commit types separated by a comma (if
  there are multiple)

  If no type is chosen the method raises a RuntimeError

  """

  menuQuestions = [ (label + ":" + text, label) for (label, text) in menu ]

  questions = [
  inquirer.Checkbox('type',
                    message="Select the type(s) of change you are committing?",
                    choices=menuQuestions)
  ]

  choices = inquirer.prompt(questions)['type']

  if len(choices) == 0:
    raise RuntimeError("Please choice a type")

  return ','.join(choices)




def getInput(question):
  print(question)
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



def getChar():
  fd = sys.stdin.fileno()
  oldSettings = termios.tcgetattr(fd)
  try:
    tty.setraw(fd)
    ch = sys.stdin.read(1)
  finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, oldSettings)
  return ch



def getShortMessage(prefix="", underscores=20, blankChar='_'):

    prefix += ": "

    word = ""

    print(prefix + (underscores - len(word) - len(prefix)) * blankChar, end='\r', flush=True)
    # Reprint prefix to move cursor
    print(prefix, end="", flush=True)

    escapeNext = 0
    while True:
        ch = getChar()
        chUTF8 = ch.encode("UTF-8")
        ch = str(ch)

        if escapeNext > 0:
          escapeNext -= 1
          continue
        if chUTF8 in b'\x08\x7f':
            # Remove character if backspace
            word = word[:-1]
        elif chUTF8 in b'\r':
            # break if enter pressed
            break
        elif ord(ch) == 27:
          escapeNext = 2
        elif ord(ch) == 3:
          raise KeyboardInterrupt
        elif len(word) + len(prefix) == underscores:
          continue
        elif ord(ch) > 30:
          word += ch

        # Print `\r` to return to start of line and then print prefix, word and underscores.
        print('\r' + prefix + word + (underscores - len(word) - len(prefix)) * blankChar, end='\r', flush=True)
        # Reprint prefix and word to move cursor
        print(prefix + word, end="", flush=True)
    print()

    return prefix + word


def commit(message):
  subprocess.run(["git", "commit", "--message", message])

if __name__ == "__main__":
  main()
