# -*- coding: utf-8 -*-
#
#    bitcoinlib - Compact Python Bitcoin Library
#    Public key cryptography and Hierarchical Deterministic Key Management
#    Copyright (C) 2016 October
#    1200 Web Development
#    http://1200wd.com/
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import hashlib
import hmac
import random
import struct
import ecdsa

from encoding import _r, change_base, generator, SECP256k1, curve, ec_order

HDKEY_XPRV = '0488ade4'.decode('hex')
HDKEY_XPUB = '0488b21e'.decode('hex')


def get_key_format(key, keytype=None):
    """
    Determins the type and format of a public or private key by length and prefix.
    This method does not validate if a key is valid.
    :param key: Any private or public key
    :param keytype: 'private' or 'public', is most cases not required as methods takes best guess
    :return: format of key as string
    """
    if keytype not in [None, 'private', 'public']:
        raise ValueError("Keytype must be 'private' or 'public")
    if isinstance(key, (int, long, float)):
        return 'decimal'
    elif len(key) == 130 and key[:2] == '04' and keytype != 'private':
        return "public_uncompressed"
    elif len(key) == 66 and key[:2] in ['02', '03'] and keytype != 'private':
        return "public"
    elif len(key) == 32:
        return 'bin'
    elif len(key) == 33:
        return 'bin_compressed'
    elif len(key) == 64:
        return 'hex'
    elif len(key) == 66  and keytype != 'public':
        return 'hex_compressed'
    elif key[:1] in ('K', 'L'):
        return 'wif_compressed'
    elif key[:1] == '5':
        return 'wif'
    else:
        raise ValueError("Unrecognised key format")


class Key:
    """
    Class to generate, import and convert public cryptograpic key pairs used for bitcoin.

    If no key is specified when creating class a cryptographically secure Private Key is
    generated using the os.urandom() function.

    A public key or (bitcoin)address is generator on request if a private key is known.
    """

    def __init__(self, import_key=None):
        self._public = None
        self._public_uncompressed = None
        if not import_key:
            self._secret = random.SystemRandom().randint(0, _r)
            return

        key_format = get_key_format(import_key)
        if key_format in ['public_uncompressed', 'public']:
            self._secret = None
            if key_format=='public_uncompressed':
                self._public = import_key
                self._x = import_key[2:66]
                self._y = import_key[66:130]
            else:
                self._public = import_key
                self._x = import_key[2:66]
                self._y = 0L
        else:
            if key_format in ['hex', 'hex_compressed']:
                self._secret = change_base(import_key, 16, 10)
            elif key_format == 'decimal':
                self._secret = import_key
            elif key_format in ['bin', 'bin_compressed']:
                self._secret = change_base(import_key, 256, 10)
            elif key_format in ['wif', 'wif_compressed']:
                # Check and remove Checksum, prefix and postfix tags
                key = change_base(import_key, 58, 256)
                checksum = key[-4:]
                key = key[:-4]
                if checksum != hashlib.sha256(hashlib.sha256(key).digest()).digest()[:4]:
                    raise ValueError("Invalid checksum, not a valid WIF compressed key")
                if import_key[0] in "KL":
                    if key[-1:] != chr(1):
                        raise ValueError("Not a valid WIF private compressed key. key[-1:] != chr(1) failed")
                    key = key[:-1]
                if key[:1] != chr(128):
                    raise ValueError("Not a valid WIF private key. key[:1] != chr(128) failed")
                key = key[1:]
                self._secret = change_base(key, 256, 10)

    def __repr__(self):
        if self._secret:
            return str(self.private_dec())
        else:
            return self._public

    def private_dec(self):
        if not self._secret:
            return False
        return self._secret

    def private_hex(self):
        if not self._secret:
            return False
        return change_base(str(self._secret), 10, 16, 64)

    def private_bit(self):
        if not self._secret:
            return False
        return change_base(str(self._secret), 10, 2, 256)

    def wif(self, compressed=True):
        """
        Get Private Key in Wallet Import Format, steps:
        (1) Convert to Binary and add 0x80 hex
        (2) Calculate Double SHA256 and add as checksum to end of key

        :param compressed: Get compressed private key, which means private key will be used to generate compressed public keys.
        :return: Base58Check encoded Private Key WIF
        """
        if not self._secret:
            return False
        key = chr(128) + change_base(str(self._secret), 10, 256, 32)
        if compressed:
            key += chr(1)
        key += hashlib.sha256(hashlib.sha256(key).digest()).digest()[:4]
        return change_base(key, 256, 58)

    def _create_public(self):
        point = generator
        point *= int(self._secret)
        point1 = ecdsa.ellipticcurve.Point(curve, point.x(), point.y(), ec_order)
        assert point1 == point
        if point.y() % 2: prefix = '03'
        else: prefix = '02'
        self._public = prefix + change_base(int(point.x()), 10, 16, 64)
        self._public_uncompressed = '04' + change_base(int(point.x()), 10, 16, 64) + change_base(int(point.y()), 10, 16, 64)

    def public(self):
        if not self._public:
            self._create_public()
        return self._public

    def public_uncompressed(self):
        if not self._public_uncompressed:
            self._create_public()
        return self._public_uncompressed

    def public_point(self):
        if not self._public:
            self._create_public()
        x = self._x and int(change_base(self._x, 16, 10))
        y = self._y and int(change_base(self._y, 16, 10))
        return (x, y)

    def public_hex(self):
        if not self._public:
            self._create_public()
        return self._public

    def public_byte(self):
        if not self._public:
            self._create_public()
        return change_base(self._public, 16, 256)

    def hash160(self):
        if not self._public:
            self._create_public()
        key = change_base(self._public, 16, 256)
        return hashlib.new('ripemd160', hashlib.sha256(key).digest()).hexdigest()

    def address(self):
        if not self._public:
            self._create_public()
        key = change_base(self._public, 16, 256)
        key = chr(0) + hashlib.new('ripemd160', hashlib.sha256(key).digest()).digest()
        checksum = hashlib.sha256(hashlib.sha256(key).digest()).digest()
        return change_base(key + checksum[:4], 256, 58)


class HDKey:

    @staticmethod
    def from_seed(import_seed):
        seed = change_base(import_seed, 16, 256)
        I = hmac.new("Bitcoin seed", seed, hashlib.sha512).digest()
        key = I[:32]
        chain = I[32:]
        return HDKey(key=key, chain=chain)

    def __init__(self, import_key=None, key=None, chain=None, depth=0, parent_fingerprint = b'\0\0\0\0', child_index = 0):
        isprivate = True
        if not (key and chain):
            if not import_key:
                # Generate new Master Key
                seedbits = random.SystemRandom().getrandbits(512)
                seed = change_base(str(seedbits), 10, 256)
                key, chain = self._key_derivation(seed)
            elif len(import_key) == 64:
                key = import_key[:32]
                chain = import_key[32:]
            elif import_key[:4] in ['xprv', 'xpub']:
                bkey = change_base(import_key, 58, 256)
                if ord(bkey[45]):
                    isprivate = False
                    key = bkey[45:78]
                else:
                    key = bkey[46:78]
                depth = ord(bkey[4])
                parent_fingerprint = bkey[5:9]
                child_index = int(change_base(bkey[9:13], 256, 10))
                chain = bkey[13:45]
                # chk = bkey[78:82]
            else:
                raise ValueError("Key format not recognised")

        self._key = key
        self._secret = change_base(key, 256, 10)
        self._chain = chain
        self._depth = depth
        self._parent_fingerprint = parent_fingerprint
        self._child_index = child_index
        self._isprivate = isprivate
        self._path = None
        print "depth %d, child %d" % (self._depth, self._child_index)
        if isprivate:
            self._public = None
        else:
            self._public = key

    def __repr__(self):
        return self.extended_wif()

    def info(self):
        if self._isprivate:
            print "SECRET EXPONENT"
            print " Private Key (hex)           ", change_base(self._key, 256, 16)
            print " Private Key (long)          ", self._secret
            print " Private Key (wif)           ", self.private().wif()
            print ""
        print "PUBLIC KEY"
        print " Public Key (hex)            ", self.public()
        print " Address (b58)               ", self.public().address()
        print " Fingerprint (hex)           ", change_base(self.fingerprint(), 256, 16)
        print ""
        print "EXTENDED KEY INFO"
        print " Path                        ", self.path()
        print " Chain code (hex)            ", change_base(self.chain(), 256, 16)
        print " Child Index                 ", self.child_index()
        print " Parent Fingerprint (hex)    ", change_base(self.parent_fingerprint(), 256, 16)
        print " Depth                       ", self.depth()
        print " Extended Public Key (wif)   ", self.extended_wif_public()
        print " Extended Private Key (wif)  ", self.extended_wif()

    def _key_derivation(self, seed):
        chain = hasattr(self, '_chain') and self._chain or "Bitcoin seed"
        I = hmac.new(chain, seed, hashlib.sha512).digest()
        key = I[:32]
        chain = I[32:]
        return key, chain

    def fingerprint(self):
        return hashlib.new('ripemd160', hashlib.sha256(self.public().public_byte()).digest()).digest()[:4]

    def extended_wif(self, public=False, child_index=None):
        rkey = self._key
        if self._isprivate and not public:
            raw = HDKEY_XPRV
            typebyte = '\x00'
        else:
            raw = HDKEY_XPUB
            typebyte = ''
            if public:
                rkey = self.public().public_byte()
        if child_index:
            self._child_index = child_index
        raw += chr(self._depth) + self._parent_fingerprint + \
              struct.pack('>L', self._child_index) + \
              self._chain + typebyte + rkey
        chk = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[:4]
        ret = raw+chk
        return change_base(ret, 256, 58, 111)

    def extended_wif_public(self):
        return self.extended_wif(public=True)

    def key(self):
        return self._key or ''

    def chain(self):
        return self._chain or ''

    def depth(self):
        return self._depth or 0

    def parent_fingerprint(self):
        return self._parent_fingerprint or b'\0\0\0\0'

    def child_index(self):
        return self._child_index or 0

    def isprivate(self):
        return self._isprivate

    def public(self):
        if not self._public:
            pub = Key(self._key).public()
            return Key(pub)
        return self._public

    def private(self):
        if self._key:
            return Key(self._key)

    def path(self):
        return self._path or ''

    def subkey_for_path(self, path):
        self._path = path
        key = self
        if path[0] in 'Mm':
            path = path[2:]
        if path:
            levels = path.split("/")
            for level in levels:
                hardened = level[-1] in "'HhPp"
                if hardened:
                    level = level[:-1]
                index = int(level)
                key = key.child_private(index=index, hardened=hardened)
        return key

    def child_private(self, index=0, hardened=True):
        if not self._isprivate:
            raise ValueError("Need a private key to create child private key")
        if hardened:
            index |= 0x80000000
        data = b'\0' + self._key + struct.pack('>L', index)
        key, chain = self._key_derivation(data)

        key = change_base(key, 256, 10)
        if key > _r:
            raise ValueError("Key cannot be greater then _r. Try another index number.")
        newkey = (key + self._secret) % generator.order()
        if newkey == 0:
            raise ValueError("Key cannot be zero. Try another index number.")
        newkey = change_base(newkey, 10, 256)

        return HDKey(key=newkey, chain=chain, depth=self._depth+1, parent_fingerprint=self.fingerprint(),
                     child_index=index)


if __name__ == '__main__':
    # k = Key('5KJvsngHeMpm884wtkJNzQGaCErckhHJBGFsvd3VyK5qMZXj3hS')
    #
    k = HDKey.from_seed('000102030405060708090a0b0c0d0e0f')
    # print k.extended_wif(public=True)
    #
    # pk = HDKey()
    # print "Random private key: %s" % pk.extended_wif()
    #
    # pk = HDKey('xprv9z4pot5VBttmtdRTWfWQmoH1taj2axGVzFqSb8C9xaxKymcFzXBDptWmT7FwuEzG3ryjH4ktypQSAewRiNMjANTtpgP4mLTj34bhnZX7UiM')
    # print "Imported private key: %s" % k
    #
    # # pK = HDKey('xpub6D4BDPcP2GT577Vvch3R8wDkScZWzQzMMUm3PWbmWvVJrZwQY4VUNgqFJPMM3No2dFDFGTsxxpG5uJh7n7epu4trkrX7x7DogT5Uv6fcLW5')
    # # print "Imported private key: %s" % pK.extended_wif()
    #
    # print change_base(k.fingerprint(), 256, 16)
    # print k.public()
    k2 = k.subkey_for_path('m/0h')
    # print "Subkey for path m/0h: %s" % k.child_private()
    # print "     ==?==            xprv9uHRZZhk6KAJC1avXpDAp4MDc3sQKNxDiPvvkX8Br5ngLNv1TxvUxt4cV1rGL5hj6KCesnDYUhd7oWgT11eZG7XnxHrnYeSvkzY7d2bhkJ7"
    k2.info()