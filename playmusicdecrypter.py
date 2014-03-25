#!/usr/bin/env python2

# playmusicdecrypter - decrypt MP3 files from Google Play Music offline storage (All Access)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

__version__ = "1.0"

import os, sys, struct, re, glob, subprocess, zlib, tarfile, io, optparse
import Crypto.Cipher.AES, Crypto.Util.Counter
import mutagen
import sqlite3

class PlayMusicDecrypter:
    """Decrypt MP3 file from Google Play Music offline storage (All Access)"""
    def __init__(self, database, infile):
        # Open source file
        self.infile = infile
        self.source = open(infile, "rb")

        # Test if source file is encrypted
        start_bytes = self.source.read(4)
        if start_bytes != "\x12\xd3\x15\x27":
            raise ValueError("Invalid file format!")

        # Get file info
        self.database = database
        self.info = self.get_info()

    def decrypt(self):
        """Decrypt one block"""
        data = self.source.read(1024)
        if not data:
            return ""

        iv = data[:16]
        encrypted = data[16:]

        counter = Crypto.Util.Counter.new(64, prefix=iv[:8], initial_value=struct.unpack(">Q", iv[8:])[0])
        cipher = Crypto.Cipher.AES.new(self.info["CpData"], Crypto.Cipher.AES.MODE_CTR, counter=counter)

        return cipher.decrypt(encrypted)

    def decrypt_all(self, outfile=""):
        """Decrypt all blocks and write them to outfile (or to stdout if outfile in not specified)"""
        destination = open(outfile, "wb") if outfile else sys.stdout
        while True:
            decrypted = self.decrypt()
            if not decrypted:
                break

            destination.write(decrypted)
            destination.flush()

    def get_info(self):
        """Returns informations about song from database"""
        db = sqlite3.connect(self.database, detect_types=sqlite3.PARSE_DECLTYPES)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()

        cursor.execute("""SELECT Title, Album, Artist, AlbumArtist, Composer, Genre, Year, Duration,
                                 TrackCount, TrackNumber, DiscCount, DiscNumber, Compilation, CpData
                          FROM music
                          WHERE LocalCopyPath = ?""", (os.path.basename(self.infile),))
        row = cursor.fetchone()
        if row:
            return dict(row)

    def get_outfile(self):
        """Returns output filename based on song informations"""
        filename = u"{AlbumArtist} - {Album} - Disc {DiscNumber} - Track {TrackNumber:02d} - {Title}.mp3".format(**self.info)
        return re.sub(r'[<>:"/\\|?*]', " ", filename)

    def update_id3(self, outfile):
        """Update ID3 tags in outfile"""
        audio = mutagen.File(outfile, easy=True)
        audio.add_tags()
        audio["title"] = self.info["Title"]
        audio["album"] = self.info["Album"]
        audio["artist"] = self.info["Artist"]
        audio["performer"] = self.info["AlbumArtist"]
        audio["composer"] = self.info["Composer"]
        audio["genre"] = self.info["Genre"]
        audio["date"] = str(self.info["Year"])
        audio["tracknumber"] = str(self.info["TrackNumber"])
        audio["discnumber"] = str(self.info["DiscNumber"])
        audio["compilation"] = str(self.info["Compilation"])
        audio.save()

def pull_database(destination_dir="."):
    """Pull Google Play Music database from device (works even without root access, yay!)"""
    if not os.path.isdir(destination_dir):
        os.makedirs(destination_dir)

    print("Downloading database backup from device...")
    subprocess.check_call(["adb", "backup", "-f", os.path.join(destination_dir, "music.ab"), "com.google.android.music"])

    print("Extracting database file from backup...")
    decompressed = zlib.decompress(open(os.path.join(destination_dir, "music.ab"), "rb").read()[24:])
    tar = tarfile.open(fileobj=io.BytesIO(decompressed))
    tf = tar.extractfile("apps/com.google.android.music/db/music.db")
    with open(os.path.join(destination_dir, "music.db"), "wb") as f:
        f.write(tf.read())

def pull_library(source_dir="/storage/sdcard0/Android/data/com.google.android.music/files/music", destination_dir="music"):
    """Pull Google Play Music library from device"""
    if not os.path.isdir(destination_dir):
        os.makedirs(destination_dir)

    print("Downloading encrypted MP3 files from device...")
    subprocess.check_call(["adb", "pull", source_dir, destination_dir])

def decrypt_files(source_dir="music", destination_dir=".", database="music.db"):
    """Decrypt all MP3 files in source directory and write them to destination directory"""
    if not os.path.isdir(destination_dir):
        os.makedirs(destination_dir)

    for f in glob.glob(os.path.join(source_dir, "*.mp3")):
        try:
            decrypter = PlayMusicDecrypter(database, f)
            print(u"Decrypting file {} -> {}".format(f, decrypter.get_outfile()))
        except ValueError:
            print(u"Skipping file {} (invalid file format)".format(f))
            continue

        outfile = os.path.join(destination_dir, decrypter.get_outfile())
        decrypter.decrypt_all(outfile)
        decrypter.update_id3(outfile)

def main():
    # Parse command line options
    parser = optparse.OptionParser(description="Decrypt MP3 files from Google Play Music offline storage (All Access)",
                                   usage="usage: %prog [-h] [options] destination_dir",
                                   version="%prog {}".format(__version__))
    parser.add_option("-d", "--database",
                      help="local path to Google Play Music database file (will be downloaded from device via adb if not specified)")
    parser.add_option("-l", "--library",
                      help="local path to directory with encrypted MP3 files (will be downloaded from device via adb if not specified")
    parser.add_option("-r", "--remote", default="/storage/sdcard0/Android/data/com.google.android.music/files/music",
                      help="remote path to directory with encrypted MP3 files on device (default: %default)")
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("you have to specify destination directory for decrypted MP3 files")
    destination_dir = args[0]

    # Download Google Play Music database from device via adb
    if not options.database:
        options.database = os.path.join(destination_dir, "music.db")
        pull_database(destination_dir)

    # Download encrypted MP3 files from device via adb
    if not options.library:
        options.library = os.path.join(destination_dir, "music")
        pull_library(options.remote, options.library)

    # Decrypt all MP3 files
    decrypt_files(options.library, destination_dir, options.database)


if __name__ == "__main__":
    main()
