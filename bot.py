#!/bin/python3
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

    URL = 'https://api.telegram.org/file/bot{0}/{1}'.format(token, file_info.file_path)
    location = download_dir + message.document.file_name
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
    location = download_dir + message.document.file_name
    sum_location = download_dir + message.document.file_name + '.md5'
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

def setup():
    '''
    Function that contains all functions required to 'setup' the bot
    '''
    loadConfig()
    checkDirs()

setup()
bot = setupBot(config)

@bot.channel_post_handler(content_types=['document'])
def handleMessages(message):
    if message.document:
        if downloadBuild(message):
            if hashBuild(message):
                print('New build succesfully downloaded and hashed!')
            else:
                print('Failed to create hash!')
        else:
            print('Failed to download build!')

print('Started polling!')
bot.polling(none_stop=True, interval=1)
