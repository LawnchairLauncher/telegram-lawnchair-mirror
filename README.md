# Telegram Lawnchair Mirror

## .. But why?
![but_why](img/but_why.gif)  
[Lawnchair](https://lawnchair.deletescape.ch/)'s main community is located on Telegram, discussions happen, stable builds get posted, Travis CI builds get posted etc. Besides Telegram though, Lawnchair also has a [thread](https://forum.xda-developers.com/android/apps-games/lawnchair-customizable-pixel-launcher-t3627137) on XDA-Developers. And as it turns out, some people don't use Telegram and don't want to use it either, which is fine. They're missing out on the Travis CI builds though, since those can happen very frequently and it would be a hassle to post all of them on XDA. That's where this bot comes into play.

## Installation
These instructions assume you're using a Debian-based GNU/Linux distribution.
### Set up Python for the bot

1. Install Python 3.4 and pip (Any Python 3 version is file, really)
```bash
sudo apt-get install python3.4 python3-pip
```

2. Install the required pip modules
```bash
sudo pip3 install pyTelegramBotAPI requests
```

### Set up the bot

1. Clone this repository using the following command
```bash
git clone git@gitlab.com:YBinnenweg/telegram-lawnchair-mirror.git
```

2. Enter the repository folder
```bash
cd telegram-lawnchair-mirror
```

3. Copy the default configuration file
```bash
cp config.cfg.default config.cfg
```

4. Fill out the config file, the required options are listed here
```
API_KEY: keyhere
```
The Python bot needs this API key in order to talk to Telegram. Don't have an API key? Have a look at [this](https://core.telegram.org/bots) guide by Telegram to set up a bot.
```
DOWNLOAD_DIR: downloads/
```
The directory where downloads will be stored (make sure the user you're running the bot as has write permissions!). This path has to be the **full** path to the directory (ie. `/home/user/telegram-bot/files/downloads/`).
```
LOG_DIR: logs/
```
The directory where the logs will be stored (make sure the user you're running the bot as has write permissions!).
```
ALLOWED_CHANNELS: -1000000000
```
The id of a channel that is allowed to mirror files via this bot. The id will be printed on-screen when it is being denied.

### Test the bot
Run the following command
```bash
python3 bot.py
```
The bot should now be up & running! :) It's recommended you try it out at this stage. Once you're confident it's properly working, move on!

### Set up the systemd service
In order to properly run the bot we're going to set up a systemd service file so that we can run the bot that way:
1. Copy the service template from the [misc](./misc/) folder to `/etc/systemd/system/lawnchairmirror.service`
```bash
sudo cp misc/lawnchairmirror.service /etc/systemd/system/lawnchairmirror.service
```

2. Replace the following variables with the correct information:
  - PATH_TO_WORKING_DIRECTORY: The working directory the service will use. I'd recommend you set this to the repository directory (ie. `/home/lawnchairmirror/telegram-lawnchair-mirror`)
  - USERNAME: The username of the user the bot should run as
  - GROUP: The group of the user the bot should run as
  - PATH_TO_HOMEDIR: The path to the homedir of the user that the bot will run as
  - PATH_TO_DOWNLOAD_DIR: The path to the directory where you will store your downloads (the directory you set earlier in the `config.cfg` file)
  - PATH_TO_BOT.PY: The path to the `bot.py` file

3. Tell systemd you want to load the new service file we just created:
```bash
sudo systemctl daemon-reload
```

4. Start the service:
```bash
sudo systemctl start lawnchairmirror.service
```

    You should now check if the bot is running properly, you can do this in multiple ways, these are the two I recommend:
    1. `sudo systemctl status lawnchairmirror.service`
    2. `ps aux | grep python3` or `ps aux | grep bot.py`

    After you've verified the bot is running properly, you can set the service to load when your server starts!

5. Enable the service at boot:
```bash
sudo systemctl enable lawnchairmirror.service
```

The bot should now be running and automatically start when your system reboots! In addition to that the `Restart=always` line in the `lawnchairmirror.service` file ensures the bot is restarted in case it crashes (which may happen due to network issues for example).

### Tips
- Create a separate user with as few privileges as possible to run the bot as. This ensures that if the bot somehow gets compromised, your own personal user is not affected, and the damage is as limited as possible.
- Set up the bot in such a way that it writes to a directory, which is the documentroot for a site at the same time. If you then also enable directory listing in your virtualhost/server block, the files you're mirroring are automatically available via HTTPS!

## FAQ

### So this bot can only be used for Lawnchair?
Kinda :/  
Everything before commit b3b282cbd85c1fd1a049c045da3f2d2dfa2776a5 can be used to mirror any channel. The changes after that include Lawnchair-specific changes for parsing the changelog for example. They're not too hard to adjust/rip out though! :)

### Your code is shit
Potatoes. Show me you can do it better.

## Links
- [Lawnchair website](https://lawnchair.deletescape.ch/)
- [Lawnchair main discussion group](https://t.me/lawnchairgroup)
- [Lawnchair Travis CI channel](https://t.me/lawnchairci)
- [Lawnchair stable builds channel](https://t.me/lawnchairchannel)
