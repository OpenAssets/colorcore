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

import bitcoin.core
import bitcoin.core.script
import colorcore.operations
import json
import openassets.protocol
import unittest
import unittest.mock


class ControllerTests(unittest.TestCase):

    def setUp(self):
        class Expando(object):
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        self.addresses = [
            Expando(
                address='moogjqrTWfjkyxLHk9ytzp147EfXVvqLEP',
                script=bitcoin.core.x('76a9145aeb17b8888d04fb47d56ba54e727b88623665b488ac')
            ),
            Expando(
                address='mpLppfoBWbdF9Y7zeN9sJHcbMzQvAeRqMs',
                script=bitcoin.core.x('76a91460cebc294b5b4ef9c32dc26bb55fff48eeaea81788ac')
            )
        ]

        self.assets = [
            Expando(
                address='qhTKTV1YV6VBaRx',
                binary=b'asset1'
            ),
            Expando(
                address='mpLppfoBWbdF9Y7zeN9sJHcbMzQvAeRqMs',
                binary=b'asset2'
            )
        ]

    # getbalance

    def test_getbalance_success(self):

        with unittest.mock.patch('bitcoin.rpc.Proxy.listunspent') as listunspent_patch, \
            unittest.mock.patch('openassets.protocol.ColoringEngine.get_output') as get_output_patch:

            self.setup_mocks(listunspent_patch, get_output_patch, [
                (20, self.addresses[0].script, self.assets[0].binary, 30),
                (50, self.addresses[1].script, self.assets[0].binary, 10),
                (80, self.addresses[0].script, None, 0)
            ])

            target = self.create_controller()

            result = target.getbalance()

            self.assert_response([
                    {
                        'address': self.addresses[0].address,
                        'value': '0.00000100',
                        'assets': [{'assetAddress': self.assets[0].address, 'quantity': '30'}]
                    },
                    {
                        'address': self.addresses[1].address,
                        'value': '0.00000050',
                        'assets': [{'assetAddress': self.assets[0].address, 'quantity':'10'}]
                    }
                ],
                result)

    # Test helpers

    def setup_mocks(self, listunspent_patch, get_output_patch, spec):
        listunspent_patch.return_value = [
            {'outpoint': bitcoin.core.COutPoint(bytes(str(i), 'utf-8') * 32, i)}
            for i in range(0, len(spec))]

        get_output_patch.side_effect = lambda hash, n: openassets.protocol.TransactionOutput(
            spec[n][0], bitcoin.core.script.CScript(spec[n][1]), spec[n][2], spec[n][3])

    def create_controller(self):
        configuration = unittest.mock.MagicMock()
        configuration.rpc_url = "RPC URL"
        configuration.version_byte = 111
        configuration.p2sh_version_byte = 196
        configuration.dust_limit = 10
        configuration.default_fees = 1000

        return colorcore.operations.Controller(configuration, lambda x: x)

    def assert_response(self, expected, actual):
        expected_json = json.dumps(expected, sort_keys=False)
        actual_json = json.dumps(actual, sort_keys=False)

        self.assertEquals(expected_json, actual_json)