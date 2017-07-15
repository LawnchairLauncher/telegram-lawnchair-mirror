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

2. Install the required pip module
```bash
sudo pip3 install pyTelegramBotAPI
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
The directory where downloads will be stored (make sure the user you're running the bot as has write permissions!).
```
ALLOWED_CHANNELS: -1000000000
```
The id of a channel that is allowed to mirror files via this bot. The id will be printed on-screen when it is being denied.

### Run the bot
Run the following command
```bash
python3 bot.py
```
Yay! Your bot should now be up & running!

### Tips
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
