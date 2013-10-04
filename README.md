Play Music Decrypter
====================

Decrypt MP3 files from Google Play Music offline storage (All Access)

Dependencies
------------

- Python 2.7
- PyCrypto (https://www.dlitz.net/software/pycrypto)
- mutagen (http://code.google.com/p/mutagen)

Optional dependencies
---------------------

- adb (platform-tools from Google Android SDK - http://developer.android.com/sdk)

Usage
-----

1. Enable "Android debugging" on your phone (in System settings -> Developer options)
2. Connect your phone to computer with USB cable (you need at least Android 4.0 for adb backup to work)
3. Run "playmusicdecrypter destination_dir" (your MP3 files will be downloaded and decrypted to destination_dir folder)
4. Unlock your phone and confirm backup (leave password empty!)

Help
----

    Usage: playmusicdecrypter [-h] [options] destination_dir
    
    Decrypt MP3 files from Google Play Music offline storage (All Access)
    
    Options:
      --version             show program's version number and exit
      -h, --help            show this help message and exit
      -d DATABASE, --database=DATABASE
                            local path to Google Play Music database file (will be
                            downloaded from device via adb if not specified)
      -l LIBRARY, --library=LIBRARY
                            local path to directory with encrypted MP3 files (will
                            be downloaded from device via adb if not specified
      -r REMOTE, --remote=REMOTE
                            remote path to directory with encrypted MP3 files on
                            device (default: /storage/sdcard0/Android/data/com.goo
                            gle.android.music/files/music)
