# Emoji Throughout Time ![img](https://i.imgur.com/m3uZGO3.png)
Visualisation from [this](https://www.reddit.com/r/dataisbeautiful/comments/8icg5x/personal_usage_of_emoji_animated_over_time_oc/) reddit /r/dataisbeautiful post.

![img](https://i.imgur.com/OHhPC1u.gif)

## Disclaimer
This software is not exactly if at all well tested, I hope you can overcome any issues you might encounter.

## Install
Clone or download this repository. Download Twemoji from https://github.com/twitter/twemoji/releases/tag/v2.5.1. Inside the archive find `72x72` subfolder and unpack it as an `emoji` folder into the repository root directory.

Install dependencies using `pip install -r requirements.txt` or manually.

## Run
Specify any required options inside `settings.py` and run `> python ./plot.py`.  
Dataset file is assumed to have the following CSV structure:
```csv
timestamp,text
timestamp,text
...
```
Timestamp is a standard UTC timestamp. Script will scan over all records for emoji and custom emoji. Custom emoji must appear in text in the following form:  
`<:emoji-name:optional-filesystem-path-or-url>`  
Custom emoji that don't have a path or url associated must be placed into `custom_emoji` directory as png images.

## Working with discord logs and custom emojis
Previously I had a custom archiver script for discord but it has stopped working after the myriad of changes in discord API and the library I was using to access it. You can try your luck with https://github.com/Tyrrrz/DiscordChatExporter.
