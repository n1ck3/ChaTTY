ChaTTY
======

ChaTTY is a simple telnet chat server built using python and gevent.

## Requirements
* Python==2.7.3
* gevent==0.13.6

## Setup
Setup venv, pull this repo, and install dependencies
```
mkdir -p ~/git/chatty && cd ~/git/chatty
virtualenv-2.7 . && source bin/activate
git clone https://github.com/n1ck3/ChaTTY.git && cd ChaTTY
pip install -r requirements.txt
```

## Usage
### Starting the server
```
cd /path/to/ChaTTY
./chatty.py
```

### Connecting to the server
```
telnet localhost 1337
```

### Using ChaTTY over telnet
* Help: `/help`
* Set status: `/status <status>`
* List connected users: `/list`
* Send public message: `<message>`
* Send private message: `/message <username> <message>`
* Quit: `/quit`
