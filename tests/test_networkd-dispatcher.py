import pytest
import os
import subprocess
import sys
myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')
import networkd_dispatcher


# Monkeypatch methods
def mp_networkctl_list_all_ifaces(cmd):
    """ Provides mock output for: networkctl list --no-pager --no-legend """

    out = (b"  1 lo               loopback           carrier     unmanaged\n"
           b"  2 wlan0            wlan               routable    configured\n"
           b"  3 eth0             eth                dormant     configured\n")
    # subprocess.check_output returns bytes
    return out


def mp_networkctl_status_single_iface(cmd):
    """
    Provides mock output for: networkctl status --no-pager --no-legend -- IFACE
    """
    out = (b'\xe2\x97\x8f 2: wlan0\n       '
           b'Link File: /etc/systemd/network/10-wifi.link\n    '
           b'Network File: /etc/systemd/network/20-wifi.network\n            '
           b'Type: wlan\n           State: routable (configured)\n            '
           b'Path: pci-0000:3a:00.0\n          Driver: iwlwifi\n          '
           b'Vendor: Intel Corporation\n           '
           b'Model: Wireless 8265 / 8275 (Dual Band Wireless-AC 8265)\n      '
           b'HW Address: dd:ee:aa:dd:12:34 (Intel Corporate)\n         '
           b'Address: 1.1.1.1\n             DNS: 10.10.10.1\n')
    return out


def test_get_networkctl_status(monkeypatch):
    expected = {'Link File': ['/etc/systemd/network/10-wifi.link'],
                'Network File': ['/etc/systemd/network/20-wifi.network'],
                'Type': 'wlan', 'State': ['routable (configured)'],
                'Path': ['pci-0000:3a:00.0'], 'Driver': ['iwlwifi'],
                'Vendor': ['Intel Corporation'],
                'Model': ['Wireless 8265 / 8275 (Dual Band Wireless-AC 8265)'],
                'HW Address': ['dd:ee:aa:dd:12:34 (Intel Corporate)'],
                'Address': ['1.1.1.1'], 'DNS': ['10.10.10.1']}
    monkeypatch.setattr(subprocess, 'check_output',
                        mp_networkctl_status_single_iface)
    assert networkd_dispatcher.get_networkctl_status('wlan0') == expected


def test_unquote():
    str = '\\ssid\\awesome'
    assert networkd_dispatcher.unquote(str) == 'ssidawesome'


def test_get_networkctl_list(monkeypatch):
    expected = [
        networkd_dispatcher.NetworkctlListState(idx=1, name='lo',
                                                type='loopback',
                                                operational='carrier',
                                                administrative='unmanaged'),
        networkd_dispatcher.NetworkctlListState(idx=2, name='wlan0',
                                                type='wlan',
                                                operational='routable',
                                                administrative='configured'),
        networkd_dispatcher.NetworkctlListState(idx=3, name='eth0',
                                                type='eth',
                                                operational='dormant',
                                                administrative='configured')
    ]

    monkeypatch.setattr(subprocess, 'check_output',
                        mp_networkctl_list_all_ifaces)
    assert networkd_dispatcher.get_networkctl_list() == expected


def test_resolve_path():
    assert (networkd_dispatcher.resolve_path('networkctl') ==
            "/usr/bin/networkctl")


def test_get_wlan_essid():
    data = networkd_dispatcher.get_wlan_essid('lo')
    assert data is not None
