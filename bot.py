#!/usr/bin/python3
import os
import shutil
import telebot
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
    print('Downloading new build!')
    print('File information:')
    print('Date: {0}'.format(message.date))
    print('File name: {0}'.format(message.document.file_name))
    print('File size: {0}'.format(message.document.file_size))
    print('Mime type: {0}'.format(message.document.mime_type))
    print('File id: {0}'.format(message.document.file_id))
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
        return 1
    except Exception as e:
        print('The following error has occured while downloading a file: ' + str(e))
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
        return 1
    except Exception as e:
        print('The following error has occured while creating the MD5sum: ' + str(e))
        return 0

def changelogBuild(message):
    download_dir = config.get('directories', 'DOWNLOAD_DIR')
    first_line = message.text.split('\n', 1)[0]
    try:
        build_number = first_line.split(' ')[-1][1:]
    except Exception as e:
        print('It seems like this is not a proper changelog message! The following error occured: ' + str(e))
        return 0

    changelog_location = download_dir + build_number + '/CHANGELOG'

    try:
        with open(changelog_location, 'wt') as f:
            f.write(message.text)
        return 1
    except Exception as e:
        print('The following error has occured while saving the changelog: ' + str(e))
        return 0

def setup():
    '''
    Function that contains all functions required to 'setup' the bot
    '''
    loadConfig()
    checkDirs()

setup()
bot = setupBot(config)

@bot.channel_post_handler(content_types=['document'])
def handleBuilds(message):
    allowed_channels = config.get('telegram', 'ALLOWED_CHANNELS')
    if str(message.chat.id) not in allowed_channels:
        print('Channel ID refused: {0}'.format(str(message.chat.id)))
        return
    if message.document:
        if downloadBuild(message):
            if hashBuild(message):
                print('New build succesfully downloaded and hashed!')
            else:
                print('Failed to create hash!')
        else:
            print('Failed to download build!')

@bot.channel_post_handler(content_types=['text'])
def handleChangelog(message):
    allowed_channels = config.get('telegram', 'ALLOWED_CHANNELS')
    if str(message.chat.id) not in allowed_channels:
        print('Channel ID refused: {0}'.format(str(message.chat.id)))
        return
    if message.text.startswith('Changelog'):
        if changelogBuild(message):
            print('New build\'s changelog saved!')
        else:
            print('Failed to obtain changelog from message!')

print('Started polling!')
bot.polling(none_stop=True, interval=1)
