import pytest
import os
import subprocess
import sys
myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')
import networkd_dispatcher


@pytest.fixture()
def get_input(request):
    """
    Returns contents of the file at tests/inputs/<function name>
    as a string
    """
    in_file = os.path.join('tests', 'inputs', request.function.__name__)
    assert os.path.exists(in_file)
    with open(in_file) as fh:
        in_txt = fh.read()
    assert in_txt != ""
    return in_txt


def test_get_networkctl_status(monkeypatch, get_input):
    expected = {'Link File': ['/etc/systemd/network/10-wifi.link'],
                'Network File': ['/etc/systemd/network/20-wifi.network'],
                'Type': 'wlan', 'State': ['routable (configured)'],
                'Path': ['pci-0000:3a:00.0'], 'Driver': ['iwlwifi'],
                'Vendor': ['Intel Corporation'],
                'Model': ['Wireless 8265 / 8275 (Dual Band Wireless-AC 8265)'],
                'HW Address': ['dd:ee:aa:dd:12:34 (Intel Corporate)'],
                'Address': ['1.1.1.100'], 'Gateway': ['1.1.1.1'],
                'DNS': ['10.10.10.1']}
    monkeypatch.setattr(subprocess, 'check_output',
                        lambda cmd: get_input.encode('utf-8'))
    assert networkd_dispatcher.get_networkctl_status('wlan0') == expected


def test_unquote():
    str = '\\ssid\\awesome'
    assert networkd_dispatcher.unquote(str) == 'ssidawesome'


def test_get_networkctl_list(monkeypatch, get_input):
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
                        lambda cmd: get_input.encode('utf-8'))
    assert networkd_dispatcher.get_networkctl_list() == expected


def test_get_wlan_ssid(monkeypatch, caplog):
    iface = 'wlp0s1'
    monkeypatch.setattr('networkd_dispatcher.IWCONFIG', None)
    monkeypatch.setattr('networkd_dispatcher.IW', None)
    assert networkd_dispatcher.get_wlan_essid(iface) is ''
    _, _, err = caplog.record_tuples[0]
    assert err == ("Unable to retrieve ESSID for wireless "
                   "interface " + iface + ": no supported wireless tool "
                   "installed")


def test_get_wlan_ssid_iwconfig(monkeypatch, get_input):
    expected = 'OMG_ssid'
    monkeypatch.setattr('networkd_dispatcher.IW', None)
    monkeypatch.setattr('networkd_dispatcher.IWCONFIG', '/usr/bin/iwconfig')
    monkeypatch.setattr(subprocess, 'check_output',
                        lambda cmd: get_input.encode('utf-8'))
    assert networkd_dispatcher.get_wlan_essid('wlan0') == expected


def test_get_wlan_ssid_iw(monkeypatch, get_input):
    expected = 'ssid123'
    monkeypatch.setattr('networkd_dispatcher.IW', '/usr/bin/iw')
    monkeypatch.setattr('networkd_dispatcher.IWCONFIG', None)
    monkeypatch.setattr(subprocess, 'check_output',
                        lambda cmd: get_input.encode('utf-8'))
    assert networkd_dispatcher.get_wlan_essid('wlan0') == expected
