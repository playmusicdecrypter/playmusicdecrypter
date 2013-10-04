#!/usr/bin/env python2

from distutils.core import setup
from playmusicdecrypter import __version__

setup(name = "playmusicdecrypter",
      version = __version__,
      description = "Decrypt MP3 files from Google Play Music offline storage (All Access)",
      author = "Anonymous",
      author_email = "playmusicdecrypter@centrum.cz",
      url = "https://github.com/playmusicdecrypter/playmusicdecrypter",
      license = "GNU GPLv3",
      py_modules=["playmusicdecrypter"],
      scripts = ["playmusicdecrypter"],
      requires = ["pycrypto", "mutagen"]
)
