# drastikbot

Drastikbot is an IRC bot that makes it easy to add new features thanks to its modular design.
Version 2.2 offers a new module API and is not backwards compatible with previous
drastikbot versions.

Warning: drastikbot 2.2 is a WIP. You are adviced to use another IRC
bot unless you are comfortable with working with python.

### Features
- Module hot code reloading
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
Python 3.8
```

### Modules

Modules are used to add functionality to the bot. By default,
drastikbot, only has a small set of built in modules used for
implementing the IRC protocol. A list of modules you can use can be
found here: https://github.com/olagood/drastikbot_modules

Contributing new modules is welcomed provided that the Contribution
guidelines below are followed.

## Contributing

All code contributions must follow the PEP 8 styling guidelines. Use of flake8 is recommended.

The code must be fully tested to ensure it does not break drastikbot or its modules.

## Authors

* **drastik** - [olagood](https://github.com/olagood) | [drastik.org](http://drastik.org)

## License

This project is licensed under the GNU Affero General Public License Version 3 - see the [COPYING](COPYING) file for details.
