Play Music Decrypter
====================

Decrypt MP3 files from Google Play Music offline storage (All Access)

Dependencies
------------

- Python 2.7
- PyCrypto (https://www.dlitz.net/software/pycrypto)
- Mutagen (https://bitbucket.org/lazka/mutagen)

Optional dependencies
---------------------

- adb (Android SDK Tools - https://developer.android.com/sdk/index.html#Other)

Usage
-----
1. Root your phone and install _BusyBox_ (https://play.google.com/store/apps/details?id=stericson.busybox).
   You can skip this step if you are using CyanogenMod or other ROM that already includes BusyBox
2. Enable _Developer options_ by clicking 7x on _Build number_ in Settings -> About phone
3. Enable _USB debugging_ in Settings -> Developer options
4. Connect your phone to computer with USB cable
5. If you have any firewall on your PC, you must first allow inbound traffic to TCP port 23456
6. Run `playmusicdecrypter destination_dir` (your MP3 files will be downloaded and decrypted to destination_dir folder)
7. Confirm _Allow USB debugging_ dialog and then superuser permissions request for _ADB shell_ (on your phone)

Help
----

    Usage: playmusicdecrypter [-h] [options] [destination_dir]
    
    Decrypt MP3 files from Google Play Music offline storage (All Access)
    
    Options:
      --version             show program's version number and exit
      -h, --help            show this help message and exit
      -a ADB, --adb=ADB     path to adb executable
      -d DATABASE, --database=DATABASE
                            local path to Google Play Music database file (will be
                            downloaded from device via adb if not specified)
      -l LIBRARY, --library=LIBRARY
                            local path to directory with encrypted MP3 files (will
                            be downloaded from device via adb if not specified
      -r REMOTE, --remote=REMOTE
                            remote path to directory with encrypted MP3 files on
                            device (default:
                            /data/data/com.google.android.music/files/music)
