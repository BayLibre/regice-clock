#!/usr/bin/env python
# -*- coding: utf-8 -*-

# MIT License
#
# Copyright (c) 2018 BayLibre
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

import unittest

from svd import SVDText
from libregice.regiceclienttest import RegiceClientTest
from libregice.device import Device
from regiceclock import FixedClock, Clock, Gate, Mux, ClockTree, Divider, PLL
from regiceclock import InvalidDivider, UnknownClock, InvalidFrequency
from regicetest import open_svd_file

def ext_get_freq(clk):
    return 1234

def ext_enable(clk):
    return clk.en_field.write(1)

def ext_disable(clk):
    return clk.en_field.write(0)

class ClockTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        file = open_svd_file('test.svd')
        svd = SVDText(file.read())
        svd.parse()
        self.client = RegiceClientTest()
        self.dev = Device(svd, self.client)
        self.tree = ClockTree(self.dev)
        self.memory = self.client.memory

    @classmethod
    def setUp(self):
        self.client.memory_restore()

class TestClock(ClockTestCase):
    def test_clock_add_to_tree(self):
        tree = ClockTree(self.dev)
        self.assertEqual(tree.clocks, {})

        Clock(tree=tree)
        self.assertEqual(tree.clocks, {})

        Clock(name='test1')
        self.assertEqual(tree.clocks, {})

        Clock(tree=tree, name='test1')
        self.assertIn('test1', tree.clocks)

    def test_check(self):
        clk = Clock(name='test1')
        with self.assertRaises(Exception):
            clk.check()

        clk = Clock(tree=self.tree)
        with self.assertRaises(Exception):
            clk.check()

        clk = Clock(tree=self.tree, name='test1')
        clk.check()

    def test_get_parent(self):
        clk1 = Clock(tree=self.tree, name='test1')
        self.assertEqual(clk1.get_parent(), None)

        clk2 = Clock(tree=self.tree, name='test2', parent='test1')
        self.assertEqual(clk2.get_parent(), clk1)

    def test_get_freq(self):
        clk = Clock(tree=self.tree, name='test1')
        with self.assertRaises(InvalidFrequency):
            clk.get_freq()

class TestGate(ClockTestCase):
    def test_enabled(self):
        field = self.dev.TEST1.TESTA.A1
        clock = Gate(name='gate', tree=self.tree, en_field=field)
        self.dev.TEST1.TESTA.A1.write(1)
        self.assertTrue(clock.enabled())
        self.dev.TEST1.TESTA.A1.write(0)
        self.assertFalse(clock.enabled())

        clock = Gate(name='gate', tree=self.tree,
                     en_field=field, rdy_field=field)
        self.dev.TEST1.TESTA.A1.write(0)
        self.assertFalse(clock.enabled())

    def test_build(self):
        clock = Gate(tree=self.tree)
        self.assertFalse(clock.build())
        clock = Gate(tree=self.tree, en_field=self.dev.TEST1.TESTA.A1)
        self.assertTrue(clock.build())

class TestFixedClock(ClockTestCase):
    def test_fixed_clock(self):
        clock = FixedClock(freq=123456)
        self.assertEqual(clock.freq, 123456)

    def test_get_freq(self):
        clock = FixedClock(name='osc', tree=self.tree, freq=123456)
        self.assertEqual(clock.get_freq(), 123456)

        clock = FixedClock(name='osc', tree=self.tree, min=123, max=456)
        clock.freq = 12
        with self.assertRaises(InvalidFrequency):
            clock.get_freq()
        clock.freq = 567
        with self.assertRaises(InvalidFrequency):
            clock.get_freq()
        clock.freq = 123
        self.assertEqual(clock.get_freq(), 123)

    def test_build(self):
        clock = FixedClock()
        self.assertFalse(clock.build())

        clock = FixedClock(freq=123456)
        self.assertTrue(clock.build())

def ext_get_mux(self):
    return 0

class TestMux(ClockTestCase):
    @classmethod
    def setUpClass(self):
        super(TestMux, self).setUpClass()
        self.mux_field = self.dev.TEST1.TESTA.A3
        self.tree = ClockTree(self.dev)
        FixedClock(name='test0', tree=self.tree, freq=1234)
        FixedClock(name='test1', tree=self.tree, freq=123456)
        FixedClock(name='test3', tree=self.tree, freq=12345)
        self.mux_parents = {0: 'test0', 1: 'test1', 3: 'test3'}
        self.mux = Mux(name='muxe', tree=self.tree,
                       parents=self.mux_parents, mux_field=self.mux_field)

    def test_get_parent(self):
        parent = self.mux.get_parent()
        self.assertEqual(parent.name, 'test3')

        mux = Mux(name='mux', tree=self.tree, parents=self.mux_parents,
                  get_mux=ext_get_mux)
        parent = mux.get_parent()
        self.assertEqual(parent.name, 'test0')

    def test_get_freq(self):
        self.assertEqual(self.mux._get_freq(), 12345)

        mux = Mux(name='pll', tree=self.tree,
                  parents={0: 'test0', 1: 'test1', 3: None},
                  mux_field=self.dev.TEST1.TESTA.A3)
        self.assertEqual(mux.get_freq(), 0)

    def test_build(self):
        mux = Mux()
        self.assertFalse(mux.build())

        mux = Mux(parents={0: 'parent1', 1: 'parent2'})
        self.assertFalse(mux.build())

        mux = Mux(parents={0: 'parent1', 1: 'parent2'},
                  mux_field=self.dev.TEST1.TESTA.A3)
        self.assertFalse(mux.build())

        mux = Mux(tree=self.tree, parents={0: 'test0', 1: 'test4'},
                  mux_field=self.dev.TEST1.TESTA.A3)
        self.assertFalse(mux.build())

        mux = Mux(tree=self.tree, parents={0: 'test0', 1: 'test1'},
                  mux_field=self.dev.TEST1.TESTA.A3)
        self.assertTrue(mux.build())

        mux = Mux(tree=self.tree, parents={0: 'test0', 1: 'test1', 2: None},
                  mux_field=self.dev.TEST1.TESTA.A3)
        self.assertTrue(mux.build())

    def test_enabled(self):
        mux = Mux(name='pll', tree=self.tree, parents={0: 'test0', 3: None},
                  mux_field=self.dev.TEST1.TESTA.A3)
        self.assertFalse(mux.enabled())
        self.dev.TEST1.TESTA.A3.write(0)
        self.assertTrue(mux.enabled())
        self.dev.TEST1.TESTA.A3.write(3)

def ext_get_div(div):
    return 3

def ext_get_div_none(div):
    return None

def ext_get_div_zero(div):
    return 0

class TestDivider(ClockTestCase):
    def test_build(self):
        div = Divider()
        self.assertFalse(div.build())

        div = Divider(parent='test')
        self.assertFalse(div.build())

        div = Divider(parent='test', div=2)
        self.assertTrue(div.build())

        table = {0: 1, 1: 4, 2: 16}
        div = Divider(parent='test', table=table)
        self.assertFalse(div.build())

        div = Divider(parent='test', table=table,
                      div_field=self.dev.TEST1.TESTA.A3)
        self.assertTrue(div.build())

        div = Divider(parent='test', table=table)
        self.assertFalse(div.build())

        div = Divider(parent='test', div_field=self.dev.TEST1.TESTA.A3)
        self.assertTrue(div.build())

    def test_get_div(self):
        tree = ClockTree(self.dev)
        FixedClock(name='test', tree=self.tree, freq=123456)

        div = Divider(name='div', tree=self.tree, parent='test', div=2)
        self.assertEqual(div._get_div(), 2)

        div = Divider(name='div', tree=self.tree, parent='test',
                      div_field=self.dev.TEST1.TESTA.A3)
        self.assertEqual(int(div._get_div()), 3)

        div = Divider(name='div', tree=self.tree, parent='test',
                      div_field=self.dev.TEST1.TESTA.A3,
                      div_type=Divider.POWER_OF_TWO)
        self.assertEqual(int(div._get_div()), 8)

        div = Divider(name='div', tree=self.tree, parent='test',
                      div_field=self.dev.TEST1.TESTA.A3, table={3: 12, 4: 16})
        self.assertEqual(int(div._get_div()), 12)

        self.dev.TEST1.TESTA.A3.write(2)
        with self.assertRaises(InvalidDivider):
            div._get_div()

        div = Divider(name='div', tree=self.tree, parent='test',
                      div_field=self.dev.TEST1.TESTA.A3, div_type=9999)
        with self.assertRaises(InvalidDivider):
            div._get_div()

        div = Divider(name='div', tree=self.tree, parent='test',
                      get_div=ext_get_div)
        self.assertTrue(div.build())
        self.assertEqual(int(div._get_div()), 3)

    def test_get_freq(self):
        freq = 123456
        tree = ClockTree(self.dev)
        FixedClock(name='test', tree=self.tree, freq=freq)

        div = Divider(name='div', tree=self.tree, parent='test', div=2)
        self.assertEqual(div._get_freq(), freq / 2)

        div = Divider(name='div', tree=self.tree, parent='test',
                      get_div=ext_get_div_none)
        self.assertEqual(div._get_freq(), 0)

        div = Divider(name='div', tree=self.tree, parent='test',
                      get_div=ext_get_div_zero)
        with self.assertRaises(ZeroDivisionError):
            self.assertEqual(div._get_freq(), 0)

        div = Divider(name='div', tree=self.tree, parent='test',
                      get_div=ext_get_div_zero, div_type=Divider.ZERO_TO_GATE)
        self.assertEqual(div._get_freq(), 0)

    def test_enabled(self):
        freq = 123456
        tree = ClockTree(self.dev)
        FixedClock(name='test', tree=self.tree, freq=freq)

        div = Divider(name='div', tree=self.tree, parent='test', div=2)
        self.assertTrue(div.enabled())

        div = Divider(name='div', tree=self.tree, parent='test',
                      get_div=ext_get_div_zero, div_type=Divider.ZERO_TO_GATE)
        self.assertFalse(div.enabled())

        div = Divider(name='div', tree=self.tree, parent='test',
                      get_div=ext_get_div_none)
        self.assertFalse(div.enabled())

def ext_get_freq(pll):
    return 1234

class TestPLL(ClockTestCase):
    def test_enabled(self):
        pll = PLL(name='pll', tree=self.tree, get_freq=ext_get_freq,
                  en_field=self.dev.TEST1.TESTA.A3)
        self.dev.TEST1.TESTA.A3.write(1)
        self.assertTrue(pll.enabled())
        self.dev.TEST1.TESTA.A3.write(0)
        self.assertFalse(pll.enabled())

    def test_get_freq(self):
        pll = PLL(name='pll', tree=self.tree, get_freq=ext_get_freq)
        self.assertTrue(pll.get_freq(), 1234)

    def test_build(self):
        pll = PLL(tree=self.tree)
        self.assertFalse(pll.build())
        pll = PLL(tree=self.tree, get_freq=ext_get_freq)
        self.assertTrue(pll.build())

class TestClockTree(ClockTestCase):
    @classmethod
    def setUpClass(self):
        super(TestClockTree, self).setUpClass()
        FixedClock(name='osc1', tree=self.tree, freq=1234)
        FixedClock(name='osc2', tree=self.tree, freq=2345)
        FixedClock(name='osc3', tree=self.tree, freq=5432)
        Mux(name='mux1', tree=self.tree, mux_field=self.dev.TEST1.TESTA.A3,
            parents={0: 'osc1', 1: 'osc2', 2: 'osc3', 3: 'osc3'})
        Divider(name='div1', tree=self.tree, div=2, parent='osc1')
        Divider(name='div2', tree=self.tree, div=4, parent='mux1')
        Gate(name='gate1', tree=self.tree, parent='div1',
             en_field=self.dev.TEST1.TESTA.A1)
        Gate(name='gate2', tree=self.tree, parent='div2',
             en_field=self.dev.TEST1.TESTA.A2)
        Divider(name='div3', tree=self.tree, div=2, parent='gate2')

    def test_get(self):
        self.assertEqual(self.tree.get(None), None)
        self.assertEqual(self.tree.get('osc3').name, 'osc3')
        with self.assertRaises(UnknownClock):
            self.tree.get("unknown clock")

    def test_get_freq(self):
        self.assertEqual(self.tree.get_freq('osc3'), 5432)
        self.assertEqual(self.tree.get_freq('mux1'), 5432)
        self.assertEqual(self.tree.get_freq('div2'), 5432 / 4)
        self.assertEqual(self.tree.get_freq('gate2'), 5432 / 4)
        self.assertEqual(self.tree.get_freq('div3'), 5432 / 8)
        self.assertEqual(self.tree.get_freq('div1'), 1234 / 2)
        self.assertEqual(self.tree.get_freq('gate1'), 1234 / 2)
        self.assertEqual(self.tree.get_freq(None), 0)
        with self.assertRaises(UnknownClock):
            self.tree.get_freq("unknown clock")

    def test_is_gated(self):
        self.dev.TEST1.TESTA.A2.write(1)
        self.assertFalse(self.tree.is_gated('gate2'))
        self.assertFalse(self.tree.is_gated('div3'))

        self.dev.TEST1.TESTA.A2.write(0)
        self.assertTrue(self.tree.is_gated('gate2'))
        self.assertTrue(self.tree.is_gated('div3'))
        self.assertTrue(self.tree.is_gated(None))

    def test_build(self):
        self.assertTrue(self.tree.build())

        Divider(name='div4', tree=self.tree)
        self.assertFalse(self.tree.build())
        self.tree.clocks.pop('div4')

    def test_get_parent(self):
        div3 = self.tree.get('div3')
        gate2 = div3.get_parent()
        div2 = gate2.get_parent()
        mux1 = div2.get_parent()
        osc = mux1.get_parent()

        self.assertEqual(gate2.name, 'gate2')
        self.assertEqual(div2.name, 'div2')
        self.assertEqual(mux1.name, 'mux1')
        self.assertEqual(osc.name, 'osc3')

    def test_get_orphans(self):
        orphans = self.tree.get_orphans()
        self.assertEqual(len(orphans), 3)
        self.assertIn('osc1', orphans)

    def test_get_children(self):
        children = self.tree.get_children("gate2")
        self.assertEqual(len(children), 1)
        self.assertIn('div3', children)

        children = self.tree.get_children("div2")
        self.assertEqual(len(children), 1)
        self.assertIn('gate2', children)

        children = self.tree.get_children("osc1")
        self.assertEqual(len(children), 2)
        self.assertIn('mux1', children)

    def test_make_tree(self):
        tree = self.tree.make_tree()
        self.assertIn('osc1', tree)
        self.assertIn('div1', tree['osc1'])
        self.assertIn('gate1', tree['osc1']['div1'])
        self.assertNotIn('mux1', tree['osc1'])
        self.assertNotIn('mux1', tree['osc2'])
        self.assertIn('mux1', tree['osc3'])

def run_tests(module):
    return unittest.main(module=module, exit=False).result

if __name__ == '__main__':
    unittest.main()
