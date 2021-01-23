#!/usr/bin/env python3

from collections import namedtuple
import termios
import sys
import tty
import textwrap
import subprocess
import shutil
import argparse
import os
import re
import inquirer

try:
  import spellchecker
except ModuleNotFoundError:
  spellchecker = None

def main(args):

  parameters = readParameters()
  if args.config:
    dumpConfig(parameters)
    return

  if not somethingToCommit():
    print("There is nothing staged to commit")
    return

  if parameters.Spellcheck == "yes" and not spellchecker:
    print("The module spellchecker is not installed")
    return

  menuEntry = showMenu(parameters)

  shortMessage = getInput(menuEntry,
                          length=parameters.MaxLength,
                          blankChar=parameters.BlankChar)

  longMessage = getInput("Longer description",
                         length=sys.maxsize,
                         blankChar='')[1]

  issueCode = getInput("Issue code",
                       length=sys.maxsize,
                       blankChar='')[1]

  breakingChange = getInput("Breaking change",
                            length=sys.maxsize,
                            blankChar='')[1]

  if parameters.Spellcheck == "yes":
    print("Starting spellchecking... ")
    shortMessage = (shortMessage[0], spellcheck(shortMessage[1], parameters))
    longMessage = spellcheck(longMessage, parameters)
    breakingChange = spellcheck(breakingChange, parameters)
    print("Spellchecking done")
    print()

  commitMessage = buildCommitMessage(shortMessage,
                                     longMessage,
                                     issueCode,
                                     breakingChange,
                                     parameters)

  commit(commitMessage, parameters)

  return


## ----------------------------------------------------------------------------

def somethingToCommit():
  return subprocess.run(["git", "diff", "--cached", "--quiet"],
                        check=False).returncode == 1

def readParameters():
  """

  Read the parameters configuration file in current project

  This function will read the .gitmess file located in the root folder of the
  git project and use it to set up the commit message style.

  If not file is presented then default values are used

  Returns all the parameters in a namedtuple structure

  """

  paramsFilename = ".gitmess"
  gitRootDirectory = subprocess.run(["git", "rev-parse",  "--show-toplevel"],
                                    capture_output=True, check=True,
                                    ).stdout.decode('utf-8').rstrip('\n')


  paramsFile = {}
  paramsFile["AddType"] = []
  try:
    paramsfid = open(gitRootDirectory + "/" + paramsFilename, 'r')

    for line in paramsfid:
      try:
        (key, value) = line.strip('\n').split(' ', maxsplit=1)
      except ValueError:
        key = line.strip('\n')
        value = ''

      if key == "AddType":
        (commitType, description) = value.split(' ', maxsplit=1)
        paramsFile[key].append((commitType, description))
      else:
        paramsFile[key] = value
  except FileNotFoundError:
    pass


  params = {}
  params['menu'] = []

  if ("UseDefaultMenu" in paramsFile) and \
     (paramsFile["UseDefaultMenu"] == "yes") or \
     ("UseDefaultMenu" not in paramsFile):


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

  params["UseDefaultMenu"] = paramsFile.get("UseDefaultMenu", "yes")
  params['MaxLength'] = int(paramsFile.get("MaxLength", 80))
  params['WrapLength'] = int(paramsFile.get("WrapLength", 80))
  params['BlankChar'] = paramsFile.get("BlankChar", "_")[0]
  params["ConfirmCommit"] = paramsFile.get("ConfirmCommit", "yes")
  params["MultipleTypes"] = paramsFile.get("MultipleTypes", "no")
  params["TypesStyle"] = paramsFile.get("TypesStyle", "comma")
  params["Spellcheck"] = paramsFile.get("Spellcheck", "yes")
  params["SpellcheckMaxOptions"] = int(paramsFile.get("SpellcheckMaxOptions", 10))

  if params["SpellcheckMaxOptions"] < 1:
    params["SpellcheckMaxOptions"] = sys.maxsize

  tupleConstructor = namedtuple('params', ' '.join(sorted(params.keys())))

  return tupleConstructor(**params)


def showMenu(params):
  """

  Shows the menu checkbox list to choose the commit type

  A menu checkbox list is built and prompted from the menu attribute of the
  parameters.

  The function returns a string with the commit types separated by a comma (if
  there are multiple)

  If no type is chosen the method raises a RuntimeError

  """

  menuQuestions = [ (label + ": " + text, label) for (label, text) in params.menu ]

  if params.MultipleTypes == "yes":
    menuType = inquirer.Checkbox
    menuMessage = "Select the type(s) of change you are committing " + \
      "(Press SPACE to select)"
  else:
    menuType = inquirer.List
    menuMessage = "\033[FSelect the type of change you are committing " + \
      "(Press ENTER to select)\r\n"

  questions = [
  menuType('type',
           message=menuMessage,
           choices=menuQuestions)
  ]

  print()
  choices = inquirer.prompt(questions)['type']

  if len(choices) == 0:
    raise RuntimeError("Please choice a type")

  if isinstance(choices, str):
    choices = [choices]

  if params.TypesStyle == "comma":
    formattedTypes = ','.join(choices)
  elif params.TypesStyle == "brackets":
    formattedTypes = ""
    for commitType in choices:
      formattedTypes += "[" + commitType + "]"

  return formattedTypes


def buildCommitMessage(shortMessage, longMessage, issue, breaking, params):
  """

  Builds the final commit message based on all the user inputs.

  Returns a string with the final commit message to be used

  """
  message = ""

  message = shortMessage[0] + shortMessage[1]

  if longMessage:
    message += '\n\n' +  '\n'.join(textwrap.wrap(longMessage,
                                                 width=params.WrapLength))

  if issue:
    message += "\n\n" + 'Issue: ' + issue

  if breaking:
    message += "\n\n" + "BREAKING CHANGE: " + breaking

  return message



def getChar():
  """

  Reads a character typed in the keyboard

  This function read a single character pressed by the user and returns it

  """
  fileDescriptor = sys.stdin.fileno()
  oldSettings = termios.tcgetattr(fileDescriptor)
  try:
    tty.setraw(fileDescriptor)
    char = sys.stdin.read(1)
  finally:
    termios.tcsetattr(fileDescriptor, termios.TCSADRAIN, oldSettings)
  return char



def getInput(prefix="", length=80, blankChar='_'):
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

  backline="\033[F"

  prefix += ": "
  lenPrefix = len(prefix)

  word = ""
  cursorPos = lenPrefix

  messageLine = prefix + (length - len(word) - lenPrefix) * blankChar
  maxLengthMessage = len(messageLine)
  (nlines, cursorLine) = printMessageWrapped(messageLine, lenPrefix)

  escapeNext = 0
  while True:
    char = str(getChar())

    if escapeNext > 0:
      escapeNext -= 1
      if ord(char) == 68 and (cursorPos > lenPrefix):
        cursorPos -= 1
      elif (ord(char) == 67) and (cursorPos < lenPrefix + len(word)):
        cursorPos +=1
      else:
        continue
    elif ord(char) == 127:
      # Remove character if backspace
      cursorPosWord = cursorPos - lenPrefix

      if cursorPosWord > 0:
        word = word[:(cursorPosWord-1)] + word[(cursorPosWord):]
        cursorPos -= 1

    elif ord(char) == 13:
      # break if enter pressed
      break
    elif ord(char) == 27:
      escapeNext = 2
    elif ord(char) == 3:
      raise KeyboardInterrupt
    elif len(word) + lenPrefix == length:
      continue
    elif ord(char) > 30:
      cursorPosWord = cursorPos - lenPrefix
      word = word[:cursorPosWord] + char + word[cursorPosWord:]
      cursorPos += 1

    # Bring back cursor to the very beginning of the input line
    print('\r', end='')
    print(backline*cursorLine, end='')

    messageLine = prefix + word + (length - len(word) - lenPrefix) * blankChar

    # Clean any old input before writing new line
    if len(messageLine) > maxLengthMessage:
      maxLengthMessage = len(messageLine)
    printMessageWrapped(' '*maxLengthMessage, 0)


    (nlines, cursorLine) = printMessageWrapped(messageLine, cursorPos)

  # Print enough new line so the new input does not overlap with this input
  print('\n'*(nlines - cursorLine), flush=True)
  return (prefix, word)


def printMessageWrapped(message, cursorPos):

  terminalSize = shutil.get_terminal_size()
  margin = 5
  cols = terminalSize.columns - margin
  backline = "\033[F"

  nlines = len(message) // cols + 1
  cursorLine = cursorPos // cols
  cursorPosLine = cursorPos % cols

  lines = [message[idx*cols:(idx+1)*cols] for idx in range(nlines)]

  # First print the entire message
  print('\n'.join(lines), end="")

  #bring back cursor to the beginning of message
  print('\r' + backline*(nlines-1), end="")

  #print until cursor
  for idx in range(cursorLine+1):
    if idx == (cursorLine):
      print(lines[idx][:cursorPosLine], end="", flush=True)
    else:
      print(lines[idx], end='\n')

  return (nlines, cursorLine)

def commit(message, params):
  """

  Runs git to commit staged files with a given message

  """

  if params.ConfirmCommit == "yes":

    headerLength = max(params.MaxLength, params.WrapLength)

    print('='*headerLength)
    print("COMMIT MESSAGE")
    print("="*headerLength)

    print("\n" + message + "\n")
    print("="*headerLength)

    shouldCommit = inquirer.prompt(
    [inquirer.List('confirm',
                  message='Do you want to commit with the above message?',
                  choices=['yes', 'no'],
                  default='no'),]
    )['confirm']
  else:
    shouldCommit = "yes"

  if shouldCommit == "yes":
    subprocess.run(["git", "commit", "--message", message], check=True)

def dumpConfig(params):
  paramsFilename = ".gitmess"
  gitRootDirectory = subprocess.run(["git", "rev-parse",  "--show-toplevel"],
                                    capture_output=True, check=True,
                                    ).stdout.decode('utf-8').rstrip('\n')

  filepath = gitRootDirectory + "/" + paramsFilename
  if not os.path.isfile(filepath):
    with open(filepath, 'w+') as fid:
      for (key, value) in params._asdict().items():
        if key != "menu":
          print(key + " " + str(value), file=fid)
  else:
    print("Configuration file already exists")

def spellcheck(message, params):

  spell = spellchecker.SpellChecker()
  wrongWords = list(spell.unknown(message.split(' ')))

  wrongWords = [words for words in wrongWords if words]

  for word in wrongWords:

    corrected = False
    userInput = ""
    userWord = ""
    originalWord = word

    while not corrected:
      print("-> Word not found in dictionary: " + word)
      print("Possible candidates are: ")
      listCandidates = list(spell.candidates(word))
      listCandidates = listCandidates[:params.SpellcheckMaxOptions]

      listCandidates = [candidate for candidate in listCandidates if candidate != word]

      if userInput:
        userWord = userInput
        listCandidates = [userWord] + listCandidates

      for idx, candidate in enumerate(listCandidates):
        print("\t" + str(idx+1) + ": " + candidate, end='')
        if userWord and idx == 0:
          print(" (your last input)")
        print()

      if len(listCandidates) == 0:
        print("\tNo suitable option was found")

      print()
      userInput = input("Select word or write a different word \n" + \
                        "(type -1 to keep the original word: " + originalWord + "\n-> ")

      try:
        idx = int(userInput)
        if idx > len(listCandidates):
          print("Please insert a number between 1 and " + str(len(listCandidates)))
          userInput = ""
          input("Press ENTER to continue")
          continue
        if idx > 0:
          newWord = listCandidates[idx-1]
          wrongReg = re.compile(re.escape(originalWord), re.IGNORECASE)
          message = wrongReg.sub(newWord, message)
        corrected = True
      except ValueError:
        newCandidates = spell.unknown([userInput])
        if not newCandidates:
          wrongReg = re.compile(re.escape(originalWord), re.IGNORECASE)
          message = wrongReg.sub(userInput, message)
          corrected = True
        else:
          word = userInput

  return message
if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--config", action="store_true", default=False)
  main(parser.parse_args())
