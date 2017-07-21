#!/usr/bin/python3
import os
import shutil
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
        sys.exit(0)
    return config

def checkDirs():
    '''
    Function that creates all directories specified in the 'directories' section in the config file
    '''
    for key in config['directories']:
        os.makedirs(os.path.dirname(config['directories'][key]), exist_ok=True)

    # Create 'latest' directory in the download dir
    os.makedirs(os.path.dirname(config['directories']['DOWNLOAD_DIR'] + 'latest/'), exist_ok=True)

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

def downloadBuild(message):
    '''
    Function that will download the Lawnchair builds that are sent to the channel
    '''
    logging.info('Downloading new build!')
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
    build_number = message.document.file_name.split('-')[1][:-4]

    # Create build-specific directory
    os.makedirs(os.path.dirname(download_dir + build_number + '/'), exist_ok=True)

    URL = 'https://api.telegram.org/file/bot{0}/{1}'.format(token, file_info.file_path)
    location = download_dir + build_number + '/' + message.document.file_name
    try:
        response = requests.get(URL, stream=True)
        with open(location, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        del response

        # Create symlink to 'latest' directory
        try:
            os.symlink(location, download_dir + 'latest/lawnchair-latest.apk')
        except FileExistsError:
            os.unlink(download_dir + 'latest/lawnchair-latest.apk')
            os.symlink(location, download_dir + 'latest/lawnchair-latest.apk')
        return 1
    except Exception as e:
        logging.critical('The following error has occured while downloading a file: ' + str(e))
        del response
        return 0

def hashBuild(message):
    hash = md5()
    download_dir = config.get('directories', 'DOWNLOAD_DIR')

    # Get the buildnumber from the filename
    build_number = message.document.file_name.split('-')[1][:-4]

    location = download_dir + build_number + '/' + message.document.file_name
    sum_location = download_dir + build_number + '/MD5SUM'
    try:
        with open(location, 'rb') as f:
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
        build_number = first_line.split(' ')[-1][1:]
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
def handleBuilds(message):
    allowed_channels = config.get('telegram', 'ALLOWED_CHANNELS')
    if str(message.chat.id) not in allowed_channels:
        logging.warning('Channel ID refused: {0}'.format(str(message.chat.id)))
        return
    if message.document:
        if downloadBuild(message):
            if hashBuild(message):
                logging.info('New build succesfully downloaded and hashed!')
            else:
                logging.critical('Failed to create hash!')
        else:
            logging.critical('Failed to download build!')

@bot.channel_post_handler(content_types=['text'])
def handleChangelog(message):
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
