# -*- coding: utf-8 -*-

# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and 
#                CFSworks <CFSworks@gmail.com>
#                fizzisist <fizzisist@fpgamining.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

def formatNumber(n):
  """Format a positive integer in a more readable fashion."""
  if n < 0:
    raise ValueError('can only format positive integers')
  prefixes = 'kMGTP'
  whole = str(int(n))
  decimal = ''
  i = 0
  while len(whole) > 3:
    if i + 1 < len(prefixes):
      decimal = '.%s' % whole[-3:-1]
      whole = whole[:-3]
      i += 1
    else:
      break
  return '%s%s %s' % (whole, decimal, prefixes[i])

def formatTime(seconds):
  """Take a number of seconds and turn it into a string like 32m18s"""
  minutes = int(seconds / 60)
  hours = int(minutes / 60)
  days = int(hours / 24)
  weeks = int(days / 7)
  seconds = seconds % 60
  minutes = minutes % 60
  hours = hours % 24
  days = days % 7
  
  time_string = ''
  if weeks > 0:
    time_string += '%dw' % weeks
  if days > 0:
    time_string += '%dd' % days
  if hours > 0:
    time_string += '%dh' % hours
  if minutes > 0:
    time_string += '%dm' % minutes
  if hours < 1:
    # hide the seconds when we're over an hour
    time_string += '%ds' % seconds
  
  return time_string
