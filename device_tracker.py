"""Support for Cisco IOS Routers."""
from __future__ import annotations

import logging
import re

from pexpect import pxssh
import voluptuous as vol

from homeassistant.components.device_tracker import (
    DOMAIN,
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    DeviceScanner,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.All(
    PARENT_PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_HOST): cv.string,
            vol.Required(CONF_USERNAME): cv.string,
            vol.Optional(CONF_PASSWORD, default=""): cv.string,
            vol.Optional(CONF_PORT, default=22): cv.port,
        }
    )
)


def get_scanner(hass: HomeAssistant, config: ConfigType) -> CiscoDeviceScanner | None:
    """Validate the configuration and return a Cisco scanner."""
    scanner = CiscoDeviceScanner(config[DOMAIN])

    return scanner if scanner.success_init else None


class CiscoDeviceScanner(DeviceScanner):
    """Class which queries a wireless controller running Cisco IOS firmware."""

    def __init__(self, config):
        """Initialize the scanner."""
        self.host = config[CONF_HOST]
        self.username = config[CONF_USERNAME]
        self.port = config.get(CONF_PORT)
        self.password = config[CONF_PASSWORD]

        self.last_results = {}

        self.success_init = self._update_info()
        _LOGGER.info("Initialized cisco_ewc scanner")

    def get_device_name(self, device):
        """Get the firmware doesn't save the name of the wireless device."""
        return None

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()

        return self.last_results

    def _update_info(self):
        """Ensure the information from the Cisco controller is up to date.

        Returns boolean if scanning successful.
        """
        if string_result := self._get_client_data():
            self.last_results = []
            last_results = []

            lines_result = string_result.splitlines()
            
            for line in lines_result:
                parts = line.split()
                if len(parts) != 8:
                    continue

                # ['d34d.b33f.caff', 'APname', 'WLAN', 'WLANid', 'State',
                # 'freq', 'None', 'Local']
                state = parts[4]
                hw_addr = parts[0]

                if state == "Run":
                    mac = _parse_cisco_mac_address(hw_addr)
                    last_results.append(mac)
                    
            self.last_results = last_results
            return True

        return False

    def _get_client_data(self):
        """Open connection to the controller and get wireless client entries."""

        try:
            cisco_ssh = pxssh.pxssh()
            cisco_ssh.login(
                self.host,
                self.username,
                self.password,
                port=self.port,
                auto_prompt_reset=False,
            )

            # Find the hostname
            initial_line = cisco_ssh.before.decode("utf-8").splitlines()
            router_hostname = initial_line[len(initial_line) - 1]
            router_hostname += ">"
            # Set the discovered hostname as prompt
            regex_expression = f"(?i)^{router_hostname}".encode()
            cisco_ssh.PROMPT = re.compile(regex_expression, re.MULTILINE)
            # Allow full client table to print at once
            cisco_ssh.sendline("terminal length 0")
            cisco_ssh.prompt(1)

            cisco_ssh.sendline("show wireless client summary")
            cisco_ssh.prompt(1)

            devices_result = cisco_ssh.before

            return devices_result.decode("utf-8")
        except pxssh.ExceptionPxssh as px_e:
            _LOGGER.error("Failed to login via pxssh: %s", px_e)

        return None


def _parse_cisco_mac_address(cisco_hardware_addr):
    """Parse a Cisco formatted HW address to normal MAC.

    e.g. convert
    001d.ec02.07ab

    to:
    00:1D:EC:02:07:AB

    Takes in cisco_hwaddr: HWAddr String from Cisco ARP table
    Returns a regular standard MAC address
    """
    cisco_hardware_addr = cisco_hardware_addr.replace(".", "")
    blocks = [
        cisco_hardware_addr[x : x + 2] for x in range(0, len(cisco_hardware_addr), 2)
    ]

    return ":".join(blocks).upper()
