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
import bitcoin.core.serialize
import bitcoin.core.script
import bitcoin.rpc
import colorcore.program
import decimal
import itertools
import math
import openassets.protocol
import openassets.transactions


class Controller(object):

    def __init__(self, configuration, tx_parser):
        self.configuration = configuration
        self.tx_parser = tx_parser

    def getbalance(self,
        address: "Obtain the balance of this address only"=None,
        minconf: "The minimum number of confirmations (inclusive)"="1",
        maxconf: "The maximum number of confirmations (inclusive)"="9999999"
    ):
        """Obtains the balance of the wallet or an address"""
        client = self._create_client()
        result = client.listunspent(self._as_int(minconf), self._as_int(maxconf), [address] if address else None)
        engine = openassets.protocol.ColoringEngine(client.getrawtransaction, openassets.protocol.OutputCache())
        colored_outputs = [engine.get_output(item["outpoint"].hash, item["outpoint"].n) for item in result]

        table = []
        for script, group in itertools.groupby(colored_outputs, lambda output: output.scriptPubKey):
            script_outputs = list(group)
            total_value = Convert.to_coin(sum([item.nValue for item in script_outputs]))
            base58 = Convert.script_to_base58_p2a(script, self.configuration.version_byte)

            group_details = {
                'address': base58,
                'satoshiValue': total_value,
                'assets': []
            }

            table.append(group_details)

            for asset_address, outputs in itertools.groupby(script_outputs, lambda output: output.asset_address):
                if asset_address is not None:
                    total_quantity = sum([item.asset_quantity for item in outputs])
                    group_details['assets'].append({
                        'assetAddress':
                            Convert.asset_address_to_base58(asset_address, self.configuration.p2sh_version_byte),
                        'quantity': str(total_quantity)
                    })

        return table

    def sendbitcoin(self,
        address: "The address to send the bitcoins from",
        amount: "The amount of satoshis to send",
        to: "The address to send the bitcoins to",
        fees: "The fess in satoshis for the transaction" = None,
        mode: """'broadcast' (default) for signing and broadcasting the transaction,
            'signed' for signing the transaction without broadcasting,
            'unsigned' for getting the raw unsigned transaction without broadcasting"""="broadcast"
    ):
        """Creates a transaction for sending bitcoins from an address to another."""
        client = self._create_client()
        builder = openassets.transactions.TransactionBuilder(self.configuration.dust_limit)
        colored_outputs = self._get_unspent_outputs(client, address)

        if fees is None:
            fees = self.configuration.default_fees
        else:
            fees = self._as_int(fees)

        transaction = builder.transfer_bitcoin(
            colored_outputs,
            Convert.base58_to_p2a_script(address),
            Convert.base58_to_p2a_script(to),
            self._as_int(amount),
            fees)

        return self.tx_parser(self._process_transaction(client, transaction, mode))

    def sendasset(self,
        address: "The address to send the asset from",
        asset: "The asset address identifying the asset to send",
        amount: "The amount of units to send",
        to: "The address to send the asset to",
        fees: "The fess in satoshis for the transaction"=None,
        mode: """'broadcast' (default) for signing and broadcasting the transaction,
            'signed' for signing the transaction without broadcasting,
            'unsigned' for getting the raw unsigned transaction without broadcasting"""="broadcast"
    ):
        """Creates a transaction for sending an asset from an address to another."""
        client = self._create_client()
        builder = openassets.transactions.TransactionBuilder(self.configuration.dust_limit)
        colored_outputs = self._get_unspent_outputs(client, address)

        if fees is None:
            fees = self.configuration.default_fees
        else:
            fees = self._as_int(fees)

        transaction = builder.transfer_assets(
            colored_outputs,
            Convert.base58_to_p2a_script(address),
            Convert.base58_to_p2a_script(to),
            Convert.base58_to_asset_address(asset),
            self._as_int(amount),
            fees)

        return self.tx_parser(self._process_transaction(client, transaction, mode))

    def issueasset(self,
        address: "The address to issue the asset from",
        amount: "The amount of units to send",
        to: "The address to send the asset to; if unspecified, the assets are sent back to the issuing address"=None,
        metadata: "The metadata to embed in the transaction"="",
        fees: "The fess in satoshis for the transaction"=None,
        mode: """'broadcast' (default) for signing and broadcasting the transaction,
            'signed' for signing the transaction without broadcasting,
            'unsigned' for getting the raw unsigned transaction without broadcasting"""="broadcast"
    ):
        """Creates a transaction for sending an asset from an address to another."""
        client = self._create_client()
        builder = openassets.transactions.TransactionBuilder(self.configuration.dust_limit)
        colored_outputs = self._get_unspent_outputs(client, address)

        if fees is None:
            fees = self.configuration.default_fees
        else:
            fees = self._as_int(fees)

        if to is None:
            to = address

        transaction = builder.issue(
            colored_outputs,
            Convert.base58_to_p2a_script(address),
            Convert.base58_to_p2a_script(to),
            Convert.base58_to_p2a_script(address),
            self._as_int(amount),
            bytes(metadata, encoding="utf-8"),
            fees)

        return self.tx_parser(self._process_transaction(client, transaction, mode))

    def distribute(self,
        address: "The address to distribute the asset from",
        forward_address: "The address where to forward the collected bitcoin funds",
        price: "Price of an asset unit in satoshis",
        metadata: "The metadata to embed in the transaction"="",
        fees: "The fess in satoshis for the transaction"=None,
        mode: """'broadcast' for signing and broadcasting the transaction,
            'signed' for signing the transaction without broadcasting,
            'unsigned' for getting the raw unsigned transaction without broadcasting,
            'preview' (default) for displaying a preview of the transactions"""="preview"
    ):
        """For every inbound transaction sending bitcoins to 'address', create an outbound transaction sending back
        to the sender newly issued assets, and send the bitcoins to the forward address. The number of issued coins
        sent back is proportional to the number of bitcoins sent, and configurable through the ratio argument.
        Because the asset issuance transaction is chained from the inbound transaction, double spend is impossible."""
        client = self._create_client()
        builder = openassets.transactions.TransactionBuilder(self.configuration.dust_limit)
        colored_outputs = self._get_unspent_outputs(client, address)

        if fees is None:
            fees = self.configuration.default_fees
        else:
            fees = self._as_int(fees)

        transactions = []
        summary = []
        for output in colored_outputs:
            incoming_transaction = client.getrawtransaction(output.out_point.hash)
            script = bytes(incoming_transaction.vout[0].scriptPubKey)
            collected, amount_issued, change = self._calculate_distribution(
                output.output.nValue, self._as_decimal(price), fees, self.configuration.dust_limit)
            if amount_issued > 0:
                transaction = bitcoin.core.CTransaction(
                    vin=[bitcoin.core.CTxIn(output.out_point, output.output.scriptPubKey)],
                    vout=[
                        builder._get_colored_output(script),
                        builder._get_marker_output([amount_issued], bytes(metadata, encoding="utf-8")),
                        builder._get_uncolored_output(Convert.base58_to_p2a_script(forward_address), collected),
                        builder._get_uncolored_output(script, change)
                    ]
                )

                transactions.append(transaction)
                summary.append({
                    'from': Convert.script_to_base58_p2a(script, self.configuration.version_byte),
                    'received': Convert.to_coin(output.output.nValue) + " BTC",
                    'collected': Convert.to_coin(collected) + " BTC",
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
        change = output_value - collected
        if change < dust_limit:
            collected += change

        return collected, units_issued, output_value - collected

    # Private methods

    def _create_client(self):
        return bitcoin.rpc.Proxy(self.configuration.rpc_url)

    @staticmethod
    def _as_int(value):
        try:
            return int(value)
        except ValueError:
            raise colorcore.program.ControllerError("Value '{}' is not a valid integer.".format(value))

    @staticmethod
    def _as_decimal(value):
        try:
            return decimal.Decimal(value)
        except ValueError:
            raise colorcore.program.ControllerError("Value '{}' is not a valid decimal number.".format(value))

    @staticmethod
    def _get_unspent_outputs(client, address):
        engine = openassets.protocol.ColoringEngine(client.getrawtransaction, openassets.protocol.OutputCache())
        result = client.listunspent(addrs=[address] if address else None)
        return [
            openassets.transactions.SpendableOutput(
            bitcoin.core.COutPoint(item['outpoint'].hash, item['outpoint'].n),
            engine.get_output(item['outpoint'].hash, item['outpoint'].n)) for item in result]

    @staticmethod
    def _process_transaction(client, transaction, mode):
        if mode == 'broadcast' or mode == 'signed':
            # Sign the transaction
            signed_transaction = client.signrawtransaction(transaction)
            if not signed_transaction['complete']:
                raise colorcore.program.ControllerError("Could not sign the transaction.")

            if mode == 'broadcast':
                result = client.sendrawtransaction(signed_transaction['tx'])
                return bitcoin.core.b2lx(result)
            else:
                return signed_transaction['tx']
        else:
            # Return the transaction in raw format as a hex string
            return transaction


class Convert(object):

    @staticmethod
    def to_coin(satoshis):
        return '%f' % (satoshis / bitcoin.core.COIN)

    @staticmethod
    def base58_to_p2a_script(base58_address):
        address_bytes = bitcoin.base58.CBase58Data(base58_address).to_bytes()
        return bytes([0x76, 0xA9]) + bitcoin.core.script.CScriptOp.encode_op_pushdata(address_bytes) \
            + bytes([0x88, 0xac])

    @staticmethod
    def base58_to_asset_address(base58_address):
        return bitcoin.base58.CBase58Data(base58_address).to_bytes()

    @staticmethod
    def asset_address_to_base58(asset_address, p2sh_version_byte):
        return str(bitcoin.base58.CBase58Data.from_bytes(asset_address, p2sh_version_byte))

    @staticmethod
    def script_to_base58_p2a(script, version_byte):
        script_object = bitcoin.core.CScript(script)
        try:
            opcodes = list(script_object.raw_iter())
        except bitcoin.core.script.CScriptInvalidError:
            return "Invalid script"

        if len(opcodes) == 5 and opcodes[0][0] == 0x76 and opcodes[1][0] == 0xA9 \
            and opcodes[3][0] == 0x88 and opcodes[4][0] == 0xac:
            opcode, data, sop_idx = opcodes[2]
            return str(bitcoin.base58.CBase58Data.from_bytes(data, version_byte))

        return "Unknown script"
