Colorcore
=========

Colorcore is an open source colored coin wallet compatible with the `Open Assets Protocol <https://github.com/OpenAssets/open-assets-protocol/blob/master/specification.mediawiki>`_. It supports two modes: a command line interface, and a JSON/RPC server. The command line interface is suitable for managing a local wallet without going through any third-party service. The JSON/RPC interface is suitable for server-side implementations of colored coins and programmatic colored coins wallet management.

Open Assets is a protocol for issuing and transferring custom digital tokens in a secure way on the Bitcoin blockchain (or any compatible blockchain).

Use `Coinprism <https://www.coinprism.com>`_ for a web-based and user-friendly colored coins wallet.

Requirements
============

The following items are required for using Colorcore:

* Python 3
* The `openassets <https://github.com/openassets/openassets>`_ package
* The `python-bitcoinlib <https://github.com/petertodd/python-bitcoinlib>`_ package
* An operational Bitcoin Core wallet with JSON/RPC enabled and full transaction index

Installation
============

Use the following command to install Colorcore::

    $ pip install colorcore
    
Or manually from source, assuming all required modules are installed on your system::

    $ python ./setup.py install

Configuration
=============

Make sure your have a Bitcoin Core server running, with the following arguments: ``-txindex=1 -server=1``. You may need to have a username and password configured in the configuration file for Bitcoin Core (``bitcoin.conf``).

All the configuration for Colorcore is done though the ``config.ini`` file.

Usage
=====

The general syntax for executing Colorcore is the following::

    python colorcore.py <command> <arguments>
    
All the commands are documented. Use the following command to show the documentation::

    python colorcore.py --help

The currently supported commands are the following:

* **getbalance**: Returns the balance in both bitcoin and colored coin assets for all of the addresses available in your Bitcoin Core wallet.
* **sendbitcoin**: Creates a transaction for sending bitcoins from an address to another.
* **sendasset**: Creates a transaction for sending an asset from an address to another.
* **issueasset**: Creates a transaction for issuing an asset.
* **distribute**: Creates a batch of transactions used for creating a token and distributing it to participants of a crowd sale.

RPC server
----------

Use the following command to start the RPC server::

    python colorcore.py server

Colorcore will then start listening on the port specified in the configuration file.

To call the RPC server, issue a HTTP POST request to http://localhost:<port>/<operation>. The list of valid operations is the same as the list of commands available via command line.

The arguments must be passed to the server in the body of the request, using the ``application/x-www-form-urlencoded`` encoding. Argument names are the same as for the command line interface.

Issue an asset
--------------

Issuing an asset is done through a standard Bitcoin transaction. The following command can be used to issue one million units of an asset::

    python colorcore.py issueasset <address> 1000000

The ``<address>`` placeholder represents the issuing address. You must own the private key for this address in your Bitcoin Core wallet, and you must have at least 0.000006 BTC on that address in order to successfully issue the asset. If the operation is successful, this command will return the transaction hash of the issuing transaction. You can then use a `color-aware block explorer <https://www.coinprism.info>`_ to see the details of the transaction.

Remarks
-------

Fees can be specified through the ``--fees`` argument, and the default amount for fees can be changed through the ``config.ini`` file.

Once you have colored coins on one address, make sure you use the ``sendbitcoin`` operation to send uncolored bitcoins from that address. If you use Bitcoin Core to send bitcoins, Bitcoin Core might spend your colored outputs as it is not aware of colored coins.

License
=======

The MIT License (MIT)

Copyright (c) 2014 Flavien Charlon

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
