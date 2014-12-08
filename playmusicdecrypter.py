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
        
        if self.info is None:
            raise ValueError("Empty file info!")

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

    def normalize_path(self, path):
        return unicode(self.normalize_path.re.sub(" ", path))
    normalize_path.re = re.compile(r'[<>:"/\\|?*]')

    def get_outfile(self):
        """Returns output filename based on song informations"""
        destination_dir = os.path.join(self.normalize_path(self.info["AlbumArtist"]), self.normalize_path(self.info["Album"]))
        filename = u"{TrackNumber:02d} - {Title}.mp3".format(**self.info)
        return os.path.join(destination_dir, self.normalize_path(filename))

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
    obj=zlib.decompressobj()
    ab_file = os.path.join(destination_dir, "music.ab")
    ab=open(ab_file, "rb")
    buf_size = 1024*1024
    data = ab.read(buf_size)[24:]
    with open(os.path.join(destination_dir, "music.ab.raw"), "wb") as f:
        f.write(obj.decompress(data))

        data = ab.read(buf_size)
        while data:
            f.write(obj.decompress(data))
            data = ab.read(buf_size)
        f.write(obj.flush())
        
    os.remove(ab_file)

    tar = tarfile.open(os.path.join(destination_dir, "music.ab.raw"))
    tf = tar.extractfile("apps/com.google.android.music/db/music.db")
    with open(os.path.join(destination_dir, "music.db"), "wb") as f:
        f.write(tf.read())

def pull_library(destination_dir="music"):
    """Pull Google Play Music library from backup"""
    if not os.path.isdir(destination_dir):
        os.makedirs(destination_dir)

    print("Extracting encrypted MP3 files from backup...")
    backup_file = os.path.join(destination_dir, "..", "music.ab.raw")
    tar = tarfile.open(backup_file)
    
    for member in tar.getmembers():
        if member.name.endswith(".mp3"):
            tf = tar.extractfile(member)
            with open(os.path.join(destination_dir, os.path.basename(member.name)), "wb") as f:
                f.write(tf.read())
                
    os.remove(backup_file)

def decrypt_files(source_dir="music", destination_dir=".", database="music.db"):
    """Decrypt all MP3 files in source directory and write them to destination directory"""
    if not os.path.isdir(destination_dir):
        os.makedirs(destination_dir)

    for f in glob.glob(os.path.join(source_dir, "*.mp3")):
        try:
            decrypter = PlayMusicDecrypter(database, f)
            print(u"Decrypting file {} -> {}".format(f, decrypter.get_outfile()))
        except ValueError as e:
            print(u"Skipping file {} ({})".format(f, e))
            continue

        outfile = os.path.join(destination_dir, decrypter.get_outfile())
        if not os.path.isdir(os.path.dirname(outfile)):
            os.makedirs(os.path.dirname(outfile))

        decrypter.decrypt_all(outfile)
        decrypter.update_id3(outfile)

        os.remove(f)

def main():
    # Parse command line options
    parser = optparse.OptionParser(description="Decrypt MP3 files from Google Play Music offline storage (All Access)",
                                   usage="usage: %prog [-h] [options] destination_dir",
                                   version="%prog {}".format(__version__))
    parser.add_option("-d", "--database",
                      help="local path to Google Play Music database file (will be downloaded from device via adb if not specified)")
    parser.add_option("-l", "--library",
                      help="local path to directory with encrypted MP3 files (will be downloaded from device via adb if not specified")
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("you have to specify destination directory for decrypted MP3 files")
    destination_dir = args[0]

    # Download Google Play Music database from device via adb
    if not options.database:
        options.database = os.path.join(destination_dir, "music.db")
        pull_database(destination_dir)

    # Extract encrypted MP3 files from backup
    if not options.library:
        options.library = os.path.join(destination_dir, "music")
        pull_library(options.library)

    # Decrypt all MP3 files
    decrypt_files(options.library, destination_dir, options.database)


if __name__ == "__main__":
    main()
