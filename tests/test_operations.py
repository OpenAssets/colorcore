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
import colorcore.program
import json
import openassets.protocol
import unittest
import unittest.mock


class ControllerTests(unittest.TestCase):

    def setUp(self):
        class Expando(object):
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        self.maxDiff = None
        self.addresses = [
            Expando(
                address='moogjqrTWfjkyxLHk9ytzp147EfXVvqLEP',
                script=bitcoin.core.x('76a9145aeb17b8888d04fb47d56ba54e727b88623665b488ac'),
                script_hex='76a9145aeb17b8888d04fb47d56ba54e727b88623665b488ac'
            ),
            Expando(
                address='mpLppfoBWbdF9Y7zeN9sJHcbMzQvAeRqMs',
                script=bitcoin.core.x('76a91460cebc294b5b4ef9c32dc26bb55fff48eeaea81788ac'),
                script_hex='76a91460cebc294b5b4ef9c32dc26bb55fff48eeaea81788ac'
            ),
            Expando(
                address='mr5im8BFT5ycERKHCgZoS7cRN5PewwTR4d',
                script=bitcoin.core.x('76a91473e3b004e54cfad91c40b8fcc65b751c5662287888ac'),
                script_hex='76a91473e3b004e54cfad91c40b8fcc65b751c5662287888ac'
            ),
            Expando(
                address='mkN27mch2UtnRT28k8c5mQPYrW75cYdXUi',
                script=bitcoin.core.x('76a914352813875577109204686b2e687f7ea046235aa588ac'),
                script_hex='76a914352813875577109204686b2e687f7ea046235aa588ac'
            ),
            Expando(
                address='msdzhXTdebVizEJnPrqGWFj5ruFRA8TLxF',
                script=bitcoin.core.x('76a91484f66db046f3e285d6b80bfe195adc114413c1f988ac'),
                script_hex='76a91484f66db046f3e285d6b80bfe195adc114413c1f988ac'
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

    # sendbitcoin

    def test_sendbitcoin_success(self):
        with unittest.mock.patch('bitcoin.rpc.Proxy.listunspent') as listunspent_patch, \
            unittest.mock.patch('openassets.protocol.ColoringEngine.get_output') as get_output_patch:

            self.setup_mocks(listunspent_patch, get_output_patch, [
                (20, self.addresses[0].script, self.assets[0].binary, 30),
                (80, self.addresses[0].script, None, 0),
                (50, self.addresses[1].script, None, 0),
                (50, self.addresses[0].script, None, 0)
            ])

            target = self.create_controller()

            result = target.sendbitcoin(
                address=self.addresses[0].address,
                amount='100',
                to=self.addresses[2].address,
                fees='10',
                mode='unsigned')

            self.assert_response({
                'version': 1,
                'locktime': 0,
                'vin': [
                    self.get_input(1, self.addresses[0]),
                    self.get_input(3, self.addresses[0])
                ],
                'vout': [
                    # Bitcoin change
                    self.get_output(20, 0, self.addresses[0]),
                    # Bitcoins sent
                    self.get_output(100, 1, self.addresses[2])
                ]
            },
            result)

    def test_sendbitcoin_default_fees(self):
        with unittest.mock.patch('bitcoin.rpc.Proxy.listunspent') as listunspent_patch, \
            unittest.mock.patch('openassets.protocol.ColoringEngine.get_output') as get_output_patch:

            self.setup_mocks(listunspent_patch, get_output_patch, [
                (80, self.addresses[0].script, None, 0),
                (50, self.addresses[1].script, None, 0),
                (50, self.addresses[0].script, None, 0)
            ])

            target = self.create_controller()

            result = target.sendbitcoin(
                address=self.addresses[0].address,
                amount='100',
                to=self.addresses[2].address,
                mode='unsigned')

            self.assert_response({
                'version': 1,
                'locktime': 0,
                'vin': [
                    self.get_input(0, self.addresses[0]),
                    self.get_input(2, self.addresses[0])
                ],
                'vout': [
                    # Bitcoin change
                    self.get_output(15, 0, self.addresses[0]),
                    # Bitcoins sent
                    self.get_output(100, 1, self.addresses[2])
                ]
            },
            result)

    # sendasset

    def test_sendasset_success(self):
        with unittest.mock.patch('bitcoin.rpc.Proxy.listunspent') as listunspent_patch, \
            unittest.mock.patch('openassets.protocol.ColoringEngine.get_output') as get_output_patch:

            self.setup_mocks(listunspent_patch, get_output_patch, [
                (10, self.addresses[0].script, self.assets[0].binary, 50),
                (50, self.addresses[1].script, None, 0),
                (40, self.addresses[0].script, None, 0),
                (10, self.addresses[0].script, self.assets[0].binary, 80)
            ])

            target = self.create_controller()

            result = target.sendasset(
                address=self.addresses[0].address,
                asset=self.assets[0].address,
                amount='100',
                to=self.addresses[2].address,
                fees='10',
                mode='unsigned')

            self.assert_response({
                'version': 1,
                'locktime': 0,
                'vin': [
                    self.get_input(0, self.addresses[0]),
                    self.get_input(3, self.addresses[0]),
                    self.get_input(2, self.addresses[0])
                ],
                'vout': [
                    # Marker output
                    self.get_marker_output(0, [100, 30], b''),
                    # Asset sent
                    self.get_output(10, 1, self.addresses[2]),
                    # Asset change
                    self.get_output(10, 2, self.addresses[0]),
                    # Bitcoin change
                    self.get_output(30, 3, self.addresses[0])
                ]
            },
            result)

    # issueasset

    def test_issueasset_success(self):
        with unittest.mock.patch('bitcoin.rpc.Proxy.listunspent') as listunspent_patch, \
            unittest.mock.patch('openassets.protocol.ColoringEngine.get_output') as get_output_patch:

            self.setup_mocks(listunspent_patch, get_output_patch, [
                (5, self.addresses[0].script, None, 0),
                (50, self.addresses[1].script, None, 0),
                (35, self.addresses[0].script, None, 0)
            ])

            target = self.create_controller()

            result = target.issueasset(
                address=self.addresses[0].address,
                amount='100',
                to=self.addresses[2].address,
                metadata='metadata',
                fees='10',
                mode='unsigned')

            self.assert_response({
                'version': 1,
                'locktime': 0,
                'vin': [
                    self.get_input(0, self.addresses[0]),
                    self.get_input(2, self.addresses[0])
                ],
                'vout': [
                    # Asset issued
                    self.get_output(10, 0, self.addresses[2]),
                    # Marker output
                    self.get_marker_output(1, [100], b'metadata'),
                    # Bitcoin change
                    self.get_output(20, 2, self.addresses[0])
                ]
            },
            result)

    # distribute

    def test_distribute_success(self):
        with unittest.mock.patch('bitcoin.rpc.Proxy.listunspent') as listunspent_patch, \
            unittest.mock.patch('bitcoin.rpc.Proxy.getrawtransaction') as getrawtransaction_patch, \
            unittest.mock.patch('openassets.protocol.ColoringEngine.get_output') as get_output_patch:

            self.setup_mocks(listunspent_patch, get_output_patch, [
                (36 + 10 + 15, self.addresses[0].script, None, 0),
                (46 + 10 + 15, self.addresses[0].script, None, 0)
            ])

            def get_raw_transaction(transaction_hash):
                index = int(str(transaction_hash[0:1], 'utf-8'))
                return bitcoin.core.CTransaction(
                    vout=[
                        bitcoin.core.CTxOut(scriptPubKey=bitcoin.core.script.CScript(self.addresses[index + 3].script))
                    ]
                )

            getrawtransaction_patch.side_effect = get_raw_transaction

            target = self.create_controller()

            result = target.distribute(
                address=self.addresses[0].address,
                forward_address=self.addresses[2].address,
                price='20',
                metadata='metadata',
                mode='unsigned')

            self.assert_response([{
                'version': 1,
                'locktime': 0,
                'vin': [self.get_input(0, self.addresses[0])],
                'vout': [
                    # Asset issued
                    self.get_output(10, 0, self.addresses[3]),
                    # Marker output
                    self.get_marker_output(1, [1], b'metadata'),
                    # Forwarded funds
                    self.get_output(20, 2, self.addresses[2]),
                    # Bitcoin change
                    self.get_output(16, 3, self.addresses[3])
                ]
            },
            {
                'version': 1,
                'locktime': 0,
                'vin': [self.get_input(1, self.addresses[0])],
                'vout': [
                    # Asset issued
                    self.get_output(10, 0, self.addresses[4]),
                    # Marker output
                    self.get_marker_output(1, [2], b'metadata'),
                    # Forwarded funds
                    self.get_output(40 + 6, 2, self.addresses[2])
                ]
            }],
            result)

    def test_distribute_preview(self):
        with unittest.mock.patch('bitcoin.rpc.Proxy.listunspent') as listunspent_patch, \
            unittest.mock.patch('bitcoin.rpc.Proxy.getrawtransaction') as getrawtransaction_patch, \
            unittest.mock.patch('openassets.protocol.ColoringEngine.get_output') as get_output_patch:

            self.setup_mocks(listunspent_patch, get_output_patch, [
                (36 + 10 + 15, self.addresses[0].script, None, 0),
                (46 + 10 + 15, self.addresses[0].script, None, 0)
            ])

            def get_raw_transaction(transaction_hash):
                index = int(str(transaction_hash[0:1], 'utf-8'))
                return bitcoin.core.CTransaction(
                    vout=[
                        bitcoin.core.CTxOut(scriptPubKey=bitcoin.core.script.CScript(self.addresses[index + 3].script))
                    ]
                )

            getrawtransaction_patch.side_effect = get_raw_transaction

            target = self.create_controller()

            result = target.distribute(
                address=self.addresses[0].address,
                forward_address=self.addresses[2].address,
                price='20',
                metadata='metadata',
                mode='preview')

            self.assert_response([{
                'from': self.addresses[3].address,
                'received': "0.00000061 BTC",
                'collected': "0.00000020 BTC",
                'sent': "1 Units",
                'transaction': bitcoin.core.b2lx(bytes('0', 'utf-8') * 32)
            },
            {
                'from': self.addresses[4].address,
                'received': "0.00000071 BTC",
                'collected': "0.00000046 BTC",
                'sent': "2 Units",
                'transaction': bitcoin.core.b2lx(bytes('1', 'utf-8') * 32)
            }],
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
        configuration.default_fees = 15

        return colorcore.operations.Controller(
            configuration,
            colorcore.program.Router.get_transaction_formatter('json'))

    def assert_response(self, expected, actual):
        expected_json = json.dumps(expected, indent=4, sort_keys=False)
        actual_json = json.dumps(actual, indent=4, sort_keys=False)

        self.assertEquals(expected_json, actual_json)

    def get_input(self, index, script):
        return {
            'txid': bitcoin.core.b2lx(bytes(str(index), 'utf-8') * 32),
            'vout': index,
            'sequence': 0xffffffff,
            'scriptSig': {
                'hex': script.script_hex
            }
        }

    def get_output(self, value, index, script):
        return {
            'value': value,
            'n': index,
            'scriptPubKey': {'hex': script.script_hex}
        }

    def get_marker_output(self, index, asset_quantities, metadata):
        marker = openassets.protocol.MarkerOutput(asset_quantities, metadata)
        script = marker.build_script(marker.serialize_payload())
        return {
            'value': 0,
            'n': index,
            'scriptPubKey': {'hex': bitcoin.core.b2x(script)}
        }
