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

import bitcoin.core
import colorcore.addresses
import unittest
import unittest.mock


class Base58AddressTests(unittest.TestCase):

    def setUp(self):
        bitcoin.SelectParams('mainnet')

    def test_from_string_no_namespace(self):
        address = colorcore.addresses.Base58Address.from_string('16UwLL9Risc3QfPqBUvKofHmBQ7wMtjvM')

        self.assertEqual(0, address.address.nVersion)
        self.assertEqual(None, address.namespace)
        self.assertEqual(bitcoin.core.x('010966776006953D5567439E5E39F86A0D273BEE'), address.to_bytes())

    def test_from_string_with_namespace(self):
        address = colorcore.addresses.Base58Address.from_string('akB4NBW9UuCmHuepksob6yfZs6naHtRCPNy')

        self.assertEqual(0, address.address.nVersion)
        self.assertEqual(19, address.namespace)
        self.assertEqual(bitcoin.core.x('010966776006953D5567439E5E39F86A0D273BEE'), address.to_bytes())

    def test_from_string_invalid_length(self):
        self.assertRaises(
            ValueError,
            colorcore.addresses.Base58Address.from_string,
            '5Hwgr3u458GLafKBgxtssHSPqJnYoGrSzgQsPwLFhLNYskDPyyA')

    def test_from_string_invalid_checksum(self):
        self.assertRaises(
            bitcoin.base58.Base58ChecksumError,
            colorcore.addresses.Base58Address.from_string,
            'akB4NBW9UuCmHuepksob6yfZs6naHtRCPNz')

    def test_from_bytes_invalid_value(self):
        self.assertRaises(
            ValueError,
            colorcore.addresses.Base58Address,
            bitcoin.core.x('010966776006953D5567439E5E39F86A0D273BEE'),
            256, 1)

        self.assertRaises(
            ValueError,
            colorcore.addresses.Base58Address,
            bitcoin.core.x('010966776006953D5567439E5E39F86A0D273BEE'),
            1, 256)

        self.assertRaises(
            ValueError,
            colorcore.addresses.Base58Address,
            bitcoin.core.x('010966776006953D5567439E5E39F86A0D273BEEFF'),
            1, 1)

    def test_str_no_namespace(self):
        address = colorcore.addresses.Base58Address.from_string('16UwLL9Risc3QfPqBUvKofHmBQ7wMtjvM')
        result = str(address)

        self.assertEqual('16UwLL9Risc3QfPqBUvKofHmBQ7wMtjvM', result)

    def test_str_with_namespace(self):
        address = colorcore.addresses.Base58Address.from_string('akB4NBW9UuCmHuepksob6yfZs6naHtRCPNy')
        result = str(address)

        self.assertEqual('akB4NBW9UuCmHuepksob6yfZs6naHtRCPNy', result)
