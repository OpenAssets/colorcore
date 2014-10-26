# -*- coding: utf-8; -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2014 Flavien Charlon
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import bitcoin.base58
import bitcoin.wallet

class Base58Address(bytes):
    """Represents a Base58-encoded address. It includes a version, checksum and namespace."""

    def __init__(self, data, version, namespace):
        """
        Initializes a Base58Address object from data, version and namespace.

        :param bytes data: The base-58 payload.
        :param int version: The version byte.
        :param int | None namespace: The namespace byte.
        :return: The Base58Address instance.
        :rtype: Base58Address
        """
        if not (0 <= version <= 255):
            raise ValueError('version must be in range 0 to 255 inclusive; got %d' % version)

        if namespace is not None and not (0 <= namespace <= 255):
            raise ValueError('namespace must be None or in range 0 to 255 inclusive; got %d' % version)

        if len(data) != 20:
            raise ValueError('The payload must be 20 bytes long')

        super().__init__()

        self.address = bitcoin.wallet.CBitcoinAddress.from_bytes(data, version)
        self.namespace = namespace

    def __new__(cls, data, version, namespace, *args, **kwargs):
        return super().__new__(cls, data)

    @classmethod
    def from_string(cls, base58):
        """
        Creates a new instance of the Base58Address class.

        :param str base58: The Base-58 encoded address.
        :return: The Base58Address instance.
        :rtype: Base58Address
        """
        decoded_bytes = bitcoin.base58.decode(base58)

        checksum = decoded_bytes[-4:]
        calculated_checksum = bitcoin.core.Hash(decoded_bytes[:-4])[:4]

        if checksum != calculated_checksum:
            raise bitcoin.base58.Base58ChecksumError(
                'Checksum mismatch: expected %r, calculated %r' % (checksum, calculated_checksum))

        if len(decoded_bytes) == 26:
            # The address has a namespace defined
            namespace, version, data = decoded_bytes[0:1], decoded_bytes[1:2], decoded_bytes[2:-4]
            return cls(data, version[0], namespace[0])
        elif len(decoded_bytes) == 25:
            # The namespace is undefined
            version, data = decoded_bytes[0:1], decoded_bytes[1:-4]
            return cls(data, version[0], None)
        else:
            raise ValueError('Invalid length')

    def to_bytes(self):
        """Converts to a bytes instance.
        Note that it's the data represented that is converted; the checksum, version and namespace are not included.

        :return: The Base58Address instance.
        :rtype: bytes
        """
        return b'' + self

    def __str__(self):
        """
        Converts the address to a string.

        :return: The base-58 encoded string.
        :rtype: str
        """
        if self.namespace is None:
            full_payload = bytes([self.address.nVersion]) + self
        else:
            full_payload = bytes([self.namespace]) + bytes([self.address.nVersion]) + self

        checksum = bitcoin.core.Hash(full_payload)[0:4]
        return bitcoin.base58.encode(full_payload + checksum)