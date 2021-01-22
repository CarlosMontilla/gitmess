#!/usr/bin/env python3

import termios, sys, tty
import inquirer
import textwrap
import subprocess

from collections import namedtuple

def main():

  if not somethingToCommit():
    print("There is nothing staged to commit")
    #return

  parameters = readParameters()

  menuEntry = showMenu(parameters.menu)

  shortMessage = getShortMessage(menuEntry,
                                 length=parameters.MaxLength,
                                 blankChar=parameters.BlankChar)

  longMessage = getInput("Longer description: ")

  issueCode = getInput("Issue code: ")

  breakingChange = getInput("Breaking change: ")

  commitMessage = buildCommitMessage(shortMessage,
                                     longMessage,
                                     issueCode,
                                     breakingChange,
                                     parameters)

  commit(commitMessage, parameters)

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

  paramsFilename = ".gitmess"

  paramsfid = open(paramsFilename, 'r')

  paramsFile = {}
  paramsFile["AddType"] = []
  for line in paramsfid:

    try:
      (key, value) = line.strip('\n').split(' ', maxsplit=1)
    except ValueError:
      key = line.strip('\n')
      value = ''

    if key == "AddType":
      (type, description) = value.split(' ', maxsplit=1)
      paramsFile[key].append((type, description))
    else:
      paramsFile[key] = value


  params = {}
  params['menu'] = []

  if ("UseDefaultMenu" in paramsFile) and \
     (paramsFile["UseDefaultMenu"] == "yes"):


    params['menu'] = [("feat", "New feature"),
                      ("fix", "Bug fix"),
                      ("chore", "Build process or auxiliary tool change"),
                      ("docs", "Documentary only changes"),
                      ("refactor", "Code that neither changes or add a feature"),
                      ("style", "Markup, white-space, formatting..."),
                      ("perf", "Code change that improves performance"),
                      ("test", "Adding tests"),
                      ("release", "Release version")]

  params['menu'].extend(paramsFile['AddType'])



  params['MaxLength'] = int(paramsFile.get("MaxLength", 80))
  params['WrapLength'] = int(paramsFile.get("WrapLength", 80))
  params['BlankChar'] = paramsFile.get("BlankChar", "_")[0]
  params["ConfirmCommit"] = paramsFile.get("ConfirmCommit", "yes")


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

  menuQuestions = [ (label + ": " + text, label) for (label, text) in menu ]

  menuMessage = "Select the type(s) of change you are committing " + \
    "(Press SPACE to select)"

  questions = [
  inquirer.Checkbox('type',
                    message=menuMessage,
                    choices=menuQuestions)
  ]

  choices = inquirer.prompt(questions)['type']

  if len(choices) == 0:
    raise RuntimeError("Please choice a type")

  return ','.join(choices)




def getInput(question):
  """

  Prompt a question and reads the input of the user

  Returns a string with the input typed by the user

  """
  print(question)
  return input()

def buildCommitMessage(shortMessage, longMessage, issue, breaking, params):
  """

  Builds the final commit message based on all the user inputs.

  Returns a string with the final commit message to be used

  """
  cm = ""

  cm = shortMessage

  if longMessage:
    cm += '\n\n' +  '\n'.join(textwrap.wrap(longMessage,
                                            width=params.WrapLength))

  if issue:
    cm += "\n\n" + 'Issue: ' + issue

  if breaking:
    cm += "\n\n" + "BREAKING CHANGE: " + breaking

  return cm



def getChar():
  """

  Reads a character typed in the keyboard

  This function read a single character pressed by the user and returns it

  """
  fd = sys.stdin.fileno()
  oldSettings = termios.tcgetattr(fd)
  try:
    tty.setraw(fd)
    ch = sys.stdin.read(1)
  finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, oldSettings)
  return ch



def getShortMessage(prefix="", length=80, blankChar='_'):
  """

  Builds the prompt for the short message

  This function shows the user a prompt line where he/she can type a message,
  but imposing a maximum number of characters. The message is composed by a
  prefix, followed by a colon and a space, followed by the user's input. The
  remaining characters left are shown by a blankChar (which defaults to '_').
  If the user tries to go above the maximum number of characters, their input
  is just ignored.

  This method accepts backspace for deleting characters, but it does not read
  the keyboard arrows to move the cursor.

  This method returns the prefix + colon + space + the user's input

  """

  prefix += ": "
  lp = len(prefix)

  word = ""
  cursorPos = lp

  messageLine = prefix + (length - len(word) - lp) * blankChar

  printnow = lambda message="", end="\n": print(message, end=end, flush=True)

  printnow(messageLine, end='\r')
  # Reprint prefix to move cursor
  printnow(messageLine[:cursorPos], end="")

  escapeNext = 0
  while True:
    ch = getChar()
    chUTF8 = ch.encode("UTF-8")
    ch = str(ch)

    if escapeNext > 0:
      escapeNext -= 1
      if ord(ch) == 68 and (cursorPos > lp):
        cursorPos -= 1
      elif (ord(ch) == 67) and (cursorPos < lp + len(word)):
        cursorPos +=1
      else:
        continue
    elif chUTF8 in b'\x08\x7f':
      # Remove character if backspace
      cursorPosWord = cursorPos - lp

      if cursorPosWord > 0:
        word = word[:(cursorPosWord-1)] + word[(cursorPosWord):]
        cursorPos -= 1

    elif chUTF8 in b'\r':
      # break if enter pressed
      break
    elif ord(ch) == 27:
      escapeNext = 2
    elif ord(ch) == 3:
      raise KeyboardInterrupt
    elif len(word) + lp == length:
      continue
    elif ord(ch) > 30:
      cursorPosWord = cursorPos - lp
      word = word[:cursorPosWord] + ch + word[cursorPosWord:]
      cursorPos += 1

    # Print line once
    printnow('\r', end='')
    messageLine = prefix + word + (length - len(word) - lp) * blankChar
    printnow(messageLine, end='\r')
    # Reprint prefix and word to move cursor
    printnow(messageLine[:cursorPos], end="")

  printnow()
  return prefix + word


def commit(message, params):
  """

  Runs git to commit staged files with a given message

  """

  if params.ConfirmCommit == "yes":

    print("\n\n" + message + "\n")

    shouldCommit = inquirer.prompt(
    [inquirer.List('confirm',
                  message='Do you want to commit with the above message?',
                  choices=['yes', 'no'],
                  default='no'),]
    )['confirm']
  else:
    shouldCommit = "yes"

  if shouldCommit == "yes":
    subprocess.run(["git", "commit", "--message", message])

if __name__ == "__main__":
  main()
