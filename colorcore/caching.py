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
import bitcoin.core.script
import contextlib
import openassets.protocol
import sqlite3


class SqliteCache(openassets.protocol.OutputCache):
    """An object that can be used for caching outputs in a Sqlite database."""

    def __init__(self, path):
        """
        Initializes the connection to the database, and creates the table if needed.

        :param str path: The path to the database file. Use ':memory:' for an in-memory database.
        """
        self.connection = sqlite3.connect(path)

        with contextlib.closing(self.connection.cursor()) as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Outputs(
                  TransactionHash BLOB,
                  OutputIndex INT,
                  Value BIGINT,
                  Script BLOB,
                  AssetID BLOB,
                  AssetQuantity INT,
                  OutputType TINYINT,
                  PRIMARY KEY (TransactionHash, OutputIndex))
            """)

    @asyncio.coroutine
    def get(self, transaction_hash, output_index):
        """
        Returns a cached output.

        :param bytes transaction_hash: The hash of the transaction the output belongs to.
        :param int output_index: The index of the output in the transaction.
        :return: The output for the transaction hash and output index provided if it is found in the cache, or None
            otherwise.
        :rtype: TransactionOutput
        """
        with contextlib.closing(self.connection.cursor()) as cursor:
            cursor.execute("""
                  SELECT  Value, Script, AssetID, AssetQuantity, OutputType
                  FROM    Outputs
                  WHERE   TransactionHash = ? AND OutputIndex = ?
                """,
                (transaction_hash, output_index))

            result = cursor.fetchone()

            if result is None:
                return None
            else:
                return openassets.protocol.TransactionOutput(
                    result[0],
                    bitcoin.core.script.CScript(result[1]),
                    result[2],
                    result[3],
                    openassets.protocol.OutputType(result[4])
                )

    @asyncio.coroutine
    def put(self, transaction_hash, output_index, output):
        """
        Saves an output in cache.

        :param bytes transaction_hash: The hash of the transaction the output belongs to.
        :param int output_index: The index of the output in the transaction.
        :param TransactionOutput output: The output to save.
        """
        with contextlib.closing(self.connection.cursor()) as cursor:
            cursor.execute("""
                  INSERT OR IGNORE INTO Outputs
                    (TransactionHash, OutputIndex, Value, Script, AssetID, AssetQuantity, OutputType)
                  VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction_hash,
                    output_index,
                    output.value,
                    bytes(output.script),
                    output.asset_id,
                    output.asset_quantity,
                    output.output_type.value
                ))

    @asyncio.coroutine
    def commit(self):
        """
        Commits all changes to the cache database.
        """
        self.connection.commit()