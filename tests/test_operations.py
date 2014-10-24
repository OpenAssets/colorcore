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

import asyncio
import bitcoin.core
import bitcoin.core.script
import bitcoin.rpc
import bitcoin.wallet
import collections
import colorcore.operations
import colorcore.providers
import colorcore.routing
import json
import openassets.protocol
import tests.helpers as helpers
import unittest
import unittest.mock


@unittest.mock.patch('openassets.protocol.ColoringEngine.get_output', autospec=True)
class ControllerTests(unittest.TestCase):
    bitcoin.SelectParams('regtest')
    private_key = bitcoin.wallet.CBitcoinSecret('cUgetboAcBhZyma6SvFHhefkw9nVnTpcpswePM5YRv2GqMjrqSgR')

    def setUp(self):
        self.maxDiff = None

        class address(collections.namedtuple('AddressBase', ['address', 'script_hex'])):
            def script(self):
                return bitcoin.core.x(self.script_hex)

        self.addresses = [
            address(
                address='moogjqrTWfjkyxLHk9ytzp147EfXVvqLEP',
                script_hex='76a9145aeb17b8888d04fb47d56ba54e727b88623665b488ac'
            ),
            address(
                address='mpLppfoBWbdF9Y7zeN9sJHcbMzQvAeRqMs',
                script_hex='76a91460cebc294b5b4ef9c32dc26bb55fff48eeaea81788ac'
            ),
            address(
                address='mr5im8BFT5ycERKHCgZoS7cRN5PewwTR4d',
                script_hex='76a91473e3b004e54cfad91c40b8fcc65b751c5662287888ac'
            ),
            address(
                address='mkN27mch2UtnRT28k8c5mQPYrW75cYdXUi',
                script_hex='76a914352813875577109204686b2e687f7ea046235aa588ac'
            ),
            address(
                address='msdzhXTdebVizEJnPrqGWFj5ruFRA8TLxF',
                script_hex='76a91484f66db046f3e285d6b80bfe195adc114413c1f988ac'
            )
        ]
        self.derived = [
            address(
                address='2N7GMwyG7pN4ZoByHX8eArHDHitUFqyuqSr',
                script_hex=None
            ),
            address(
                address='2NBpNRdo28FREjmeKD6Mrxj1NKm8Ufwh35v',
                script_hex=None
            ),
            None,
            address(
                address='',
                script_hex='a9144794a990b714a12081df1506da6693da2dff842287'
            ),
            address(
                address='',
                script_hex='a91465f3d570bfa3f8538d9bad904edc1aa5bb07c22b87'
            )
        ]

        asset = collections.namedtuple('Asset', ['address', 'binary'])
        self.assets = [
            asset(
                address='qhTKTV1YV6VBaRx',
                binary=b'asset1'
            ),
            asset(
                address='qhTKTV1YVE1kJfp',
                binary=b'asset2'
            )
        ]

        self.provider_instance = colorcore.providers.AbstractBlockchainProvider()
        self.provider = unittest.mock.create_autospec(self.provider_instance, instance=True)

    # getbalance

    @helpers.async_test
    def test_getbalance_success(self, *args, loop):
        self.setup_mocks(loop, [
            (20, self.addresses[0].script(), self.assets[0].binary, 30),
            (50, self.addresses[1].script(), self.assets[0].binary, 10),
            (80, self.addresses[0].script(), None, 0)
        ])

        target = self.create_controller()

        result = yield from target.getbalance()

        self.assert_response([
                {
                    'address': self.addresses[0].address,
                    'value': '0.00000100',
                    'assets': [{'asset_address': self.assets[0].address, 'quantity': '30'}],
                    'derived_address': self.derived[0].address
                },
                {
                    'address': self.addresses[1].address,
                    'value': '0.00000050',
                    'assets': [{'asset_address': self.assets[0].address, 'quantity': '10'}],
                    'derived_address': self.derived[1].address
                }
            ],
            result)

    # listunspent

    @helpers.async_test
    def test_listunspent_success(self, *args, loop):
        self.setup_mocks(loop, [
            (20, self.addresses[0].script(), self.assets[0].binary, 30),
            (50, self.addresses[1].script(), self.assets[1].binary, 10),
            (80, self.addresses[0].script(), None, 0)
        ])

        target = self.create_controller()

        result = yield from target.listunspent()

        self.assert_response([
                {
                    'txid': '30' * 32,
                    'vout': 0,
                    'address': self.addresses[0].address,
                    'script': self.addresses[0].script_hex,
                    'amount': '0.00000020',
                    'confirmations': 0,
                    'asset_address': self.assets[0].address,
                    'asset_quantity': '30'
                },
                {
                    'txid': '31' * 32,
                    'vout': 1,
                    'address': self.addresses[1].address,
                    'script': self.addresses[1].script_hex,
                    'amount': '0.00000050',
                    'confirmations': 1,
                    'asset_address': self.assets[1].address,
                    'asset_quantity': '10'
                },
                {
                    'txid': '32' * 32,
                    'vout': 2,
                    'address': self.addresses[0].address,
                    'script': self.addresses[0].script_hex,
                    'amount': '0.00000080',
                    'confirmations': 2,
                    'asset_address': None,
                    'asset_quantity': '0'
                }
            ],
            result)

    # sendbitcoin

    @helpers.async_test
    def test_sendbitcoin_success(self, *args, loop):
        result = yield from self._setup_sendbitcoin_test('unsigned', 'json', loop)

        self.assert_response({
            'version': 1,
            'locktime': 0,
            'vin': [
                self.get_input(1, self.addresses[0]),
                self.get_input(2, self.addresses[0])
            ],
            'vout': [
                # Bitcoin change
                self.get_output(20, 0, self.addresses[0]),
                # Bitcoins sent
                self.get_output(100, 1, self.addresses[2])
            ]
        },
        result)

    @helpers.async_test
    def test_sendbitcoin_signed_success(self, *args, loop):
        self.loop = loop
        self.set_get_private_key_mock()
        result = yield from self._setup_sendbitcoin_test('signed', 'json', loop)

        self.assertEqual(1, self.provider.get_private_key.call_count)
        self.assertEqual(2, len(result['vin']))
        self.assertEqual(2, len(result['vout']))

    @helpers.async_test
    def test_sendbitcoin_broadcast(self, *args, loop):
        self.loop = loop
        self.set_get_private_key_mock()
        self.set_send_transaction_mock(b'transaction ID')
        result = yield from self._setup_sendbitcoin_test('broadcast', 'json', loop)

        self.assertEqual(1, self.provider.get_private_key.call_count)
        self.assertEqual(1, self.provider.send_transaction.call_count)
        self.assertEqual(bitcoin.core.b2lx(b'transaction ID'), result)

    @helpers.async_test
    def test_sendbitcoin_raw_unsigned(self, *args, loop):
        result = yield from self._setup_sendbitcoin_test('unsigned', 'raw', loop)

        self.assertEqual(
            True,
            result.startswith('01000000023131313131313131313131313131313131313131313131313131313131313131'))
        self.assertIn(self.addresses[0].script_hex, result)
        self.assertIn(self.addresses[2].script_hex, result)
        self.assertEqual(420, len(result))

    @helpers.async_test
    def test_sendbitcoin_raw_broadcast(self, *args, loop):
        self.loop = loop
        self.set_get_private_key_mock()
        self.set_send_transaction_mock(b'transaction ID')

        result = yield from self._setup_sendbitcoin_test('broadcast', 'raw', loop)

        self.assertEqual(1, self.provider.get_private_key.call_count)
        self.assertEqual(1, self.provider.send_transaction.call_count)
        self.assertEqual(bitcoin.core.b2lx(b'transaction ID'), result)

    @helpers.async_test
    def test_sendbitcoin_default_fees(self, *args, loop):
        self.setup_mocks(loop, [
            (80, self.addresses[0].script(), None, 0),
            (50, self.addresses[0].script(), None, 0)
        ])

        target = self.create_controller()

        result = yield from target.sendbitcoin(
            address=self.addresses[0].address,
            amount='100',
            to=self.addresses[2].address,
            mode='unsigned')

        self.assert_response({
            'version': 1,
            'locktime': 0,
            'vin': [
                self.get_input(0, self.addresses[0]),
                self.get_input(1, self.addresses[0])
            ],
            'vout': [
                # Bitcoin change
                self.get_output(15, 0, self.addresses[0]),
                # Bitcoins sent
                self.get_output(100, 1, self.addresses[2])
            ]
        },
        result)

    @helpers.async_test
    def test_invalid_fees(self, *args, loop):
        self.setup_mocks(loop, [
            (80, self.addresses[0].script(), None, 0),
            (50, self.addresses[1].script(), None, 0),
            (50, self.addresses[0].script(), None, 0)
        ])

        target = self.create_controller()

        yield from helpers.assert_coroutine_raises(
            self,
            colorcore.routing.ControllerError,
            target.sendbitcoin,
            address=self.addresses[0].address,
            amount='100',
            to=self.addresses[2].address,
            fees='10a',
            mode='unsigned')

    @asyncio.coroutine
    def _setup_sendbitcoin_test(self, mode, format, loop):
        self.setup_mocks(loop, [
            (20, self.addresses[0].script(), self.assets[0].binary, 30),
            (80, self.addresses[0].script(), None, 0),
            (50, self.addresses[0].script(), None, 0)
        ])

        target = self.create_controller(format)

        result = yield from target.sendbitcoin(
            address=self.addresses[0].address,
            amount='100',
            to=self.addresses[2].address,
            fees='10',
            mode=mode)

        return result

    # sendasset

    @helpers.async_test
    def test_sendasset_success(self, *args, loop):
        self.setup_mocks(loop, [
            (10, self.addresses[0].script(), self.assets[0].binary, 50),
            (40, self.addresses[0].script(), None, 0),
            (10, self.addresses[0].script(), self.assets[0].binary, 80)
        ])

        target = self.create_controller()

        result = yield from target.sendasset(
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
                self.get_input(2, self.addresses[0]),
                self.get_input(1, self.addresses[0])
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

    @helpers.async_test
    def test_issueasset_success(self, *args, loop):
        self.setup_mocks(loop, [
            (5, self.addresses[0].script(), None, 0),
            (35, self.addresses[0].script(), None, 0)
        ])

        target = self.create_controller()

        result = yield from target.issueasset(
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
                self.get_input(1, self.addresses[0])
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

    @helpers.async_test
    def test_distribute_success(self, *args, loop):
        self.setup_mocks(loop, [
            (36 + 10 + 15, self.addresses[0].script(), None, 0),
            (46 + 10 + 15, self.addresses[0].script(), None, 0)
        ])

        self.set_get_transaction_mock(self._distribute_get_raw_transaction)

        target = self.create_controller()

        result = yield from target.distribute(
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
                self.get_output(10, 0, self.derived[3]),
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
                self.get_output(10, 0, self.derived[4]),
                # Marker output
                self.get_marker_output(1, [2], b'metadata'),
                # Forwarded funds
                self.get_output(40 + 6, 2, self.addresses[2])
            ]
        }],
        result)

    @helpers.async_test
    def test_distribute_preview(self, *args, loop):
        self.setup_mocks(loop, [
            (36 + 10 + 15, self.addresses[0].script(), None, 0),
            (46 + 10 + 15, self.addresses[0].script(), None, 0)
        ])

        self.set_get_transaction_mock(self._distribute_get_raw_transaction)

        target = self.create_controller()

        result = yield from target.distribute(
            address=self.addresses[0].address,
            forward_address=self.addresses[2].address,
            price='20',
            metadata='metadata',
            mode='preview')

        self.assert_response([{
            'from': self.addresses[3].address,
            'received': '0.00000061 BTC',
            'collected': '0.00000020 BTC',
            'sent': '1 Units',
            'transaction': bitcoin.core.b2lx(bytes('0', 'utf-8') * 32)
        },
        {
            'from': self.addresses[4].address,
            'received': '0.00000071 BTC',
            'collected': '0.00000046 BTC',
            'sent': '2 Units',
            'transaction': bitcoin.core.b2lx(bytes('1', 'utf-8') * 32)
        }],
        result)

    @helpers.async_test
    def test_distribute_invalid_price(self, *args, loop):
        target = self.create_controller()

        yield from helpers.assert_coroutine_raises(
            self,
            colorcore.routing.ControllerError,
            target.distribute,
            address=self.addresses[0].address,
            forward_address=self.addresses[2].address,
            price='20.2r',
            metadata='metadata',
            mode='preview')

    def _distribute_get_raw_transaction(self, transaction_hash):
        index = int(str(transaction_hash[0:1], 'utf-8'))
        return self.completed(bitcoin.core.CTransaction(
            vout=[
                bitcoin.core.CTxOut(scriptPubKey=bitcoin.core.script.CScript(self.addresses[index + 3].script()))
            ]
        ))

    # Test helpers

    def setup_mocks(self, loop, spec):
        self.loop = loop

        self.provider.list_unspent = unittest.mock.create_autospec(self.provider_instance.list_unspent)
        self.provider.list_unspent.return_value = self.completed([
                {'outpoint': bitcoin.core.COutPoint(bytes(str(i), 'utf-8') * 32, i), 'confirmations': i}
                for i in range(0, len(spec))])

        def get_output(_, hash, n):
            return self.completed(openassets.protocol.TransactionOutput(
                spec[n][0], bitcoin.core.script.CScript(spec[n][1]), spec[n][2], spec[n][3]))

        openassets.protocol.ColoringEngine.get_output.side_effect = get_output

    def set_get_transaction_mock(self, side_effect):
        self.provider.get_transaction = unittest.mock.create_autospec(self.provider_instance.get_transaction)
        self.provider.get_transaction.side_effect = side_effect

    def set_get_private_key_mock(self):
        self.provider.get_private_key = unittest.mock.create_autospec(self.provider_instance.get_private_key)
        self.provider.get_private_key.return_value = self.completed(self.private_key)

    def set_send_transaction_mock(self, return_value):
        self.provider.send_transaction = unittest.mock.create_autospec(self.provider_instance.send_transaction)
        self.provider.send_transaction.return_value = self.completed(return_value)

    def create_controller(self, format='json'):
        configuration = unittest.mock.MagicMock()
        configuration.rpc_url = 'RPC URL'
        configuration.version_byte = 111
        configuration.p2sh_version_byte = 196
        configuration.dust_limit = 10
        configuration.default_fees = 15
        configuration.create_blockchain_provider = unittest.mock.Mock(
            spec=colorcore.routing.Configuration.create_blockchain_provider,
            return_value=self.provider)

        class MockCache(openassets.protocol.OutputCache):
            @asyncio.coroutine
            def commit(self):
                pass

        return colorcore.operations.Controller(
            configuration,
            MockCache,
            colorcore.routing.Router.get_transaction_formatter(format),
            None)

    def assert_response(self, expected, actual):
        expected_json = json.dumps(expected, indent=4, sort_keys=False)
        actual_json = json.dumps(actual, indent=4, sort_keys=False)

        self.assertEqual(expected_json, actual_json)

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

    def completed(self, value):
        future = asyncio.Future(loop=self.loop)
        future.set_result(value)
        return future


class ConvertTests(unittest.TestCase):

    def test_base58_to_script_success(self):
        target = colorcore.operations.Convert(0, 5)

        result = target.base58_to_script('1AaaBxiLVzo1xZSFpAw3Zm9YBYAYQgQuuU')
        self.assertEqual(bitcoin.core.x('76a914' + '691290451961ad74e177bf44f32d9e2fe7454ee6' + '88ac'), result)

        result = target.base58_to_script('36hBrMeUfevFPZdY2iYSHVaP9jdLd9Np4R')
        self.assertEqual(bitcoin.core.x('a914' + '36e0ea8e93eaa0285d641305f4c81e563aa570a2' + '87'), result)

    def test_base58_to_script_invalid_version(self):
        target = colorcore.operations.Convert(0, 5)

        self.assertRaises(
            colorcore.routing.ControllerError,
            target.base58_to_script,
            'mr5im8BFT5ycERKHCgZoS7cRN5PewwTR4d')

    def test_base58_to_asset_address_success(self):
         target = colorcore.operations.Convert(0, 5)

         result = target.base58_to_asset_address('36hBrMeUfevFPZdY2iYSHVaP9jdLd9Np4R')

         self.assertEqual(bitcoin.core.x('36e0ea8e93eaa0285d641305f4c81e563aa570a2'), result)

    def test_base58_to_asset_address_invalid_version(self):
         target = colorcore.operations.Convert(0, 5)

         self.assertRaises(
             colorcore.routing.ControllerError,
             target.base58_to_asset_address,
             '1AaaBxiLVzo1xZSFpAw3Zm9YBYAYQgQuuU')

    def test_script_to_base58_success(self):
         target = colorcore.operations.Convert(0, 5)

         result = target.script_to_base58(
             bitcoin.core.x('76a914' + '691290451961ad74e177bf44f32d9e2fe7454ee6' + '88ac'))

         self.assertEqual('1AaaBxiLVzo1xZSFpAw3Zm9YBYAYQgQuuU', result)

    def test_script_to_base58_unknown_script(self):
         target = colorcore.operations.Convert(0, 5)

         result = target.script_to_base58(
             bitcoin.core.x('000000' + '691290451961ad74e177bf44f32d9e2fe7454ee6' + '88ac'))

         self.assertEqual('Unknown script', result)

    def test_script_to_base58_invalid_script(self):
         target = colorcore.operations.Convert(0, 5)

         result = target.script_to_base58(
             bitcoin.core.x('76a914' + '691290'))

         self.assertEqual('Invalid script', result)

    def test_asset_address_to_base58(self):
         target = colorcore.operations.Convert(0, 5)

         result = target.asset_address_to_base58(
             bitcoin.core.x('36e0ea8e93eaa0285d641305f4c81e563aa570a2'))

         self.assertEqual('36hBrMeUfevFPZdY2iYSHVaP9jdLd9Np4R', result)
