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
import bitcoin.base58
import bitcoin.core
import bitcoin.core.script
import bitcoin.rpc
import inspect
import itertools
import openassets.protocol
import openassets.transactions
import prettytable

def controller(configuration):
    parser = _Router("Colorcore: The colored coins Open Asset client")

    # Commands

    @parser.add
    def getbalance(
            address: "Obtain the balance of this address only"=None,
            minconf: "The minimum number of confirmations (inclusive)"="1",
            maxconf: "The maximum number of confirmations (inclusive)"="9999999"
    ):
        """Obtains the balance of the wallet or an address"""
        client = create_client()
        result = client.listunspent(as_int(minconf), as_int(maxconf), [address] if address else None)
        engine = openassets.protocol.ColoringEngine(client.getrawtransaction, openassets.protocol.OutputCache())
        colored_outputs = [engine.get_output(item["outpoint"].hash, item["outpoint"].n) for item in result]

        table = prettytable.PrettyTable(["Address", "Asset", "Quantity"])

        for script, group in itertools.groupby(colored_outputs, lambda output: output.scriptPubKey):
            script_outputs = list(group)
            total_value = sum([item.nValue for item in script_outputs]) / bitcoin.core.COIN
            base58 = get_p2a_address_from_script(script)
            table.add_row([base58, "Bitcoin", str(total_value)])

            for asset_address, outputs in itertools.groupby(script_outputs, lambda output: output.asset_address):
                if asset_address is not None:
                    total_quantity = sum([item.asset_quantity for item in outputs])
                    table.add_row([base58, get_base85_color_address(asset_address), str(total_quantity)])

        print(table)

    @parser.add
    def sendbitcoin(
        address: "The address to send the bitcoins from",
        amount: "The amount of satoshis to send",
        to: "The address to send the bitcoins to",
        fees: "The fess in satoshis for the transaction" = None,
        mode: """'broadcast' (default) for signing and broadcasting the transaction,
            'signed' for signing the transaction without broadcasting,
            'unsigned' for getting the raw unsigned transaction without broadcasting"""="broadcast"
    ):
        """Creates a transaction for sending bitcoins from an address to another."""
        client = create_client()
        builder = openassets.transactions.TransactionBuilder(configuration.dust_limit)
        colored_outputs = get_unspent_outputs(client, address)

        if fees is None:
            fees = configuration.default_fees
        else:
            fees = as_int(fees)

        transaction = builder.transfer_bitcoin(
            colored_outputs,
            get_script_from_p2a_address(address),
            get_script_from_p2a_address(to),
            as_int(amount),
            fees)

        result = process_transaction(client, transaction, mode)

        print(result)

    # Helpers

    def create_client():
        return bitcoin.rpc.Proxy(configuration.rpc_url)

    def get_unspent_outputs(client, address):
        engine = openassets.protocol.ColoringEngine(client.getrawtransaction, openassets.protocol.OutputCache())
        result = client.listunspent(addrs=[address] if address else None)
        return [
            openassets.transactions.SpendableOutput(
            bitcoin.core.COutPoint(item['outpoint'].hash, item['outpoint'].n),
            engine.get_output(item['outpoint'].hash, item['outpoint'].n)) for item in result]

    def process_transaction(client, transaction, mode):
        if mode == 'broadcast' or mode == 'signed':
            # Sign the transaction
            signed_transaction = client.signrawtransaction(transaction)
            if not signed_transaction['complete']:
                raise CommandLineError("Could not sign the transaction.")

            if mode == 'broadcast':
                result = client.sendrawtransaction(signed_transaction['tx'])
                return bitcoin.core.b2lx(result)
            else:
                return bitcoin.core.b2x(signed_transaction['tx'].serialize())
        else:
            # Return the transaction in raw format as a hex string
            return bitcoin.core.b2x(transaction.serialize())

    def as_int(value):
        try:
            return int(value)
        except ValueError:
            raise CommandLineError("Value '{}' is not a valid integer.".format(value))

    def get_p2a_address_from_script(script):
        script_object = bitcoin.core.CScript(script)
        try:
            opcodes = list(script_object.raw_iter())
        except bitcoin.core.script.CScriptInvalidError:
            return "Invalid script"

        if len(opcodes) == 5 and opcodes[0][0] == 0x76 and opcodes[1][0] == 0xA9 \
            and opcodes[3][0] == 0x88 and opcodes[4][0] == 0xac:
            opcode, data, sop_idx = opcodes[2]
            return str(bitcoin.base58.CBase58Data.from_bytes(data, configuration.version_byte))

        return "Unknown script"

    def get_script_from_p2a_address(base58_address):
        address_bytes = bitcoin.base58.CBase58Data(base58_address).to_bytes()
        return bytes([0x76, 0xA9]) + bitcoin.core.script.CScriptOp.encode_op_pushdata(address_bytes) \
            + bytes([0x88, 0xac])

    def get_base85_color_address(asset_address):
        return str(bitcoin.base58.CBase58Data.from_bytes(asset_address, configuration.p2sh_version_byte))

    parser.parse()
    return parser


class _Router:
    """Infrastructure for routing command line calls to the right function."""

    def __init__(self, description=None):
        self._parser = argparse.ArgumentParser(description=description)
        self._subparsers = self._parser.add_subparsers()

    def add(self, func):
        subparser = self._subparsers.add_parser(func.__name__, help=func.__doc__)
        subparser.set_defaults(_func=self.filter_errors(func))
        func_signature = inspect.signature(func)
        for name, arg in func_signature.parameters.items():
            if arg.kind != arg.POSITIONAL_OR_KEYWORD:
                continue
            arg_help = arg.annotation if arg.annotation is not arg.empty else None
            if arg.default is arg.empty:
                # a positional argument
                subparser.add_argument(name, help=arg_help)
            else:
                # an optional argument
                subparser.add_argument("--" + name,
                    help=arg_help,
                    nargs="?",
                    default=arg.default)
        return func

    def parse(self):
        args = vars(self._parser.parse_args())
        func = args.pop("_func", self._parser.print_usage)
        func(**args)

    @staticmethod
    def filter_errors(function):
        def decorator(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except CommandLineError as error:
                print("Error: {}".format(str(error)))

        return decorator


class CommandLineError(Exception):
    pass