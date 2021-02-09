#!/usr/bin/env python3

from collections import namedtuple
import time
import termios
import sys
import tty
import textwrap
import subprocess
import shutil
import argparse
import os
import re
import string
import inquirer

try:
  import aspell as spellchecker
except ModuleNotFoundError:
  spellchecker = None

def main(args):

  parameters = readParameters()
  if args.config:
    dumpConfig(parameters)
    return

  if not somethingToCommit() and not args.dry:
    print("There is nothing staged to commit")
    return

  if parameters.Spellcheck == "yes" and not spellchecker:
    print("The module spellchecker is not installed")
    return

  readyToCommit = False
  title = ["", ""]
  description = ["Description", ""]
  scope = ["Scope", ""]
  issueCode = ["Issue Code", ""]
  breakingChange = ["BREAKING CHANGES", ""]
  types = []

  while not readyToCommit:

    ## Show menu with commit types
    types = showMenu(parameters, types)

    ## Ask for commit scope
    scope = getInput(scope[0],
                     length=parameters.ScopeLength+7,
                     blankChar=parameters.BlankChar,
                     inputText=scope[1])

    ## Build the title message prefix
    if parameters.TypesStyle == "comma":
      typesPrefix = ','.join(types)
    elif parameters.TypesStyle == "brackets":
      typesPrefix = ""
      for commitType in types:
        typesPrefix += "[" + commitType + "]"

    ## If scope is not empty, add it to the title prefix
    if scope[1]:
      titlePrefix = typesPrefix + "(" + scope[1] + ")"
    else:
      titlePrefix = typesPrefix

    title = getInput(prefix=titlePrefix,
                     length=parameters.MaxLength,
                     blankChar=parameters.BlankChar,
                     inputText=title[1])

    description = getInput(description[0],
                           length=sys.maxsize,
                           blankChar='',
                           inputText=description[1])

    issueCode = getInput(issueCode[0],
                         length=sys.maxsize,
                         blankChar='',
                         inputText=issueCode[1])

    breakingChange = getInput(breakingChange[0],
                              length=sys.maxsize,
                              blankChar='',
                              inputText=breakingChange[1])

    if parameters.Spellcheck == "yes":
      print("Starting spellchecking... ")
      title[1] = spellcheck(title[1], parameters)
      description[1] = spellcheck(description[1], parameters)
      breakingChange[1] = spellcheck(breakingChange[1], parameters)
      print("Spellchecking done")
      print()

    while len(title[0] + title[1]) > parameters.MaxLength:
      print("Length of corrected title is greater than maximum length allowed")
      print("Press enter to change it")
      input()
      title = getInput(prefix=title[0],
                       length=parameters.MaxLength,
                       blankChar=parameters.BlankChar,
                       inputText=title[1])
      title[1] = spellcheck(title[1], parameters)


    commitMessage = buildCommitMessage(title,
                                       description,
                                       issueCode,
                                       breakingChange,
                                       parameters)

    if parameters.ConfirmCommit == "yes":

      headerLength = max(parameters.MaxLength, parameters.WrapLength)

      print('='*headerLength)
      print("COMMIT MESSAGE")
      print('='*headerLength)

      print('\n' + commitMessage + '\n')
      print('='*headerLength)

      shouldCommit = inquirer.prompt(
        [inquirer.List('confirm',
                       message="Do you want to commit with the above message?",
                       choices=['yes', 'edit', 'cancel'],
                       default='edit'),]
      )['confirm']

      if shouldCommit == 'yes':
        readyToCommit = True
      elif shouldCommit == 'edit':
        shouldCommit == False
      else:
        return

    else:
      readyToCommit = True

  if not args.dry:
    commit(commitMessage, parameters)
  else:
    print('Dry run: Nothing was committed into repository')

  return


## ----------------------------------------------------------------------------

def somethingToCommit():
  """
  Check if there is something staged for commit in the repository

  Parameters
  ----------

  Returns
  -------
  bool
    True if there is something staged to be committed, False otherwise
  """
  return subprocess.run(['git', 'diff', '--cached', '--quiet'],
                        check=False).returncode == 1


def readParameters():
  """
  Read the parameters configuration file in current project

  This function will read the parameters file located in the root folder of the
  git project and use it to set up the commit message style.

  If not file is presented then default values are used

  Parameters
  ----------


  Returns
  -------
  namedtuple
    Structure with all the configuration parameters

  """

  parametersFile = getParametersFilename()

  defaultMenu = [('feat', "New feature"),
                 ('fix', "Bug fix"),
                 ('chore', "Build process or auxiliary tool change"),
                 ('docs', "Documentary only changes"),
                 ('refactor', "Code that neither changes or add a feature"),
                 ('style', "Markup, white-space, formatting..."),
                 ('perf', "Code change that improves performance"),
                 ('test', "Adding tests"),
                 ('release', "Release version")]
  params = {}
  params['UseDefaultMenu'] = 'yes'
  params['MaxLength'] = 70
  params['WrapLength'] = 80
  params['BlankChar'] = '_'
  params['ConfirmCommit'] = 'yes'
  params['MultipleTypes'] = 'no'
  params['TypesStyle'] = 'comma'
  params['Spellcheck'] = 'yes'
  params['SpellcheckMaxOptions'] = 10
  params['SpellcheckLanguage'] = 'English'
  params['ScopeLength'] = 20
  params['userTypes'] = []


  if os.path.isfile(parametersFile):

    paramsfid = open(parametersFile, 'r')

    for line in paramsfid:
      try:
        (key, value) = line.strip('\n').split(' ', maxsplit=1)
      except ValueError:
        key = line.strip('\n')
        value = ''


      # Try to parse to an integer. If it is not an int, then convert the
      # string to lower case
      try:
        value = int(value)
      except ValueError:
        value = value.lower()

      if key == 'AddType':
        (commitType, description) = value.split(' ', maxsplit=1)
        params['userTypes'].append((commitType, description))
      else:
        params[key] = value


  # Build commit types based on default values (if required)
  if params['UseDefaultMenu'] == 'yes':
    params['menu'] = defaultMenu
  elif params['UseDefaultMenu'] == 'no':
    params['menu'] = []
  else:
    types2keep = params['UseDefaultMenu'].split(' ')
    params['menu'] = [entry for entry in defaultMenu if entry[0] in types2keep]

  # Extend commit types with user defined types
  params['menu'].extend(params['userTypes'])

  # If negative entry for SpellcheckMaxOptions, then set to a very large number
  # this will display all the options found by the spell checker
  if params['SpellcheckMaxOptions'] < 1:
    params['SpellcheckMaxOptions'] = sys.maxsize

  tupleConstructor = namedtuple('params', ' '.join(sorted(params.keys())))

  return tupleConstructor(**params)


def showMenu(params, defaults=None):
  """

  Shows the menu checkbox list to choose the commit type

  A menu checkbox list is built and prompted from the menu attribute of the
  parameters.


  Parameters
  ----------
  params: namedtuple
    Structure with commit parameters
  defaults: list
    Value(s) to be selected by default when prompting the menu


  Returns
  -------
  list
    Choice(s) chosen by the user

  The function returns a string with the commit types separated by a comma (if
  there are multiple)

  Raises
  ------
  RuntimeError
    If nothing is chosen

  """

  # Create the text for the menu composed of label: type
  menuQuestions = [ (label + ': ' + text, label)
                    for (label, text) in params.menu ]

  if params.MultipleTypes == 'yes':
    menuType = inquirer.Checkbox
    menuMessage = "Select the type(s) of change you are committing " + \
      "(Press SPACE to select)"
  else:
    menuType = inquirer.List
    menuMessage = "\033[FSelect the type of change you are committing " + \
      "(Press ENTER to select)\r\n"
    if defaults:
      defaults = defaults[0]

  questions = [
  menuType('type',
           message=menuMessage,
           choices=menuQuestions,
           default=defaults)
  ]

  print()
  choices = inquirer.prompt(questions)['type']

  if len(choices) == 0:
    raise RuntimeError("Please choice a type")

  # if only one choice, convert it to list anyways
  if isinstance(choices, str):
    choices = [choices]

  return choices


def buildCommitMessage(title, description, issue, breaking, params):
  """
  Builds the final commit message based on all the user inputs.

  Parameters
  ----------
  title: tuple
    Tuple of strings with the prefix and the title entered by the user
  description: tuple
    Tuple of strings with the prefix and the description entered by the user
  issue: tuple
    Tuple of strings with the prefix and the issue code entered by the user
  breaking: tuple
    Tuple of strings with the prefix and the breaking changes entered by the user
  params: namedtuple
    Structure with the commit parameters

  Returns
  -------
  String
    Message to commit

  """

  message = title[0] + title[1]

  if description[1]:
    message += '\n\n' +  '\n'.join(textwrap.wrap(description[1],
                                                 width=params.WrapLength))
  if issue[1]:
    message += '\n\n' + issue[0] + ': ' + issue[1]

  if breaking[1]:
    message += '\n\n' + breaking[0] + ': ' + breaking[1]

  return message


def getChar():
  """

  Reads a character typed in the keyboard

  This function read a single character pressed by the user and returns it


  Parameters
  ----------

  Returns
  -------
  str
    The character typed by the user

  """

  fileDescriptor = sys.stdin.fileno()
  oldSettings = termios.tcgetattr(fileDescriptor)
  try:
    tty.setraw(fileDescriptor)
    char = sys.stdin.read(1)
  finally:
    termios.tcsetattr(fileDescriptor, termios.TCSADRAIN, oldSettings)
  return char


def getInput(prefix='', length=80, blankChar='_', inputText=''):
  """
  Builds an input system that checks that the length of the input is smaller
  than some value.

  This function shows the user a prompt line where he/she can type a message,
  but imposing a maximum number of characters. The message is composed of one
  non-editable string (prefix + ': ') and one editable part where the user
  writes the input. The sum of the length of both string restricted to be less
  or equal than the parameter 'length'

  Also as the user writes, the inputs get wrapped in multiple lines (if the
  input is too long) according to the terminal's size


  Parameters:
  -----------
  prefix: str, optional
    The non-editable prefix of the user message (Default='')
  length: int, optional
    The maximum total length of the input string (Default=80)
  blankChar: str, optional
    Character to be used as a placeholder for the empty characters in the message (Default='_')
  inputText: str, optional
    Predefined text to be used in the editable section of the user prompt (Default='')

  Returns
  -------
  tuple
    A tuple of 2 strings:
      1. The non editable part (prefix + ': ')
      2. The editable part typed by the user
    The length of the string is equal or less than 'length' parameter

  Raises
  ------
  KeyboardInterrupt signal if the user press ctrl+c

  """

  ## TODO Set to global variable
  backline='\033[F'

  prefix += ': '
  lenPrefix = len(prefix)

  cursorPos = lenPrefix

  userInput = inputText[:(length-len(prefix))]
  cursorPos += len(userInput)

  messageLine = prefix + userInput + (length - len(userInput) - lenPrefix) * blankChar
  maxLengthMessage = len(messageLine)

  (nlines, cursorLine) = printMessageWrapped(messageLine, cursorPos)

  escapeNext = 0

  while True:

    char = str(getChar())

    ## If the arrow key are pressed they produced first a escape sequence and
    ## then the arrow key code, so this handles that
    if escapeNext > 0:
      escapeNext -= 1
      if ord(char) == 68 and (cursorPos > lenPrefix):
        cursorPos -= 1
      elif (ord(char) == 67) and (cursorPos < lenPrefix + len(userInput)):
        cursorPos +=1
      else:
        continue
    elif ord(char) == 127: ## 127 = backspace -> erase character
      # Remove character if backspace

      cursorPosWord = cursorPos - lenPrefix

      if cursorPosWord > 0:
        userInput = userInput[:(cursorPosWord-1)] + userInput[(cursorPosWord):]
        cursorPos -= 1

    elif ord(char) == 13: ## 13: enter. Input finished
      break
    elif ord(char) == 27: ## 27: first character sent when arrow key pressed
      escapeNext = 2
    elif ord(char) == 3: ## Ctrl+c pressed -> interrupt
      raise KeyboardInterrupt
    elif len(userInput) + lenPrefix == length: ## If already at the end, don't do anything
      continue
    elif ord(char) >= 32: #Write only letters numbers and symbols
      cursorPosWord = cursorPos - lenPrefix
      userInput = userInput[:cursorPosWord] + char + userInput[cursorPosWord:]
      cursorPos += 1

    # Bring back cursor to the very beginning of the input line
    print('\r', end='')
    print(backline*cursorLine, end='')

    messageLine = prefix + userInput + (length - len(userInput) - lenPrefix) * blankChar

    # Clean any old input before writing new line
    if len(messageLine) > maxLengthMessage:
      maxLengthMessage = len(messageLine)
    printMessageWrapped(' '*maxLengthMessage, 0)

    # Print the user input in a formatted way
    (nlines, cursorLine) = printMessageWrapped(messageLine, cursorPos)

  # Print enough new line so the new input does not overlap with this input
  print('\n'*(nlines - cursorLine), flush=True)
  return [prefix, userInput]


def printMessageWrapped(message, cursorPos):
  """
  Print a wrapped string in the terminal and sets the cursor to a specific
  location

  The function gets the size of the current terminal and breaks the string
  into several lines and then prints those lines. Also the cursor is placed in
  a specific location using the parameters cursorPos

  Parameters
  ----------
  message: str
    The message to be printed on the console
  cursorPos: int
    The position where the cursor should be placed. The beginning of the string
    is 0

  Returns
  -------
  tuple
    Tuple with the total number of lines and the line of the current cursor position

  """

  terminalSize = shutil.get_terminal_size()
  margin = 5
  cols = terminalSize.columns - margin

  # Special character to move the cursor up one line
  backline = '\033[F'

  nlines = len(message) // cols + 1
  cursorLine = cursorPos // cols
  cursorPosLine = cursorPos % cols

  # Break the message into lines
  lines = [message[idx*cols:(idx+1)*cols] for idx in range(nlines)]

  # First print the entire message
  print('\n'.join(lines), end='')

  #bring back cursor to the beginning of message
  print('\r' + backline*(nlines-1), end='')

  # Print all lines coming before cursor (if there are any)
  if cursorLine > 0:
    print('\n'.join(lines[:cursorLine]), end='\n', flush=True)

  #print until cursor
  print(lines[cursorLine][:cursorPosLine], end='', flush=True)

  return (nlines, cursorLine)


def commit(message, params):
  """
  Runs git to commit staged files with a given message

  Parameters
  ----------
  message: str
    Commit message already formatted
  params: namedtuple
    Structure with the commit parameters

  Returns
  -------
  None

  """

  subprocess.run(['git', 'commit', '--message', message], check=True)


def dumpConfig(params):
  """
  Create a configuration file with given parameters

  Parameters
  ----------
  params: namedtuple
    Structure with the commit parameters

  Returns
  -------
  None

  """

  parametersFile = getParametersFilename()

  if not os.path.isfile(parametersFile):
    with open(parametersFile, 'w+') as fid:
      for (key, value) in params._asdict().items():
        if key != 'menu':
          print(key + ' ' + str(value), file=fid)
  else:
    print("Configuration file already exists")


def spellcheck(message, params):
  """
  Spell check a given string.

  A simple list is shown to the user and asked to selected a corrected word, or
  keep the original.

  Parameters
  ----------
  message: str
    The string to be checked
  params: namedtuple
    Structure with the commit parameters

  Returns
  -------
  str
    The corrected message

  """

  langDict = {
    'english': 'en',
    'spanish': 'es',
    'deutch': 'de',
    'french': 'fr',
    'portuguese': 'pt'
  }

  #spell = spellchecker.SpellChecker(language=langDict[params.SpellcheckLanguage.lower()])
  spell = spellchecker.Speller('lang', langDict[params.SpellcheckLanguage.lower()])

  ## Remove punctuation from text
  noPunctuation = message.translate(str.maketrans('', '', string.punctuation))

  ## Remove any empty string that might appear in the list
  #wrongWords = list(spell.unknown(noPunctuation.split(' ')))
  wrongWords = [w for w in noPunctuation.split(' ') if w not in spell]
  print(wrongWords)

  for word in wrongWords:

    corrected = False
    userInput = ""
    userWord = ""
    originalWord = word

    while not corrected:

      print("-> Word not found in dictionary: " + word)
      print("Possible candidates are: ")

      listCandidates = list(spell.suggest(word))
      listCandidates = listCandidates[:params.SpellcheckMaxOptions]
      listCandidates = [candidate for candidate in listCandidates if candidate != word]

      if userInput:
        userWord = userInput
        listCandidates = [userWord] + listCandidates

      for idx, candidate in enumerate(listCandidates):
        print('\t' + str(idx+1) + ': ' + candidate, end='')
        if userWord and idx == 0:
          print(" (your last input)",end='')
        print()

      if len(listCandidates) == 0:
        print("\tNo suitable option was found")

      print()
      userInput = input("Select word or write a different word \n" + \
                        "(type -1 to keep the original word: " + originalWord + ")\n-> ")

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
        if spell.check(userInput):
          wrongReg = re.compile(re.escape(originalWord), re.IGNORECASE)
          message = wrongReg.sub(userInput, message)
          corrected = True
        else:
          newCandidates = spell.suggest(userInput)
          word = userInput.rstrip('\n')

  return message


def getParametersFilename():
  """
  Returns the full path filename for the parameters file

  Returns
  -------
  str
    Full parameters file path

  """
  basename = '.gitmess'
  rootDirectory = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                                 capture_output=True, check=True
                                ).stdout.decode('utf-8').rstrip('\n')

  return rootDirectory + '/' + basename


## Main
if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--config', action='store_true', default=False)
  parser.add_argument('--dry', action='store_true', default=False)
  main(parser.parse_args())
