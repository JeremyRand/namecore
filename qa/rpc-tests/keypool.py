#!/usr/bin/env python2
# Copyright (c) 2014-2015 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

# Exercise the wallet keypool, and interaction with wallet encryption/locking

# Add python-bitcoinrpc to module search path:

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import *
from test_framework import auxpow


def check_array_result(object_array, to_match, expected):
    """
    Pass in array of JSON objects, a dictionary with key/value pairs
    to match against, and another dictionary with expected key/value
    pairs.
    """
    num_matched = 0
    for item in object_array:
        all_match = True
        for key,value in to_match.items():
            if item[key] != value:
                all_match = False
        if not all_match:
            continue
        for key,value in expected.items():
            if item[key] != value:
                raise AssertionError("%s : expected %s=%s"%(str(item), str(key), str(value)))
            num_matched = num_matched+1
    if num_matched == 0:
        raise AssertionError("No objects matched %s"%(str(to_match)))

class KeyPoolTest(BitcoinTestFramework):

    def run_test(self):
        nodes = self.nodes
        # Encrypt wallet and wait to terminate
        nodes[0].encryptwallet('test')
        bitcoind_processes[0].wait()
        # Restart node 0
        nodes[0] = start_node(0, self.options.tmpdir)
        # Keep creating keys
        addr = nodes[0].getnewaddress()
        try:
            addr = nodes[0].getnewaddress()
            raise AssertionError('Keypool should be exhausted after one address')
        except JSONRPCException as e:
            assert(e.error['code']==-12)

        # put three new keys in the keypool
        nodes[0].walletpassphrase('test', 12000)
        nodes[0].keypoolrefill(3)
        nodes[0].walletlock()

        # drain the keys
        addr = set()
        addr.add(nodes[0].getrawchangeaddress())
        addr.add(nodes[0].getrawchangeaddress())
        addr.add(nodes[0].getrawchangeaddress())
        addr.add(nodes[0].getrawchangeaddress())
        # assert that four unique addresses were returned
        assert(len(addr) == 4)
        # the next one should fail
        try:
            addr = nodes[0].getrawchangeaddress()
            raise AssertionError('Keypool should be exhausted after three addresses')
        except JSONRPCException as e:
            assert(e.error['code']==-12)

        # refill keypool with three new addresses
        nodes[0].walletpassphrase('test', 1)
        nodes[0].keypoolrefill(3)
        # test walletpassphrase timeout
        time.sleep(1.1)
        assert_equal(nodes[0].getwalletinfo()["unlocked_until"], 0)

        # drain them by mining
        nodes[0].generate(1)
        nodes[0].generate(1)
        nodes[0].generate(1)
        nodes[0].generate(1)
        try:
            nodes[0].generate(1)
            raise AssertionError('Keypool should be exhausted after three addesses')
        except JSONRPCException as e:
            assert(e.error['code']==-12)

        # test draining with getauxblock
        test_auxpow(nodes)

def test_auxpow(nodes):
    """
    Test behaviour of getauxpow.  Calling getauxpow should reserve
    a key from the pool, but it should be released again if the
    created block is not actually used.  On the other hand, if the
    auxpow is submitted and turned into a block, the keypool should
    be drained.
    """

    nodes[0].walletpassphrase('test', 12000)
    nodes[0].keypoolrefill(1)
    nodes[0].walletlock()
    assert_equal (nodes[0].getwalletinfo()['keypoolsize'], 2)

    nodes[0].getauxblock()
    assert_equal (nodes[0].getwalletinfo()['keypoolsize'], 2)
    nodes[0].generate(1)
    assert_equal (nodes[0].getwalletinfo()['keypoolsize'], 1)
    auxblock = nodes[0].getauxblock()
    assert_equal (nodes[0].getwalletinfo()['keypoolsize'], 1)

    target = auxpow.reverseHex(auxblock['_target'])
    solved = auxpow.computeAuxpow(auxblock['hash'], target, True)
    res = nodes[0].getauxblock(auxblock['hash'], solved)
    assert res
    assert_equal(nodes[0].getwalletinfo()['keypoolsize'], 0)

    try:
        nodes[0].getauxblock()
        raise AssertionError('Keypool should be exhausted by getauxblock')
    except JSONRPCException,e:
        assert(e.error['code']==-12)

def main():
    import optparse

    parser = optparse.OptionParser(usage="%prog [options]")
    parser.add_option("--nocleanup", dest="nocleanup", default=False, action="store_true",
                      help="Leave namecoinds and test.* datadir on exit or error")
    parser.add_option("--srcdir", dest="srcdir", default="../../src",
                      help="Source directory containing namecoind/namecoin-cli (default: %default%)")
    parser.add_option("--tmpdir", dest="tmpdir", default=tempfile.mkdtemp(prefix="test"),
                      help="Root directory for datadirs")
    (options, args) = parser.parse_args()

    os.environ['PATH'] = options.srcdir+":"+os.environ['PATH']

    check_json_precision()

    success = False
    nodes = []
    try:
        print("Initializing test directory "+options.tmpdir)
        if not os.path.isdir(options.tmpdir):
            os.makedirs(options.tmpdir)
        initialize_chain(options.tmpdir)

        nodes = start_nodes(1, options.tmpdir)

        run_test(nodes, options.tmpdir)

        success = True

    except AssertionError as e:
        print("Assertion failed: "+e.message)
    except JSONRPCException as e:
        print("JSONRPC error: "+e.error['message'])
        traceback.print_tb(sys.exc_info()[2])
    except Exception as e:
        print("Unexpected exception caught during testing: "+str(sys.exc_info()[0]))
        traceback.print_tb(sys.exc_info()[2])

    def setup_chain(self):
        print("Initializing test directory "+self.options.tmpdir)
        initialize_chain(self.options.tmpdir)

    def setup_network(self):
        self.nodes = start_nodes(1, self.options.tmpdir)

if __name__ == '__main__':
    KeyPoolTest().main()
