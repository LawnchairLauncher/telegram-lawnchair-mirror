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

def _lawnchairBuildNameProcessor(fileName):
    '''
    Function that parses the name of a Lawnchair build and returns the branch + version number
    '''
    fileName = fileName[10:] # Strip "Lawnchair-" from filename
    fileName = fileName[:-4] # Strip ".apk" from filename
    fileNameSplit = fileName.split('_')

    version = fileNameSplit[-1] # Prints the last element in fileNameSplit
    branch = '_'.join(i for i in fileNameSplit[:-1]) # Joins together all elements in fileNameSplit, except the last element (which is the version)

    return {'branch': branch, 'version': version}

def _lawnstepBuildNameProcessor(fileName):
    '''
    Function that parses the name of a Lawnstep build and returns the version number
    '''
    fileName = fileName[9:] # Strip "Lawnstep-" from filename
    fileName = fileName[:-4] # Strip ".zip" from filename

    version = fileName
    branch = 'PLACEHOLDER'

    return {'branch': branch, 'version': version}

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
    log_dir = config.get('directories', 'LOG_DIR')
    log_name = config.get('logging', 'FILE_NAME')
    log_level = config.get('logging', 'LEVEL')
    numeric_level = getattr(logging, log_level.upper(), None)
    log_location = log_dir + log_name
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: {0}'.format(log_level))
    logging.basicConfig(filename=log_location, level=numeric_level, format='[%(asctime)s][%(levelname)s] %(message)s')
    print('Logs will be written to: {0}'.format(log_location))

def setupBot(config):
    '''
    Function that creates and returns the telebot object
    '''
    token = config.get('telegram', 'API_KEY')
    return telebot.TeleBot(token)

def downloadManager(message):
    '''
    Function that will download the supported files that are sent to the channel
    '''

    validFile = False
    processFunction = None
    projectFolderName = None

    # Dictionary containing the filenames + mime types we support
    supported_files = {
        'Lawnchair-*.apk': {
            'mime_type': 'application/vnd.android.package-archive',
            'folder_name': 'lawnchair',
            'process_function': _lawnchairBuildNameProcessor
        },
        'Lawnstep-*.zip': {
            'mime_type': 'application/zip',
            'folder_name': 'lawnstep',
            'process_function': _lawnstepBuildNameProcessor
        } 
    }

    logging.info('File sent to Lawnchair channel')

    for sFile in supported_files:
        if fnmatch.fnmatch(message.document.file_name, sFile):
            validFile = True
            processFunction = supported_files[sFile]['process_function']
            projectFolderName = supported_files[sFile]['folder_name']
            break

    if not validFile:
        logging.info('Unsupported file sent in channel:')
        logging.info('Date: {0}'.format(message.date))
        logging.info('File name: {0}'.format(message.document.file_name))
        logging.info('File size: {0}'.format(message.document.file_size))
        logging.info('Mime type: {0}'.format(message.document.mime_type))
        logging.info('File id: {0}'.format(message.document.file_id))
        return 0

    logging.info('File information:')
    logging.info('Date: {0}'.format(message.date))
    logging.info('File name: {0}'.format(message.document.file_name))
    logging.info('File size: {0}'.format(message.document.file_size))
    logging.info('Mime type: {0}'.format(message.document.mime_type))
    logging.info('File id: {0}'.format(message.document.file_id))
    token = config.get('telegram', 'API_KEY')
    download_dir = config.get('directories', 'DOWNLOAD_DIR')
    file_info = bot.get_file(message.document.file_id)

    # Get the buildnumber from the filename
    processedFileName = processFunction(message.document.file_name)

    build_number = processedFileName['version']

    # Create build-specific directory
    build_directory = '{}/{}/{}/'.format(download_dir, projectFolderName, build_number)
    os.makedirs(os.path.dirname(build_directory), exist_ok=True)

    # Create 'latest' directory for project
    latest_directory = '{}/{}/latest/'.format(download_dir, projectFolderName)
    os.makedirs(os.path.dirname(latest_directory), exist_ok=True)

    URL = 'https://api.telegram.org/file/bot{0}/{1}'.format(token, file_info.file_path)
    location = '{}{}/{}/{}'.format(download_dir, projectFolderName, build_number, message.document.file_name)
    try:
        response = requests.get(URL, stream=True)
        with open(location, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        del response

        # Create symlink to 'latest' directory
        latest_location = '{}{}/latest/{}'.format(download_dir, projectFolderName, message.document.file_name)
        try:
            os.symlink(location, latest_location)
        except FileExistsError:
            os.unlink(latest_location)
            os.symlink(location, latest_location)
        return 1
        return {'status': 1, 'path': None, 'filename': None}
    except Exception as e:
        logging.critical('The following error has occured while downloading a file: ' + str(e))
        del response
        return 0
        return {'status': 0, 'path': build_directory, 'filename': message.document.file_name}

def hashBuild(path, filename):
    hash = md5()

    file_location = path + filename
    sum_location = path + 'MD5SUM'
    try:
        with open(file_location, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash.update(chunk)
        with open(sum_location, 'wt') as f:
            f.write(hash.hexdigest())

        # Create symlink to 'latest' directory
        try:
            os.symlink(sum_location, download_dir + 'latest/MD5SUM')
        except FileExistsError:
            os.unlink(download_dir + 'latest/MD5SUM')
            os.symlink(sum_location, download_dir + 'latest/MD5SUM')
        return 1
    except Exception as e:
        logging.critical('The following error has occured while creating the MD5sum: ' + str(e))
        return 0

def changelogBuild(message):
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
        if downloadManager(message):
            if hashBuild(message):
                logging.info('New build succesfully downloaded and hashed!')
            else:
                logging.critical('Failed to create hash!')
        else:
            logging.critical('Failed to download build!')

@bot.channel_post_handler(content_types=['text'])
def handleChangelogs(message):
    allowed_channels = config.get('telegram', 'ALLOWED_CHANNELS')
    if str(message.chat.id) not in allowed_channels:
        logging.warning('Channel ID refused: {0}'.format(str(message.chat.id)))
        return
    if message.text.startswith('Changelog'):
        if changelogBuild(message):
            logging.info('New build\'s changelog saved!')
        else:
            logging.critical('Failed to obtain changelog from message!')

logging.info('Started polling!')
bot.polling(none_stop=True, interval=1)
