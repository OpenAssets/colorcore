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
import colorcore.providers
import colorcore.routing
import configparser
import io
import openassets.transactions
import unittest
import unittest.mock


class RouterTests(unittest.TestCase):

    def test_parse_call(self):
        router, _ = self.create_router()
        router.parse(['test_operation', 'val1', 'val2'])

        self.assertEqual('"val1val2default"\n', self.output.getvalue())

    def test_raise_controller_error(self):
        router, _ = self.create_router()
        router.parse(['test_raise_controller_error'])

        self.assertEqual('Error: Test error\n', self.output.getvalue())

    def test_raise_transaction_builder_error(self):
        router, _ = self.create_router()
        router.parse(['test_raise_transaction_builder_error'])

        self.assertEqual('Error: InsufficientAssetQuantityError\n', self.output.getvalue())

    @unittest.mock.patch('argparse.ArgumentParser.exit', autospec=True)
    def test_parse_help(self, exit_mock):
        router, _ = self.create_router()
        with unittest.mock.patch('argparse._sys', stdout=self.output, autospec=True):
            exit_mock.side_effect = SystemError

            self.assertRaises(SystemError, router.parse, ['test_operation', '--help'])
            self.assertIn('help1', self.output.getvalue())
            self.assertIn('help2', self.output.getvalue())
            self.assertIn('help3', self.output.getvalue())

    def test_parse_server(self):
        router, event_loop_mock = self.create_router()
        run_forever_mock_value = asyncio.Future(loop=event_loop_mock)
        run_forever_mock_value.set_result(None)
        event_loop_mock.run_forever = unittest.mock.Mock(
            spec=event_loop_mock.create_server, return_value=run_forever_mock_value)

        self.configuration.rpc_enabled = True
        self.configuration.rpc_port = 8080

        router.parse(['server'])

        self.assertIn('Starting RPC server on port 8080...\n', self.output.getvalue())
        self.assertEqual(1, event_loop_mock.create_server.call_count)

    def test_parse_server_not_enabled(self):
        router, event_loop_mock = self.create_router()
        self.configuration.rpc_enabled = False
        self.configuration.rpc_port = 8080

        router.parse(['server'])

        self.assertIn('Error: RPC must be enabled in the configuration.\n', self.output.getvalue())
        self.assertEqual(0, event_loop_mock.create_server.call_count)

    def create_router(self):
        class MockController(object):
            def __init__(self, configuration, cache_factory, *args):
                pass

            @asyncio.coroutine
            def test_operation(self, parameter1: 'help1', parameter2: 'help2', parameter3: 'help3'='default'):
                """function help"""
                return parameter1 + parameter2 + parameter3

            @asyncio.coroutine
            def test_raise_controller_error(self):
                """raise 1"""
                raise colorcore.routing.ControllerError('Test error')

            @asyncio.coroutine
            def test_raise_transaction_builder_error(self):
                """raise 2"""
                raise openassets.transactions.InsufficientAssetQuantityError

        self.configuration = unittest.mock.Mock()
        self.output = io.StringIO()

        event_loop = asyncio.new_event_loop()

        create_server_return_value = asyncio.Future(loop=event_loop)
        create_server_return_value.set_result(None)
        event_loop.create_server = unittest.mock.Mock(
            spec=event_loop.create_server, return_value=create_server_return_value)
        return (
            colorcore.routing.Router(MockController, self.output, object, self.configuration, event_loop),
            event_loop)


class ConfigurationTests(unittest.TestCase):

    def test_init(self):
        config = configparser.ConfigParser()
        config.add_section('environment')
        config.add_section('cache')
        env = config['environment']
        env['version-byte'] = '1'
        env['p2sh-version-byte'] = '20'
        env['asset-version-byte'] = '24'
        env['dust-limit'] = '100'
        env['default-fees'] = '300'
        config['cache']['path'] = 'test_path'

        target = colorcore.routing.Configuration(config)

        self.assertEqual(None, target.blockchain_provider)
        self.assertEqual(1, target.version_byte)
        self.assertEqual(20, target.p2sh_byte)
        self.assertEqual(24, target.asset_byte)
        self.assertEqual(100, target.dust_limit)
        self.assertEqual(300, target.default_fees)
        self.assertEqual('test_path', target.cache_path)
        self.assertEqual(False, target.rpc_enabled)

    @unittest.mock.patch('colorcore.routing.Configuration.__init__', autospec=True)
    def test_create_blockchain_provider(self, init_mock):
        init_mock.return_value = None

        # chain.com
        configuration = colorcore.routing.Configuration(None)
        configuration.blockchain_provider = 'chain.com'
        configuration.parser = {'chain.com': {'base-url': '1', 'api-key-id': '2', 'secret': '3'}}

        result = configuration.create_blockchain_provider(None)

        self.assertIsInstance(result, colorcore.providers.ChainApiProvider)
        self.assertIsNone(result._fallback_provider)

        # chain.com + Bitcoind
        configuration = colorcore.routing.Configuration(None)
        configuration.blockchain_provider = 'chain.com+bitcoind'
        configuration.parser = {
            'chain.com': {'base-url': '1', 'api-key-id': '2', 'secret': '3'},
            'bitcoind': {'rpcurl': 'url'}
        }

        result = configuration.create_blockchain_provider(None)

        self.assertIsInstance(result, colorcore.providers.ChainApiProvider)
        self.assertIsNotNone(result._fallback_provider)

        # Bitcoind
        configuration = colorcore.routing.Configuration(None)
        configuration.blockchain_provider = 'bitcoind'
        configuration.parser = {'bitcoind': {'rpcurl': 'url'}}

        result = configuration.create_blockchain_provider(None)

        self.assertIsInstance(result, colorcore.providers.BitcoinCoreProvider)