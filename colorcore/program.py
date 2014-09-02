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

import argparse
import bitcoin.core
import configparser
import itertools
import colorcore.operations
import inspect
import json


class Program(object):

    def execute(self):
        self.configuration = Configuration()
        self.router = Router(colorcore.operations.Controller, self.configuration)
        self.router.parse()


class Configuration():
    def __init__(self):
        parser = configparser.ConfigParser()
        config_path = "config.ini"
        parser.read(config_path)

        self.rpc_url = parser["bitcoind"]["rpcurl"]
        self.version_byte = int(parser["environment"]["version-byte"])
        self.p2sh_version_byte = int(parser["environment"]["p2sh-version-byte"])
        self.dust_limit = int(parser["environment"]["dust-limit"])
        self.default_fees = int(parser["environment"]["default-fees"])


class Router:
    """Infrastructure for routing command line calls to the right function."""

    extra_parameters = [
        ('txformat', 'Format of transactions if a transaction is returned ("raw" or "json")', 'json')
    ]

    def __init__(self, controller, configuration, description=None):
        self.controller = controller
        self._parser = argparse.ArgumentParser(description=description)
        subparsers = self._parser.add_subparsers()

        for name, function in inspect.getmembers(self.controller, predicate=inspect.isfunction):
            # Skip non-public functions
            if name[0] != "_":
                subparser = subparsers.add_parser(name, help=function.__doc__)
                self.create_subparser(subparser, configuration, function)

    def create_subparser(self, subparser, configuration, func):
        subparser.set_defaults(_func=self.execute_operation(configuration, func))
        func_signature = inspect.signature(func)
        for name, arg in func_signature.parameters.items():
            if name == "self":
                continue
            if arg.kind != arg.POSITIONAL_OR_KEYWORD:
                continue

            arg_help = arg.annotation if arg.annotation is not arg.empty else None
            if arg.default is arg.empty:
                # a positional argument
                subparser.add_argument(name, help=arg_help)
            else:
                # an optional argument
                subparser.add_argument("--" + name, help=arg_help, nargs="?", default=arg.default)

        for name, help, default in self.extra_parameters:
            subparser.add_argument("--" + name, help=help, nargs="?", default=default)

    def execute_operation(self, configuration, function):
        def decorator(*args, txformat, **kwargs):
            if txformat == "json":
                tx_parser = self.get_transaction_json
            else:
                tx_parser = lambda transaction: bitcoin.core.b2x(transaction.serialize())

            controller = self.controller(configuration, tx_parser)

            try:
                result = function(controller, *args, **kwargs)

                print(json.dumps(result, indent=4, separators=(',', ': ')))

            except ControllerError as error:
                print("Error: {}".format(str(error)))

        return decorator

    @staticmethod
    def get_transaction_json(transaction):
        return {
            'version': transaction.nVersion,
            'locktime': transaction.nLockTime,
            'vin': [{
                    'txid': bitcoin.core.b2lx(input.prevout.hash),
                    'vout': input.prevout.n,
                    'sequence': input.nSequence,
                    'scriptSig': {
                        'hex': bitcoin.core.b2x(bytes(input.scriptSig))
                    }
                }
                for input in transaction.vin],
            'vout': [{
                'value': output.nValue,
                'n': index,
                'scriptPubKey': {
                    'hex': bitcoin.core.b2x(bytes(output.scriptPubKey))
                }
            }
            for index, output in enumerate(transaction.vout)]
        }

    def parse(self):
        args = vars(self._parser.parse_args())
        func = args.pop("_func", self._parser.print_usage)
        func(**args)


class ControllerError(Exception):
    pass