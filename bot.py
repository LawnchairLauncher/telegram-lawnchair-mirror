#!/usr/bin/python3
import os
import sys
import shutil
import fnmatch
import telebot
import logging
import requests
import traceback
import configparser

from hashlib import md5

def loadConfig():
    '''
    Function that creates a configparser object and tries to load the config
    '''
    try:
        global config
        config = configparser.ConfigParser()
        config.read('config.cfg')
        print('Configuration file succesfully loaded!')
    except Exception as e:
        print('Error while reading config file!')
        traceback.print_exc()
        sys.exit(1)
    return config

def checkDirs():
    '''
    Function that creates all directories specified in the 'directories' section in the config file
    '''
    for key in config['directories']:
        os.makedirs(os.path.dirname(config['directories'][key]), exist_ok=True)

    print('Directories are ok!')

def setupLogging():
    '''
    Function that sets up the logging object along with everything we want it to do (ie. log to a logfile)
    '''
    logDir = config.get('directories', 'LOG_DIR')
    logName = config.get('logging', 'FILE_NAME')
    logLevel = config.get('logging', 'LEVEL')
    numericLevel = getattr(logging, logLevel.upper(), None)
    logLocation = logDir + logName
    if not isinstance(numericLevel, int):
        raise ValueError('Invalid log level: {0}'.format(logLevel))
    logging.basicConfig(filename=logLocation, level=numericLevel, format='[%(asctime)s][%(levelname)s] %(message)s')
    print('Logs will be written to: {0}'.format(logLocation))

def setupBot(config):
    '''
    Function that creates and returns the telebot object
    '''
    token = config.get('telegram', 'API_KEY')
    return telebot.TeleBot(token)

class Document(object):
    def __init__(self, message):
        self.message = message

        self.validFile = False
        self.processFunction = None
        self.projectFolderName = None

        self.fileVersion = None
        self.fileBranch = None
        self.fileLocation = None
        self.fileName = message.document.file_name
        self.fileExt = os.path.splitext(message.document.file_name)[-1]
        self.buildDirectory = None
        self.latestDirectory = None

        self.token = config.get('telegram', 'API_KEY')
        self.downloadDir = config.get('directories', 'DOWNLOAD_DIR')
        self.fileInfo = bot.get_file(message.document.file_id)

    def _lawnchairBuildNameProcessor(self):
        '''
        Function that parses the name of a Lawnchair build and returns the branch + version number
        '''

        logging.debug('Processing Lawnchair build file name')

        fileName = self.fileName

        fileName = fileName[10:] # Strip "Lawnchair-" from filename
        fileName = fileName[:-4] # Strip ".apk" from filename
        fileNameSplit = fileName.split('_')

        self.fileVersion = fileNameSplit[-1] # Prints the last element in fileNameSplit
        self.fileBranch = '_'.join(i for i in fileNameSplit[:-1]) # Joins together all elements in fileNameSplit, except the last element (which is the version)

    def _lawnstepBuildNameProcessor(self):
        '''
        Function that parses the name of a Lawnstep build and returns the version number
        '''

        logging.debug('Processing Lawnstep build file name')

        fileName = self.fileName

        fileName = fileName[9:] # Strip "Lawnstep-" from filename
        fileName = fileName[:-4] # Strip ".zip" from filename

        self.fileVersion = fileName
        self.fileBranch = 'PLACEHOLDER'

    def _checkFile(self):
        '''
        Function that checks if the sent file is supported
        '''
        logging.debug('Checking file against supported files')

        supportedFiles = {
            'Lawnchair-*.apk': {
                'mime_type': 'application/vnd.android.package-archive',
                'folder_name': 'lawnchair',
                'process_function': self._lawnchairBuildNameProcessor
            },
            'Lawnstep-*.zip': {
                'mime_type': 'application/zip',
                'folder_name': 'lawnstep',
                'process_function': self._lawnstepBuildNameProcessor
            }
        }

        for sFile in supportedFiles:
            if fnmatch.fnmatch(self.message.document.file_name, sFile):
                self.validFile = True
                self.processFunction = supportedFiles[sFile]['process_function']
                self.projectFolderName = supportedFiles[sFile]['folder_name']
                break

    def _createDirectories(self):
        '''
        Function that creates the correct directories for a build
        '''
        logging.debug('Creating directories for new build')

        # Create build-specific directory
        self.buildDirectory = '{}/{}/{}/'.format(self.downloadDir, self.projectFolderName, self.fileVersion)
        os.makedirs(os.path.dirname(self.buildDirectory), exist_ok=True)

        # Create 'latest' directory for project
        self.latestDirectory = '{}/{}/latest/'.format(self.downloadDir, self.projectFolderName)
        os.makedirs(os.path.dirname(self.latestDirectory), exist_ok=True)

    def _downloadBuild(self):
        '''
        Function that downloads a build
        '''
        logging.debug('Downloading build')

        URL = 'https://api.telegram.org/file/bot{0}/{1}'.format(self.token, self.fileInfo.file_path)
        self.fileLocation = '{}{}/{}/{}'.format(self.downloadDir, self.projectFolderName, self.fileVersion, self.fileName)
        try:
            response = requests.get(URL, stream=True)
            with open(self.fileLocation, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            del response
            return True
        except Exception:
            logging.error('Unable to download file from Telegram!')
            traceback.print_exc()
            return False

    def _hashBuild(self):
        '''
        Function that hashes a build
        '''
        logging.debug('Creating checksum of build')

        hash = md5()

        self.sumLocation = self.buildDirectory + 'MD5SUM'
        try:
            with open(self.fileLocation, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash.update(chunk)
            with open(self.sumLocation, 'wt') as f:
                f.write(hash.hexdigest())
        except Exception as e:
            logging.critical('The following error has occured while creating the MD5sum: ' + str(e))

    def _symlink(self):
        '''
        Function that symlinks the build and MD5SUM file to the 'latest' directory
        '''
        logging.debug('Creating symlinks for files')

        # Create symlink for the file itself
        fileSymlink = '{}{}'.format(self.latestDirectory, 'latest' + self.fileExt)
        try:
            os.symlink(self.fileLocation, fileSymlink)
        except FileExistsError:
            os.unlink(fileSymlink)
            os.symlink(self.fileLocation, fileSymlink)

        # Create symlink for the MD5SUM
        md5sumSymlink = '{}MD5SUM'.format(self.latestDirectory)
        try:
            os.symlink(self.sumLocation, md5sumSymlink)
        except FileExistsError:
            os.unlink(md5sumSymlink)
            os.symlink(self.sumLocation, md5sumSymlink)

    def processFile(self):
        '''
        Function that kicks off all other functions contained within the class
        '''
        logging.info('New build was sent to the channel')
        logging.info('File information:')
        logging.info('Date: {0}'.format(self.message.date))
        logging.info('File name: {0}'.format(self.message.document.file_name))
        logging.info('File size: {0}'.format(self.message.document.file_size))
        logging.info('Mime type: {0}'.format(self.message.document.mime_type))
        logging.info('File id: {0}'.format(self.message.document.file_id))

        self._checkFile()

        if self.validFile:
            self.processFunction()
            self._createDirectories()
            self._downloadBuild()
            self._hashBuild()
            self._symlink()
            return True
        else:
            return False

class Changelog(object):
    def __init__(self, message):
        self.changelog = message.text

        self.validChangelog = False

        self.projectFolderName = None

        self.changelogVersion = None
        self.changelogBranch = None
        self.changelogLocation = None
        self.buildDirectory = None
        self.latestDirectory = None

        self.downloadDir = config.get('directories', 'DOWNLOAD_DIR')

        self.metadata = None

    def _lawnchairChangelogProcessor(self):
        '''
        Function that parses the changelog of a Lawnchair build and returns the branch + version number
        '''

        logging.debug('Processing Lawnchair build changelog')

        branch = self.metadata.split('-')[0]
        version = self.metadata.split('-')[1][:-1] # select the second element of the list and remove the last character of said element

        self.changelogVersion = version
        self.changelogBranch = branch

    def _lawnstepChangelogProcessor(self):
        '''
        Function that parses the changelog of a Lawnstep build and returns the version number
        '''

        logging.debug('Processing Lawnstep build changelog')

        version = self.metadata.split('-')[1]

        self.changelogVersion = version
        self.changelogBranch = 'PLACEHOLDER'

    def _checkChangelog(self):
        '''
        Function that checks the changelog and starts the appropriate processor
        '''

        # Get the first line of the changelog, which contains the metadata we need
        firstLine = self.changelog.split('\n')[0].lower()

        # Extract the data we're going to process
        self.metadata = firstLine.split()[-1]

        # Ugly workaround for the fact that Lawnstep is the only project that includes the project 
        # name in the initial line of the changelog (or this just isn't the ideal way, whatever).
        # With this we assume that if 'lawnstep' is in the first line, the changelog is meant for Lawnstep
        # if not, it's meant for Lawnchair. This is ugly. :)
        try:
            if 'lawnstep' in firstLine:
                self.projectFolderName = 'lawnstep'
                self._lawnstepChangelogProcessor()
            else:
                self.projectFolderName = 'lawnchair'
                self._lawnchairChangelogProcessor()
            self.validChangelog = True
        except Exception:
            logging.error('Unable to process changelog, has the format changed?')
            traceback.print_exc()
            self.validChangelog = False

    def _createDirectories(self):
        '''
        Function that creates the correct directories for a changelog
        '''
        logging.debug('Creating directories for new build')

        # Create build-specific directory
        self.buildDirectory = '{}/{}/{}/'.format(self.downloadDir, self.projectFolderName, self.changelogVersion)
        os.makedirs(os.path.dirname(self.buildDirectory), exist_ok=True)

        # Create 'latest' directory for project
        self.latestDirectory = '{}/{}/latest/'.format(self.downloadDir, self.projectFolderName)
        os.makedirs(os.path.dirname(self.latestDirectory), exist_ok=True)

    def _saveChangelog(self):
        '''
        Function that saves the changelog
        '''
        self.changelogLocation = self.buildDirectory + 'CHANGELOG'

        try:
            with open(self.changelogLocation, 'wt') as f:
                f.write(self.changelog)
        except Exception:
            logging.error('Unable to write changelog!')
            traceback.print_exc()

    def _symlink(self):
        '''
        Function that symlinks the changelog to the 'latest' directory
        '''
        logging.debug('Creating symlinks for changelog')

        changelogSymlink = '{}CHANGELOG'.format(self.latestDirectory)

        try:
            os.symlink(self.changelogLocation, changelogSymlink)
        except FileExistsError:
            os.unlink(changelogSymlink)
            os.symlink(self.changelogLocation, changelogSymlink)

    def processChangelog(self):
        '''
        Function that kicks off all other functions contained within the class
        '''
        logging.info('New changelog was sent to the channel')

        self._checkChangelog()

        if self.validChangelog:
            self._createDirectories()
            self._saveChangelog()
            self._symlink()
            return True
        else:
            return False

def setup():
    '''
    Function that contains all functions required to 'setup' the bot
    '''
    loadConfig()
    checkDirs()
    setupLogging()

setup()
bot = setupBot(config)

@bot.channel_post_handler(content_types=['document'])
def handleDocuments(message):
    allowedChannels = config.get('telegram', 'ALLOWED_CHANNELS')
    if str(message.chat.id) not in allowedChannels:
        logging.warning('Channel ID refused: {0}'.format(str(message.chat.id)))
        return
    if message.document:
        document = Document(message)
        if document.processFile():
            logging.info('New build succesfully downloaded and hashed!')
        else:
            logging.critical('Failed to process build!')

@bot.channel_post_handler(content_types=['text'])
def handleChangelogs(message):
    allowedChannels = config.get('telegram', 'ALLOWED_CHANNELS')
    if str(message.chat.id) not in allowedChannels:
        logging.warning('Channel ID refused: {0}'.format(str(message.chat.id)))
        return
    if message.text.startswith('Changelog'):
        changelog = Changelog(message)

        if changelog.processChangelog():
            logging.info('New build\'s changelog saved!')
        else:
            logging.critical('Failed to obtain changelog from message!')

logging.info('Started polling!')
bot.polling(none_stop=True, interval=1)
