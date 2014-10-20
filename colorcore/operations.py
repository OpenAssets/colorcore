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
import bitcoin.base58
import bitcoin.core
import bitcoin.core.serialize
import bitcoin.core.script
import bitcoin.rpc
import colorcore.routing
import decimal
import itertools
import math
import openassets.protocol
import openassets.transactions


class Controller(object):
    """Contains all operations provided by Colorcore."""

    def __init__(self, configuration, cache_factory, tx_parser, event_loop):
        self.configuration = configuration
        self.tx_parser = tx_parser
        self.cache_factory = cache_factory
        self.event_loop = event_loop
        self.convert = Convert(configuration.version_byte, configuration.p2sh_version_byte)

    @asyncio.coroutine
    def getbalance(self,
        address: "Obtain the balance of this address only, or all addresses if unspecified"=None,
        minconf: "The minimum number of confirmations (inclusive)"='1',
        maxconf: "The maximum number of confirmations (inclusive)"='9999999'
    ):
        """Obtains the balance of the wallet or an address."""
        client = self._create_client()
        unspent_outputs = yield from self._get_unspent_outputs(
            client, address, self._as_int(minconf), self._as_int(maxconf))
        colored_outputs = [output.output for output in unspent_outputs]

        sorted_outputs = sorted(colored_outputs, key=lambda output: output.script)

        table = []
        for script, group in itertools.groupby(sorted_outputs, lambda output: output.script):
            script_outputs = list(group)
            total_value = self.convert.to_coin(sum([item.value for item in script_outputs]))
            base58 = self.convert.script_to_base58(script)

            group_details = {
                'address': base58,
                'value': total_value,
                'assets': []
            }

            table.append(group_details)

            sorted_script_outputs = sorted(
                [item for item in script_outputs if item.asset_address],
                key=lambda output: output.asset_address)

            for asset_address, outputs in itertools.groupby(sorted_script_outputs, lambda output: output.asset_address):
                total_quantity = sum([item.asset_quantity for item in outputs])
                group_details['assets'].append({
                    'asset_address': self.convert.asset_address_to_base58(asset_address),
                    'quantity': str(total_quantity)
                })

        return table

    @asyncio.coroutine
    def listunspent(self,
        address: "Obtain the balance of this address only, or all addresses if unspecified"=None,
        minconf: "The minimum number of confirmations (inclusive)"='1',
        maxconf: "The maximum number of confirmations (inclusive)"='9999999'
    ):
        """Returns an array of unspent transaction outputs augmented with the asset address and quantity of
        each output."""
        client = self._create_client()
        unspent_outputs = yield from self._get_unspent_outputs(
            client, address, self._as_int(minconf), self._as_int(maxconf))

        table = []
        for output in unspent_outputs:
            table.append({
                'txid': bitcoin.core.b2lx(output.out_point.hash),
                'vout': output.out_point.n,
                'address': self.convert.script_to_base58(output.output.script),
                'script': bitcoin.core.b2x(output.output.script),
                'amount': self.convert.to_coin(output.output.value),
                'confirmations': output.confirmations,
                'asset_address':
                    None if output.output.asset_address is None
                    else self.convert.asset_address_to_base58(output.output.asset_address),
                'asset_quantity': str(output.output.asset_quantity)
            })

        return table

    @asyncio.coroutine
    def sendbitcoin(self,
        address: "The address to send the bitcoins from",
        amount: "The amount of satoshis to send",
        to: "The address to send the bitcoins to",
        fees: "The fess in satoshis for the transaction"=None,
        mode: """'broadcast' (default) for signing and broadcasting the transaction,
            'signed' for signing the transaction without broadcasting,
            'unsigned' for getting the raw unsigned transaction without broadcasting"""='broadcast'
    ):
        """Creates a transaction for sending bitcoins from an address to another."""
        client = self._create_client()
        builder = openassets.transactions.TransactionBuilder(self.configuration.dust_limit)
        colored_outputs = yield from self._get_unspent_outputs(client, address)

        transaction = builder.transfer_bitcoin(
            colored_outputs,
            self.convert.base58_to_script(address),
            self.convert.base58_to_script(to),
            self._as_int(amount),
            self._get_fees(fees))

        return self.tx_parser(self._process_transaction(client, transaction, mode))

    @asyncio.coroutine
    def sendasset(self,
        address: "The address to send the asset from",
        asset: "The asset address identifying the asset to send",
        amount: "The amount of units to send",
        to: "The address to send the asset to",
        fees: "The fess in satoshis for the transaction"=None,
        mode: """'broadcast' (default) for signing and broadcasting the transaction,
            'signed' for signing the transaction without broadcasting,
            'unsigned' for getting the raw unsigned transaction without broadcasting"""='broadcast'
    ):
        """Creates a transaction for sending an asset from an address to another."""
        client = self._create_client()
        builder = openassets.transactions.TransactionBuilder(self.configuration.dust_limit)
        colored_outputs = yield from self._get_unspent_outputs(client, address)

        transaction = builder.transfer_assets(
            colored_outputs,
            self.convert.base58_to_script(address),
            self.convert.base58_to_script(to),
            self.convert.base58_to_asset_address(asset),
            self._as_int(amount),
            self._get_fees(fees))

        return self.tx_parser(self._process_transaction(client, transaction, mode))

    @asyncio.coroutine
    def issueasset(self,
        address: "The address to issue the asset from",
        amount: "The amount of units to send",
        to: "The address to send the asset to; if unspecified, the assets are sent back to the issuing address"=None,
        metadata: "The metadata to embed in the transaction"='',
        fees: "The fess in satoshis for the transaction"=None,
        mode: """'broadcast' (default) for signing and broadcasting the transaction,
            'signed' for signing the transaction without broadcasting,
            'unsigned' for getting the raw unsigned transaction without broadcasting"""='broadcast'
    ):
        """Creates a transaction for issuing an asset."""
        client = self._create_client()
        builder = openassets.transactions.TransactionBuilder(self.configuration.dust_limit)
        colored_outputs = yield from self._get_unspent_outputs(client, address)

        if to is None:
            to = address

        transaction = builder.issue(
            colored_outputs,
            self.convert.base58_to_script(address),
            self.convert.base58_to_script(to),
            self.convert.base58_to_script(address),
            self._as_int(amount),
            bytes(metadata, encoding='utf-8'),
            self._get_fees(fees))

        return self.tx_parser(self._process_transaction(client, transaction, mode))

    @asyncio.coroutine
    def distribute(self,
        address: "The address to distribute the asset from",
        forward_address: "The address where to forward the collected bitcoin funds",
        price: "Price of an asset unit in satoshis",
        metadata: "The metadata to embed in the transaction"='',
        fees: "The fess in satoshis for the transaction"=None,
        mode: """'broadcast' for signing and broadcasting the transaction,
            'signed' for signing the transaction without broadcasting,
            'unsigned' for getting the raw unsigned transaction without broadcasting,
            'preview' (default) for displaying a preview of the transactions"""='preview'
    ):
        """For every inbound transaction sending bitcoins to 'address', create an outbound transaction sending back
        to the sender newly issued assets, and send the bitcoins to the forward address. The number of issued coins
        sent back is proportional to the number of bitcoins sent, and configurable through the ratio argument.
        Because the asset issuance transaction is chained from the inbound transaction, double spend is impossible."""
        decimal_price = self._as_decimal(price)
        client = self._create_client()
        builder = openassets.transactions.TransactionBuilder(self.configuration.dust_limit)
        colored_outputs = yield from self._get_unspent_outputs(client, address)

        transactions = []
        summary = []
        for output in colored_outputs:
            incoming_transaction = client.getrawtransaction(output.out_point.hash)
            script = bytes(incoming_transaction.vout[0].scriptPubKey)
            collected, amount_issued, change = self._calculate_distribution(
                output.output.value, decimal_price, self._get_fees(fees), self.configuration.dust_limit)
            if amount_issued > 0:
                inputs = [bitcoin.core.CTxIn(output.out_point, output.output.script)]
                outputs = [
                    builder._get_colored_output(script),
                    builder._get_marker_output([amount_issued], bytes(metadata, encoding='utf-8')),
                    builder._get_uncolored_output(self.convert.base58_to_script(forward_address), collected)
                ]

                if change > 0:
                    outputs.append(builder._get_uncolored_output(script, change))

                transaction = bitcoin.core.CTransaction(vin=inputs, vout=outputs)

                transactions.append(transaction)
                summary.append({
                    'from': self.convert.script_to_base58(script),
                    'received': self.convert.to_coin(output.output.value) + " BTC",
                    'collected': self.convert.to_coin(collected) + " BTC",
                    'sent': str(amount_issued) + " Units",
                    'transaction': bitcoin.core.b2lx(output.out_point.hash)
                })

        if mode == 'preview':
            return summary
        else:
            result = []
            for transaction in transactions:
                result.append(self.tx_parser(self._process_transaction(client, transaction, mode)))

            return result

    @staticmethod
    def _calculate_distribution(output_value, price, fees, dust_limit):
        effective_amount = output_value - fees - dust_limit
        units_issued = int(effective_amount / price)

        collected = int(math.ceil(units_issued * price))
        change = effective_amount - collected
        if change < dust_limit:
            collected += change

        return collected, units_issued, effective_amount - collected

    # Private methods

    def _create_client(self):
        return bitcoin.rpc.Proxy(self.configuration.rpc_url)

    @staticmethod
    def _as_int(value):
        try:
            return int(value)
        except ValueError:
            raise colorcore.routing.ControllerError("Value '{}' is not a valid integer.".format(value))

    @staticmethod
    def _as_decimal(value):
        try:
            return decimal.Decimal(value)
        except decimal.InvalidOperation:
            raise colorcore.routing.ControllerError("Value '{}' is not a valid decimal number.".format(value))

    def _get_fees(self, value):
        if value is None:
            return self.configuration.default_fees
        else:
            return self._as_int(value)

    @asyncio.coroutine
    def _get_unspent_outputs(self, client, address, *args):
        cache = self.cache_factory()
        engine = openassets.protocol.ColoringEngine(asyncio.coroutine(client.getrawtransaction), cache, self.event_loop)
        unspent = client.listunspent(addrs=[address] if address else None, *args)

        result = []
        for item in unspent:
            output_result = yield from engine.get_output(item['outpoint'].hash, item['outpoint'].n)
            output = openassets.transactions.SpendableOutput(
                bitcoin.core.COutPoint(item['outpoint'].hash, item['outpoint'].n), output_result)
            output.confirmations = item['confirmations']
            result.append(output)

        # Commit new outputs to cache
        yield from cache.commit()
        return result

    @staticmethod
    def _process_transaction(client, transaction, mode):
        if mode == 'broadcast' or mode == 'signed':
            # Sign the transaction
            signed_transaction = client.signrawtransaction(transaction)
            if not signed_transaction['complete']:
                raise colorcore.routing.ControllerError("Could not sign the transaction.")

            if mode == 'broadcast':
                result = client.sendrawtransaction(signed_transaction['tx'])
                return bitcoin.core.b2lx(result)
            else:
                return signed_transaction['tx']
        else:
            # Return the transaction in raw format as a hex string
            return transaction


class Convert(object):
    """Provides conversion helpers."""

    def __init__(self, p2a_version_byte, p2sh_version_byte):
        self.p2a_version_byte = p2a_version_byte
        self.p2sh_version_byte = p2sh_version_byte

    @staticmethod
    def to_coin(satoshis):
        return '{0:.8f}'.format(decimal.Decimal(satoshis) / decimal.Decimal(bitcoin.core.COIN))

    def base58_to_script(self, base58_address):
        address = bitcoin.base58.CBase58Data(base58_address)
        if address.nVersion != self.p2a_version_byte:
            raise colorcore.routing.ControllerError("Invalid version byte.")

        address_bytes = address.to_bytes()
        return bytes([0x76, 0xA9]) + bitcoin.core.script.CScriptOp.encode_op_pushdata(address_bytes) \
            + bytes([0x88, 0xac])

    def base58_to_asset_address(self, base58_address):
        address = bitcoin.base58.CBase58Data(base58_address)
        if address.nVersion != self.p2sh_version_byte:
            raise colorcore.routing.ControllerError("Invalid version byte.")

        return address.to_bytes()

    def asset_address_to_base58(self, asset_address):
        return str(bitcoin.base58.CBase58Data.from_bytes(asset_address, self.p2sh_version_byte))

    def script_to_base58(self, script):
        script_object = bitcoin.core.CScript(script)
        try:
            opcodes = list(script_object.raw_iter())
        except bitcoin.core.script.CScriptInvalidError:
            return "Invalid script"

        if len(opcodes) == 5 and opcodes[0][0] == 0x76 and opcodes[1][0] == 0xA9 \
            and opcodes[3][0] == 0x88 and opcodes[4][0] == 0xac:
            opcode, data, sop_idx = opcodes[2]
            return str(bitcoin.base58.CBase58Data.from_bytes(data, self.p2a_version_byte))

        return "Unknown script"
