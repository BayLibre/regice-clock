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

def init_args(parser):
    """
        Add argument required to configure clocks.
    """
    parser.add_argument('--freq', action='append', metavar="NAME=VALUE",
                        help='Set the frequency of oscillator')

def process_args(device, args):
    """
        Get clock frequency from args and set it.

        :param device: A Device object, used to get / set the clock tree
        :args: Parsed args from ArgumentParser
        :return: An empty dictionary
    """
    if not args.freq:
        return {}
    for name_value in args.freq:
        mul = 1
        name, value = name_value.split('=')
        if value[-1] == 'k' or value[-1] == 'K':
            value = value[:-1]
            mul = 1000
        if value[-1] == 'm' or value[-1] == 'M':
            value = value[:-1]
            mul = 1000000
        if name in device.tree.clocks:
            clock = device.tree.get(name)
            clock.freq = float(value) * mul
    return {}
