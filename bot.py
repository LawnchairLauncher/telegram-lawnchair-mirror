#!/usr/bin/python3
import os
import sys
import shutil
import fnmatch
import telebot
import logging
import requests
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
        print(e)
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

# def downloadManager(message):
#     '''
#     Function that will download the supported files that are sent to the channel
#     '''

#     logging.info('File sent to Lawnchair channel')

#     if not validFile:
#         logging.info('Unsupported file sent in channel:')
#         logging.info('Date: {0}'.format(message.date))
#         logging.info('File name: {0}'.format(message.document.file_name))
#         logging.info('File size: {0}'.format(message.document.file_size))
#         logging.info('Mime type: {0}'.format(message.document.mime_type))
#         logging.info('File id: {0}'.format(message.document.file_id))
#         return 0

#     logging.info('File information:')
#     logging.info('Date: {0}'.format(message.date))
#     logging.info('File name: {0}'.format(message.document.file_name))
#     logging.info('File size: {0}'.format(message.document.file_size))
#     logging.info('Mime type: {0}'.format(message.document.mime_type))
#     logging.info('File id: {0}'.format(message.document.file_id))
#     token = config.get('telegram', 'API_KEY')
#     download_dir = config.get('directories', 'DOWNLOAD_DIR')
#     file_info = bot.get_file(message.document.file_id)

#     # Get the buildnumber from the filename
#     processedFileName = processFunction(message.document.file_name)

#     URL = 'https://api.telegram.org/file/bot{0}/{1}'.format(token, file_info.file_path)
#     location = '{}{}/{}/{}'.format(download_dir, projectFolderName, build_number, message.document.file_name)
#     try:
#         response = requests.get(URL, stream=True)
#         with open(location, 'wb') as f:
#             response.raw.decode_content = True
#             shutil.copyfileobj(response.raw, f)
#         del response

#         # Create symlink to 'latest' directory
#         latest_location = '{}{}/latest/{}'.format(download_dir, projectFolderName, message.document.file_name)
#         try:
#             os.symlink(location, latest_location)
#         except FileExistsError:
#             os.unlink(latest_location)
#             os.symlink(location, latest_location)
#         return 1
#         return {'status': 1, 'path': None, 'filename': None}
#     except Exception as e:
#         logging.critical('The following error has occured while downloading a file: ' + str(e))
#         del response
#         return 0
#         return {'status': 0, 'path': build_directory, 'filename': message.document.file_name}

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

        logging.debug('Checking file against supported files')

        supported_files = {
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

        for sFile in supported_files:
            if fnmatch.fnmatch(self.message.document.file_name, sFile):
                self.validFile = True
                self.processFunction = supported_files[sFile]['process_function']
                self.projectFolderName = supported_files[sFile]['folder_name']
                break

    def _createDirectories(self):

        logging.debug('Creating directories for new build')

        # Create build-specific directory
        self.buildDirectory = '{}/{}/{}/'.format(self.downloadDir, self.projectFolderName, self.fileVersion)
        os.makedirs(os.path.dirname(self.buildDirectory), exist_ok=True)

        # Create 'latest' directory for project
        self.latestDirectory = '{}/{}/latest/'.format(self.downloadDir, self.projectFolderName)
        os.makedirs(os.path.dirname(self.latestDirectory), exist_ok=True)

    def _downloadBuild(self):

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
            # TODO: do this properly
            print('oh noes')
            return False

    def _hashBuild(self):

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
        pass

    def _createDirectories(self):

        logging.debug('Creating directories for new build')

        # Create build-specific directory
        self.buildDirectory = '{}/{}/{}/'.format(self.downloadDir, self.projectFolderName, self.fileVersion)
        os.makedirs(os.path.dirname(self.buildDirectory), exist_ok=True)

        # Create 'latest' directory for project
        self.latestDirectory = '{}/{}/latest/'.format(self.downloadDir, self.projectFolderName)
        os.makedirs(os.path.dirname(self.latestDirectory), exist_ok=True)

    def changelogBuild(self, message):
        download_dir = config.get('directories', 'DOWNLOAD_DIR')
        first_line = message.text.split('\n', 1)[0]
        try:
            build_number = first_line.split(' ')[-1]
        except Exception as e:
            logging.critical('It seems like this is not a proper changelog message! The following error occured: ' + str(e))
            return 0

        changelog_location = download_dir + build_number + '/CHANGELOG'

        try:
            with open(changelog_location, 'wt') as f:
                f.write(message.text)

            # Create symlink to 'latest' directory
            try:
                os.symlink(changelog_location, download_dir + 'latest/CHANGELOG')
            except FileExistsError:
                os.unlink(download_dir + 'latest/CHANGELOG')
                os.symlink(changelog_location, download_dir + 'latest/CHANGELOG')
            return 1
        except Exception as e:
            logging.critical('The following error has occured while saving the changelog: ' + str(e))
            return 0

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
    allowed_channels = config.get('telegram', 'ALLOWED_CHANNELS')
    if str(message.chat.id) not in allowed_channels:
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
    allowed_channels = config.get('telegram', 'ALLOWED_CHANNELS')
    if str(message.chat.id) not in allowed_channels:
        logging.warning('Channel ID refused: {0}'.format(str(message.chat.id)))
        return
    if message.text.startswith('Changelog'):
        changelog = Changelog(message)

        # if changelogBuild(message):
        #     logging.info('New build\'s changelog saved!')
        # else:
        #     logging.critical('Failed to obtain changelog from message!')

logging.info('Started polling!')
bot.polling(none_stop=True, interval=1)
