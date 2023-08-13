# homeassistant_cisco_ewc
A presence detection plugin for Cisco Embedded Wireless Controllers

## Overview
99% ripped from @fbradyirl's cisco_ios HA integration.  I changed a few lines to get the list of associated wireless clients and made modifications to select the proper fields.

## Requirements
Your homeassistant must be able to connect to the embedded wireless controller via SSH.

## Recommendations
Create a read-only user on your EWC for homeassistant

## Installation
- Create a <code>cisco_ewc</code> directory under your <code>custom_components</code> directory.
- Upload the three files from the repo, or pull from github.

## Configuration
Add some lines to <code>configuration.yaml</code>
<pre>
device_tracker:
  - platform: cisco_ewc
    host: 192.168.1.6
    username: presence
    password: Presenc3
    interval_seconds: 120 # optional, default 12 seconds (seems abusive)
    port: 22 # optional, default 22</pre>
