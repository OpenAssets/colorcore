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
import colorcore.operations
import http.server
import inspect
import json
import openassets.transactions
import re
import sys
import urllib.parse


class Program(object):

    def execute(self):
        configuration = Configuration()
        router = Router(
            colorcore.operations.Controller,
            sys.stdout,
            configuration,
            "Colorcore: The Open Assets client for colored coins")
        router.parse(sys.argv[1:])


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

        if 'rpc' in parser:
            self.rpc_port = int(parser['rpc']['port'])
            self.rpc_enabled = True
        else:
            self.rpc_enabled = False


class RpcServer(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        self.error(101, 'Requests must be POST')

    def do_POST(self):
        try:
            url = re.search('^/(?P<operation>\w+)$', self.path)
            if url is None:
                return self.error(102, 'The request path is invalid')

            operation_name = url.group('operation')
            operation = getattr(self.server.controller, operation_name, None)

            if operation_name == "" or operation_name[0] == "_" or operation is None:
                return self.error(103, 'The operation name {name} is invalid'.format(name=operation_name))

            length = int(self.headers['content-length'])

            post_vars = {}
            for key, value in urllib.parse.parse_qs(self.rfile.read(length), keep_blank_values=1).items():
                post_vars[str(key, 'utf-8')] = str(value[0], 'utf-8')

            tx_parser = Router.get_transaction_formatter(post_vars.pop('txformat', 'json'))

            controller = self.server.controller(self.server.configuration, tx_parser)

            try:
                result = operation(controller, **post_vars)
            except TypeError:
                return self.error(104, 'Invalid parameters provided')
            except ControllerError as error:
                return self.error(201, str(error))
            except openassets.transactions.TransactionBuilderError as error:
                return self.error(301, type(error).__name__)

            self.set_headers(200)
            self.json_response(result)
        except:
            self.set_headers(500)
            self.json_response({'error': {'code': 0, 'message': 'Internal server error'}})

    def set_headers(self, code):
        self.server_version = 'Colorcore/' + colorcore.__version__
        self.sys_version = ""
        self.send_response(code)
        self.send_header('Content-Type', 'text/json')
        self.end_headers()

    def error(self, code, message):
        self.set_headers(400)
        self.json_response({'error': {'code': code, 'message': message}})

    def json_response(self, data):
        self.wfile.write(bytes(json.dumps(data, indent=4, separators=(',', ': ')), "utf-8"))


class Router:
    """Infrastructure for routing command line calls to the right function."""

    extra_parameters = [
        ('txformat', 'Format of transactions if a transaction is returned ("raw" or "json")', 'json')
    ]

    def __init__(self, controller, output, configuration, description=None):
        self.controller = controller
        self.configuration = configuration
        self.output = output
        self._parser = argparse.ArgumentParser(description=description)
        subparsers = self._parser.add_subparsers()

        subparser = subparsers.add_parser("server", help="Starts the Colorcore JSON/RPC server.")
        subparser.set_defaults(_func=self.run_rpc_server)

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
            controller = self.controller(configuration, self.get_transaction_formatter(txformat))

            try:
                result = function(controller, *args, **kwargs)

                self.output.write(json.dumps(result, indent=4, separators=(',', ': '), sort_keys=False))

            except ControllerError as error:
                self.output.write("Error: {}".format(str(error)))
            except openassets.transactions.TransactionBuilderError as error:
                self.output.write("Error: {}".format(type(error).__name__))

        return decorator

    @staticmethod
    def get_transaction_formatter(format):
        if format == "json":
            def get_transaction_json(transaction):
                if isinstance(transaction, bitcoin.core.CTransaction):
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
                else:
                    return transaction
        else:
            def get_transaction_json(transaction):
                if isinstance(transaction, bitcoin.core.CTransaction):
                    return bitcoin.core.b2x(transaction.serialize())
                else:
                    return transaction

        return get_transaction_json

    def run_rpc_server(self):
        if not self.configuration.rpc_enabled:
            self.output.write("Error: RPC must be enabled in the configuration.")
            return

        self.output.write("Starting RPC server on port {port}...".format(port=self.configuration.rpc_port))

        httpd = http.server.HTTPServer(('', self.configuration.rpc_port), RpcServer)
        httpd.controller = self.controller
        httpd.configuration = self.configuration
        httpd.serve_forever()

    def parse(self, args):
        args = vars(self._parser.parse_args(args))
        func = args.pop("_func", self._parser.print_usage)
        func(**args)


class ControllerError(Exception):
    pass