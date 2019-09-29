# drastikbot

Drastikbot is an IRC bot that makes it easy to add new features thanks to its modular design.
Version 2.1 offers a new User Access List to stop users from abusing the bot's features and
an interface that allows Channel Operators and Bot Owners to access the bot's moderation and
personalization features over IRC.

Visit: http://drastik.org/drastikbot/

### Features
- Automatic module reloading
- Simple to use module API
- SSL Support
- SASL Support (Plain)
- User Access Lists
- Per module channel whilelist/blacklist
- Per channel command prefix
- User authentication with NickServ
- Easy administration over IRC

### Prerequisites

```
Python 3
GNU/Linux or any unix-like OS.
```

### Installing

Check http://drastik.org/drastikbot/docs/start.html for installation and configuration instructions

### Modules

You can find some modules to use with the bot here: https://github.com/olagood/drastikbot_modules

Contributing new modules is welcomed provided that the Contribution guidelines below are followed.

## Contributing

All code contributions must follow the PEP 8 styling guidelines. Use of flake8 is recommended.

The code must be fully tested to ensure it does not break drastikbot or its modules.

## Authors

* **drastik** - [olagood](https://github.com/olagood) | [drastik.org](http://drastik.org)

## License

This project is licensed under the GNU Affero General Public License Version 3 ONLY - see the [COPYING](COPYING) file for details.
