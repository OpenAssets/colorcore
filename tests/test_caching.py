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

import bitcoin.core.script
import colorcore.caching
import openassets.protocol
import tests.helpers
import unittest


class SqliteCacheTests(unittest.TestCase):
    @tests.helpers.async_test
    def test_colored_output(self, loop):
        target = colorcore.caching.SqliteCache(':memory:')

        output = openassets.protocol.TransactionOutput(
            150,
            bitcoin.core.script.CScript(b'abcd'),
            b'1234',
            75,
            openassets.protocol.OutputType.issuance
        )

        yield from target.put(b'transaction', 5, output)
        result = yield from target.get(b'transaction', 5)

        self.assert_output(result, 150, b'abcd', b'1234', 75, openassets.protocol.OutputType.issuance)

    @tests.helpers.async_test
    def test_commit(self, loop):
        target = colorcore.caching.SqliteCache(':memory:')

        output = openassets.protocol.TransactionOutput(
            150,
            bitcoin.core.script.CScript(b'abcd'),
            b'1234',
            75,
            openassets.protocol.OutputType.issuance
        )

        yield from target.put(b'transaction', 5, output)
        yield from target.commit()
        result = yield from target.get(b'transaction', 5)

        self.assert_output(result, 150, b'abcd', b'1234', 75, openassets.protocol.OutputType.issuance)

    @tests.helpers.async_test
    def test_uncolored_output(self, loop):
        target = colorcore.caching.SqliteCache(':memory:')

        output = openassets.protocol.TransactionOutput(
            150,
            bitcoin.core.script.CScript(b'abcd'),
            None,
            0,
            openassets.protocol.OutputType.uncolored
        )

        yield from target.put(b'transaction', 5, output)
        result = yield from target.get(b'transaction', 5)

        self.assert_output(result, 150, b'abcd', None, 0, openassets.protocol.OutputType.uncolored)

    @tests.helpers.async_test
    def test_max_values(self, loop):
        target = colorcore.caching.SqliteCache(':memory:')

        output = openassets.protocol.TransactionOutput(
            2 ** 63 - 1,
            bitcoin.core.script.CScript(b'a' * 16384),
            b'1234',
            2 ** 63 - 1,
            openassets.protocol.OutputType.issuance
        )

        yield from target.put(b'transaction', 5, output)
        result = yield from target.get(b'transaction', 5)

        self.assert_output(
            result, 2 ** 63 - 1, b'a' * 16384, b'1234', 2 ** 63 - 1, openassets.protocol.OutputType.issuance)

    @tests.helpers.async_test
    def test_cache_miss(self, loop):
        target = colorcore.caching.SqliteCache(':memory:')

        result = yield from target.get(b'transaction', 5)

        self.assertIsNone(result)

    def assert_output(self, output, value, script, asset_id, asset_quantity, output_type):
        self.assertEqual(value, output.value)
        self.assertEqual(script, bytes(output.script))
        self.assertEqual(asset_id, output.asset_id)
        self.assertEqual(asset_quantity, output.asset_quantity)
        self.assertEqual(output_type, output.output_type)