#!/usr/bin/env python3
"""Check ASIO device availability"""

import os
# CRITICAL: Enable ASIO BEFORE importing sounddevice
os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd

# Get all devices
devices = sd.query_devices()
host_apis = sd.query_hostapis()

print("=== ALL HOST APIs ===")
for i, api in enumerate(host_apis):
    print(f"{i}: {api['name']}")
print()

print("=== ASIO DEVICES ===")
asio_found = False
for i, d in enumerate(devices):
    hostapi = host_apis[d['hostapi']]
    if 'ASIO' in hostapi['name'].upper():
        asio_found = True
        print(f"Device {i}: {d['name']}")
        print(f"  Host API: {hostapi['name']}")
        print(f"  Max inputs: {d['max_input_channels']}, Max outputs: {d['max_output_channels']}")
        print()

if not asio_found:
    print("NO ASIO DEVICES FOUND!")
    print()

print("=== Audio 4 DJ devices ===")
for i, d in enumerate(devices):
    if 'Audio 4 DJ' in d['name']:
        hostapi = host_apis[d['hostapi']]
        print(f"Device {i}: {d['name']}")
        print(f"  Host API: {hostapi['name']}")
        print(f"  Max inputs: {d['max_input_channels']}, Max outputs: {d['max_output_channels']}")
        print()

print(f"Device 16: {devices[16]['name']}")
print(f"Host API: {host_apis[devices[16]['hostapi']]['name']}")

# Look for devices that have both input and output
print("\n=== DEVICES WITH BOTH INPUT AND OUTPUT ===")
for i, d in enumerate(devices):
    if d['max_input_channels'] > 0 and d['max_output_channels'] > 0:
        hostapi = host_apis[d['hostapi']]
        is_asio = 'ASIO' in hostapi['name'].upper()
        print(f"Device {i}: {d['name']} {'[ASIO]' if is_asio else ''}")
        print(f"  Host: {hostapi['name']}")
        print(f"  In: {d['max_input_channels']}, Out: {d['max_output_channels']}")
        print()
