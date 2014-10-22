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

import aiohttp
import asyncio
import bitcoin.core
import colorcore.providers.core
import json


class ChainApiProvider(colorcore.providers.core.AbstractBlockchainProvider):
    """Provides a Blockchain provider using the chain.com API."""

    def __init__(self, base_url, api_key, api_secret, fallback_provider, loop):
        self._base_url = base_url
        self._auth = aiohttp.BasicAuth(api_key, api_secret)
        self._fallback_provider = fallback_provider
        self._loop = loop

    @asyncio.coroutine
    def list_unspent(self, addresses, *args, **kwargs):
        if addresses is None:
            if self._fallback_provider:
                return (yield from self._fallback_provider.list_unspent(addresses, *args, **kwargs))
            else:
                raise NotImplementedError("This blockchain provider does not have access to a wallet.")

        response = yield from self._get('addresses/{address}/unspents'.format(address=','.join(addresses)))
        data = json.loads(str(response, 'utf-8'))
        return [{
            'outpoint': bitcoin.core.COutPoint(bitcoin.core.lx(item['transaction_hash']), item['output_index']),
            'confirmations': item['confirmations']}
            for item in data]

    @asyncio.coroutine
    def get_transaction(self, transaction_hash, *args, **kwargs):
        response = yield from self._get('transactions/{hash}'.format(hash=bitcoin.core.b2lx(transaction_hash)))
        data = json.loads(str(response, 'utf-8'))

        return bitcoin.core.CTransaction(
            vin=[bitcoin.core.CTxIn(
                prevout=bitcoin.core.COutPoint(bitcoin.core.lx(input['output_hash']), input['output_index']),
            )
            for input in data['inputs']],
            vout=[bitcoin.core.CTxOut(
                nValue=output['value'],
                scriptPubKey=bitcoin.core.CScript(bitcoin.core.x(output['script_hex']))
            )
            for output in data['outputs']]
        )

    @asyncio.coroutine
    def sign_transaction(self, transaction, *args, **kwargs):
        if self._fallback_provider:
            return (yield from self._fallback_provider.sign_transaction(transaction, *args, **kwargs))
        else:
            raise NotImplementedError("This blockchain provider does not support signing a transaction.")

    @asyncio.coroutine
    def send_transaction(self, transaction, *args, **kwargs):
        if self._fallback_provider:
            return (yield from self._fallback_provider.send_transaction(transaction, *args, **kwargs))
        else:
            raise NotImplementedError("This blockchain provider does not support sending a transaction.")

    @asyncio.coroutine
    def _get(self, url):
        response = yield from aiohttp.request('GET', self._base_url + url, auth=self._auth, loop=self._loop)
        return (yield from response.read())