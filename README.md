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


### Upgrading from v2.1

Because v2.2 brings in changes that break compatibility with previous
versions you are suggested to reconfigure drastikbot 2.2 and avoid
reusing your old configuration file.

#### New module API

A new module API was introduced in v2.2. Modules written for previous
drastikbot versions have to up updated to work in v2.2.

#### New User ACL representation

The User ACL rule configuration representation has been changed from a
list of strings to a list of JSON objects. The old rules will not work
and drastikbot 2.2 will show a "dispatch error" if invalid UACL rules
are present in the configuration.

To update your rules remove them from the configuration file and
reinsert them using the command: .acl_add

#### Developer mode

A new runtime option "--dev" has been added in v2.2 to help module
development and debugging. This mode enables automatic module
reloading (the modules are reloaded on each call) and importing and
sets the bot's logging level to "debug".

During normal operation (when the --dev option is not used) you can
still perform module reloading and importing using the commands:
.mod_import and .mod_reload

## Contributing

All code contributions must follow the PEP 8 styling guidelines. Use of flake8 is recommended.

The code must be fully tested to ensure it does not break drastikbot or its modules.

## Authors

* **drastik** - [olagood](https://github.com/olagood) | [drastik.org](http://drastik.org)

## License

This project is licensed under the GNU Affero General Public License Version 3 - see the [COPYING](COPYING) file for details.
