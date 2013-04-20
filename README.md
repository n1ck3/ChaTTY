ChaTTY
======

ChaTTY is a simple telnet chat server built using python and gevent.

## Requirements
* Python==2.7.3
* gevent==0.13.6

## Setup
Install dependencies and pull this repo.
```
sudo apt-get install python2.7 python-gevent
cd ~
git clone https://github.com/n1ck3/ChaTTY.git
```

## Usage
### Starting the server
```
cd /path/to/ChaTTY
./chatty.py
```

### Connecting to the server
```
telnet localhost 6789
```

### Using ChaTTY over telnet
* Help: `/help`
* Set status: `/status <status>`
* List connected users: `/list`
* Send public message: `<message>`
* Send private message: `/message <username> <message>`
* Quit: `/quit`
