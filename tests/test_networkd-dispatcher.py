import collections
from collections import namedtuple
import dbus
import errno
import logging
import mock
import os
import socket
import subprocess
import sys
import pytest
from mock import patch
myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')
import networkd_dispatcher
from networkd_dispatcher import (Dispatcher, NetworkctlListState, LOG_FORMAT)

try:
    from gi.repository import GLib as glib
except ImportError:
    import glib


def get_datafile(datafile):
    assert datafile is not None
    in_file = os.path.join('tests', 'inputs', datafile)
    assert os.path.exists(in_file)
    with open(in_file, 'rb') as fh:
        in_txt = fh.read()
    assert in_txt is not None
    return in_txt


def test_resolve_path(monkeypatch):
    monkeypatch.setattr(os, 'environ',
                        {'PATH': '/bin:/usr/bin:/sbin:/usr/sbin'})
    # exists
    monkeypatch.setattr(os.path, 'exists',
                        lambda x: (True if x == '/sbin/vpn' else False))
    assert networkd_dispatcher.resolve_path('vpn') == '/sbin/vpn'
    # doesn't exist
    monkeypatch.setattr(os.path, 'exists',
                        lambda x: False)
    assert networkd_dispatcher.resolve_path('vpn') is None


@patch('subprocess.check_output')
def test_get_networkctl_status(mock_subprocess, monkeypatch,
                               get_networkctl_status_out, caplog):
    # CalledProcessError
    caplog.clear()
    mock_subprocess.side_effect = (
        subprocess.CalledProcessError(-1, '/usr/bin/networkctl'))
    assert (networkd_dispatcher.get_networkctl_status('wlan0')
            == collections.defaultdict(list))
    _, _, err = caplog.record_tuples[0]
    # Python Issue #27167 ('fixed' in 3.6) changes output of CalledProcessError
    if int(''.join(sys.version.split()[0].split('.')[0:2])) < 36:
        assert err == ('Failed to get interface "wlan0" status: Command '
                       '\'/usr/bin/networkctl\' returned non-zero exit '
                       'status -1')
    else:
        assert err == ('Failed to get interface "wlan0" status: Command '
                       '\'/usr/bin/networkctl\' died with <Signals.SIGHUP: '
                       '1>.')

    # check output
    mock_subprocess.side_effect = None
    mock_subprocess.return_value = get_datafile('networkctl_status')
    assert (networkd_dispatcher.get_networkctl_status('wlan0') ==
            get_networkctl_status_out)


def test_unquote():
    str = '\\ssid\\awesome'
    assert networkd_dispatcher.unquote(str) == 'ssidawesome'


@patch('subprocess.check_output')
def test_get_networkctl_list(mock_subprocess, monkeypatch,
                             get_networkctl_list_out, caplog):
    mock_subprocess.return_value = get_datafile('networkctl_list')
    assert networkd_dispatcher.get_networkctl_list() == get_networkctl_list_out
    # CalledProcessError
    caplog.clear()
    mock_subprocess.side_effect = (
        subprocess.CalledProcessError(-1, '/usr/bin/networkctl'))
    assert networkd_dispatcher.get_networkctl_list() == []
    _, _, err = caplog.record_tuples[0]
    # Python Issue #27167 ('fixed' in 3.6) changes output of CalledProcessError
    if int(''.join(sys.version.split()[0].split('.')[0:2])) < 36:
        assert err == ('networkctl list failed: Command \'/usr/bin/'
                       'networkctl\' returned non-zero exit status -1')
    else:
        assert err == ('networkctl list failed: Command \'/usr/bin/'
                       'networkctl\' died with <Signals.SIGHUP: 1>.')


@patch('networkd_dispatcher.iwconfig_get_ssid')
@patch('networkd_dispatcher.iw_get_ssid')
def test_get_wlan_ssid(mock_iw_get_ssid, mock_iwconfig_get_ssid,
                       monkeypatch, caplog):
    iface = 'wlp0s1'
    monkeypatch.setattr('networkd_dispatcher.IWCONFIG', None)
    monkeypatch.setattr('networkd_dispatcher.IW', None)
    assert networkd_dispatcher.get_wlan_essid(iface) == ''
    _, _, err = caplog.record_tuples[0]
    assert err == ("Unable to retrieve ESSID for wireless "
                   "interface " + iface + ": no supported wireless tool "
                   "installed")
    # iw exists
    monkeypatch.setattr('networkd_dispatcher.IWCONFIG', None)
    monkeypatch.setattr('networkd_dispatcher.IW', '/usr/bin/iw')
    networkd_dispatcher.get_wlan_essid(iface)
    mock_iw_get_ssid.assert_called_with(iface)
    # iwconfig exists
    monkeypatch.setattr('networkd_dispatcher.IW', None)
    monkeypatch.setattr('networkd_dispatcher.IWCONFIG', '/usr/bin/iwconfig')
    networkd_dispatcher.get_wlan_essid(iface)
    mock_iwconfig_get_ssid.assert_called_with(iface)


def test_iwconfig_get_ssid(monkeypatch):
    expected = 'OMG_ssid'
    monkeypatch.setattr('networkd_dispatcher.IW', None)
    monkeypatch.setattr('networkd_dispatcher.IWCONFIG', '/usr/bin/iwconfig')
    monkeypatch.setattr(subprocess, 'check_output',
                        lambda cmd: get_datafile('iwconfig'))
    assert networkd_dispatcher.get_wlan_essid('wlan0') == expected


def test_iw_get_ssid(monkeypatch, caplog):
    expected = 'ssid123'
    monkeypatch.setattr('networkd_dispatcher.IW', '/usr/bin/iw')
    monkeypatch.setattr('networkd_dispatcher.IWCONFIG', None)
    monkeypatch.setattr(subprocess, 'check_output',
                        lambda cmd: get_datafile('iw'))
    assert networkd_dispatcher.get_wlan_essid('wlan0') == expected
    # Invalid data from iw
    expected = ''
    monkeypatch.setattr(subprocess, 'check_output',
                        lambda cmd: b'')
    caplog.set_level(logging.WARNING)
    assert networkd_dispatcher.get_wlan_essid('wlan0') == expected
    _, _, warn = caplog.record_tuples[0]
    assert warn == 'Unable to retrieve ESSID for wireless interface wlan0.'


def test_scripts_in_path(monkeypatch, scripts_etc, scripts_usr,
                         scripts_etc_filenames, scripts_usr_filenames,
                         scripts_sorted, caplog):
    path = '/etc/networkd-dispatcher:/usr/lib/networkd-dispatcher'
    for subdir in ['dormant.d', 'no-carrier.d', 'off.d', 'routable.d']:
        monkeypatch.setattr(os, 'listdir',
                            lambda p: scripts_usr_filenames[subdir]
                            if p.startswith('/usr')
                            else scripts_etc_filenames[subdir])
        stat = namedtuple('stat', ('st_mode st_uid st_gid st_size st_mtime '
                          'st_atime st_ctime'))
        # file exists
        monkeypatch.setattr(os, 'stat', lambda x: stat(st_mode=33261, st_uid=0,
                                                       st_gid=0, st_size=99,
                                                       st_atime=1540220480,
                                                       st_mtime=1539272713,
                                                       st_ctime=1539272713))
        # make sure isfile returns true for files in fixtures
        monkeypatch.setattr(os.path, 'isfile', lambda x:
                            True if x in scripts_usr[subdir]
                            or x in scripts_etc[subdir] else False)
        scripts_returned = networkd_dispatcher.scripts_in_path(path, subdir)
        assert scripts_returned == scripts_sorted[subdir]
        # path does not exist
        caplog.clear()
        caplog.set_level(logging.DEBUG)
        monkeypatch.setattr(os.path, 'exists', lambda x: False)
        scripts_returned = networkd_dispatcher.scripts_in_path(path, subdir)
        assert scripts_returned == []
        _, _, debug = caplog.record_tuples[0]
        assert debug.endswith('does not exist; skipping')
        # file not executable
        caplog.clear()
        caplog.set_level(logging.ERROR)
        monkeypatch.setattr(os.path, 'exists', lambda x: True)
        monkeypatch.setattr(os, 'stat', lambda x: stat(st_mode=33152, st_uid=0,
                                                       st_gid=0, st_size=99,
                                                       st_atime=1540220480,
                                                       st_mtime=1539272713,
                                                       st_ctime=1539272713))
        scripts_returned = networkd_dispatcher.scripts_in_path(path, subdir)
        assert scripts_returned == []
        _, _, err = caplog.record_tuples[0]
        assert err.startswith('Unable to execute script, check file mode: ')
        # file not owned by root
        caplog.clear()
        caplog.set_level(logging.ERROR)
        monkeypatch.setattr(os.path, 'exists', lambda x: True)
        monkeypatch.setattr(os, 'stat', lambda x: stat(st_mode=33261,
                                                       st_uid=1000,
                                                       st_gid=1000, st_size=99,
                                                       st_atime=1540220480,
                                                       st_mtime=1539272713,
                                                       st_ctime=1539272713))
        scripts_returned = networkd_dispatcher.scripts_in_path(path, subdir)
        assert scripts_returned == []
        _, _, err = caplog.record_tuples[0]
        assert err.startswith('Unable to execute script, check file perms: ')



def test_parse_address_strings():
    addrs = ['123.321.132.312',
             '127.0.0.1',
             '1.0.1.1',
             'fe80::b2c0:90ff:fe60:861d',
             'feed::82c9:7bbf:ae39:8ff0',
             '192.168.1.254',
             'deeb::7bb8:f2c9:8ff0:ae39']
    ipv4addrs, ipv6addrs = networkd_dispatcher.parse_address_strings(addrs)
    assert ipv4addrs is not None or ipv6addrs is not None
    for addr in ipv4addrs:
        assert not addr.startswith('127.')
        assert ':' not in addr
        assert '.' in addr
    for addr in ipv6addrs:
        assert not addr.startswith('fe80:')
        assert '.' not in addr
        assert ':' in addr


def test_get_interface_data(monkeypatch, get_networkctl_status_out,
                            get_interface_data_out):
    iface = NetworkctlListState(idx='1', name='wlan0',
                                type='wlan',
                                operational='routable',
                                administrative='configured')
    monkeypatch.setattr('networkd_dispatcher.get_networkctl_status',
                        lambda x: get_networkctl_status_out)
    monkeypatch.setattr(subprocess, 'check_output',
                        lambda cmd: get_datafile('iwconfig'))
    out = networkd_dispatcher.get_interface_data(iface)
    assert out != get_interface_data_out


@patch('socket.socket')
def test_sd_notify(mock_socket, monkeypatch, caplog):
    # no state specified
    assert networkd_dispatcher.sd_notify() == -errno.EINVAL
    # not invoked with systemd
    monkeypatch.setattr('os.environ.get',
                        lambda x, y: '')
    assert networkd_dispatcher.sd_notify(READY=1) == -errno.EINVAL
    # invalid NOTIFY_SOCKET
    monkeypatch.setattr('os.environ.get',
                        lambda x, y: 'whatever')
    assert networkd_dispatcher.sd_notify(READY=1) == -errno.EINVAL
    # invoked with systemd and valid state (NOTIFY_SOCKET starts with /)
    monkeypatch.setattr('os.environ.get',
                        lambda x, y: '/var/run/dbus/system_bus_socket')
    mock_socket.return_value = socket.socket
    mock_socket.sendto.return_value = 0
    assert networkd_dispatcher.sd_notify(READY=1) == 0
    mock_socket.assert_called_with(socket.AF_UNIX, socket.SOCK_DGRAM)
    mock_socket.sendto.assert_called_with(bytearray(b'READY=1'),
                                          '/var/run/dbus/system_bus_socket')
    mock_socket.close.assert_called_with()
    # invoked with systemd and valid state (NOTIFY_SOCKET starts with @)
    monkeypatch.setattr('os.environ.get',
                        lambda x, y: '@systemd-networkd')
    assert networkd_dispatcher.sd_notify(READY=1) == 0
    mock_socket.assert_called_with(socket.AF_UNIX, socket.SOCK_DGRAM)
    mock_socket.sendto.assert_called_with(bytearray(b'READY=1'),
                                          '\x00systemd-networkd')
    mock_socket.close.assert_called_with()
    # socket.sendto error
    monkeypatch.setattr('os.environ.get',
                        lambda x, y: '@systemd-networkd')
    mock_socket.sendto.return_value = 1
    assert networkd_dispatcher.sd_notify(READY=1) == 1
    # Exceptions
    mock_socket.side_effect = Exception()
    monkeypatch.setattr('os.environ.get',
                        lambda x, y: '@systemd-networkd')
    caplog.clear()
    networkd_dispatcher.sd_notify(READY=1)
    _, _, ex = caplog.record_tuples[0]
    assert ex == 'Ignoring unexpected error during sd_notify() invocation'


# In order to test Dispatcher, the call to _interface_scan should be mocked
# since this runs in __init__
with patch.object(networkd_dispatcher.Dispatcher, "_interface_scan",
                  lambda x: None):
    class TestDispatcher():
        dp = Dispatcher()

        def test__interface_scan(self, monkeypatch, get_networkctl_list_out,
                                 Dispatcher_ifaces_by_name,
                                 Dispatcher_iface_names_by_idx, caplog):
            monkeypatch.setattr('networkd_dispatcher.get_networkctl_list',
                                lambda: get_networkctl_list_out)
            caplog.set_level(logging.DEBUG)
            self.dp._interface_scan()
            assert self.dp.ifaces_by_name == Dispatcher_ifaces_by_name
            assert self.dp.iface_names_by_idx == Dispatcher_iface_names_by_idx
            _, _, debug = caplog.record_tuples[0]
            assert debug == ('Performed interface scan; state: <Dispatcher({'
                             '\'script_dir\': \'/etc/networkd-dispatcher:/usr'
                             '/lib/networkd-dispatcher\'})>')

        @patch('dbus.SystemBus')
        @patch('dbus.bus.BusConnection')
        def test_register(self, mock_dbus_bus, mock_dbus_SystemBus):
            mock_dbus_SystemBus.return_value = mock.MagicMock()
            self.dp.register(bus=None)
            mock_dbus_SystemBus.assert_called_with()

        @patch('networkd_dispatcher.Dispatcher.handle_state')
        def test_trigger_all(self, mock_hs, monkeypatch, caplog):
            iface = NetworkctlListState(idx='1',
                                        name='wlan0',
                                        type='wlan',
                                        operational='routable',
                                        administrative='configured')
            monkeypatch.setattr(('networkd_dispatcher.Dispatcher'
                                 '.ifaces_by_name'), {'wlan0': iface})
            mock_hs.return_value = None
            self.dp.trigger_all()
            mock_hs.assert_called_with('wlan0',
                                       administrative_state='configured',
                                       operational_state='routable',
                                       force=True)
            # invalid iface
            monkeypatch.setattr(('networkd_dispatcher.Dispatcher'
                                 '.ifaces_by_name'), {'eth0': 1})
            caplog.clear()
            caplog.set_level(logging.WARNING)
            self.dp.trigger_all()
            _, _, ex = caplog.record_tuples[0]
            assert ex == 'Error handling initial for interface 1'

        @patch('networkd_dispatcher.Dispatcher.run_hooks_for_state')
        def test__handle_one_state(self, mock_run_hooks_for_state,
                                   monkeypatch, caplog):
            monkeypatch.setattr(('networkd_dispatcher.Dispatcher'
                                 '.ifaces_by_name'), {})
            # None state
            assert self.dp._handle_one_state(self, None, None, None) is None
            # None for prior iface
            assert (self.dp._handle_one_state('wlan0', 'routable', None, None)
                    is None)
            _, _, err = caplog.record_tuples[0]
            assert err == ('Attempting to handle state for unknown interface '
                           '\'wlan0\'')
            # No state change
            caplog.clear()
            caplog.set_level(logging.DEBUG)
            iface = NetworkctlListState(idx='1',
                                        name='wlan0',
                                        type='wlan',
                                        operational='routable',
                                        administrative='configured')
            monkeypatch.setattr(('networkd_dispatcher.Dispatcher'
                                 '.ifaces_by_name'), {'wlan0': iface})
            assert (self.dp._handle_one_state('wlan0', 'routable',
                                              'operational', force=False)
                    is None)
            _, _, debug = caplog.record_tuples[0]
            assert debug == (('No change represented by operational state '
                              '\'routable\' for interface \'wlan0\''))
            # Force update
            caplog.clear()
            mock_run_hooks_for_state.return_value = True
            assert (self.dp._handle_one_state('wlan0', 'routable',
                                              'operational', force=True)
                    is None)
            mock_run_hooks_for_state.assert_called_with(iface, 'routable')
            assert len(caplog.record_tuples) == 0
            # New iface state
            caplog.clear()
            mock_run_hooks_for_state.return_value = True
            assert (self.dp._handle_one_state('wlan0', 'dormant',
                                              'operational')
                    is None)
            new_iface = NetworkctlListState(idx='1',
                                            name='wlan0',
                                            type='wlan',
                                            operational='dormant',
                                            administrative='configured')
            mock_run_hooks_for_state.assert_called_with(new_iface, 'dormant')
            assert (self.dp.ifaces_by_name[new_iface.name].operational
                    == 'dormant')
            # Exceptions
            caplog.clear()
            mock_run_hooks_for_state.side_effect = Exception()
            assert (self.dp._handle_one_state('wlan0', 'routable',
                                              'operational')
                    is None)
            _, _, ex = caplog.record_tuples[0]
            assert ex == ('Error handling notification for interface '
                          '\'wlan0\' entering operational state routable')

        @patch('networkd_dispatcher.Dispatcher._handle_one_state')
        def test_handle_state(self, mock__handle_one_state, monkeypatch,
                              caplog):
            self.dp.handle_state('wlan0', 'configured', 'routable', False)
            calls = [mock.call('wlan0', 'configured', 'administrative',
                               force=False),
                     mock.call('wlan0', 'routable', 'operational',
                               force=False)]
            mock__handle_one_state.assert_has_calls(calls, any_order=False)

        @patch.object(networkd_dispatcher, 'scripts_in_path')
        def test_get_scripts_list(self, mock_scripts_in_path):
            for basedir in ['/etc/networkd-dispatcher',
                            '/usr/lib/networkd-dispatcher']:
                for subdir in ['dormant', 'no-carrier', 'off', 'routable']:
                    expected = basedir + '/' + subdir + '.d/10-blah.sh'
                    mock_scripts_in_path.return_value = expected
                    assert (self.dp.get_scripts_list(state=subdir)
                            == expected)

        @patch('subprocess.Popen')
        def test_run_hooks_for_state(self, mock_subprocess, monkeypatch,
                                     get_interface_data_out,
                                     caplog):
            e_env = {'ADDR': '', 'ESSID': 'whatever',
                     'IP_ADDRS': '123.321.132.312 1.0.1.1 192.168.1.254',
                     'IP6_ADDRS': ('feed::82c9:7bbf:ae39:8ff0 '
                                   'deeb::7bb8:f2c9:8ff0:ae39'),
                     'IFACE': 'wlan0', 'STATE': 'routable',
                     'AdministrativeState': 'configured',
                     'OperationalState': 'routable',
                     'json': ('{"AdministrativeState": "configured", '
                              '"Driver": ["iwlwifi"], "ESSID": "whatever", '
                              '"HW Address": ["dd:ee:aa:dd:12:34 (Intel '
                              'Corporate)"], "Link File": '
                              '["/etc/systemd/network/10-wifi.link"], '
                              '"Model": ["Wireless 8265 / 8275 (Dual Band '
                              'Wireless-AC 8265)"], "Network File": '
                              '["/etc/systemd/network/20-wifi.network"], '
                              '"OperationalState": "routable", "Path": '
                              '["pci-0000:3a:00.0"], "State": "routable '
                              '(configured)", "Type": "wlan", "Vendor": '
                              '["Intel Corporation"]}')}
            ipv4 = ['123.321.132.312', '1.0.1.1', '192.168.1.254']
            ipv6 = ['feed::82c9:7bbf:ae39:8ff0', 'deeb::7bb8:f2c9:8ff0:ae39']
            addrs = networkd_dispatcher.AddressList(ipv4, ipv6)
            monkeypatch.setattr('networkd_dispatcher.get_interface_data',
                                lambda x: get_interface_data_out)
            monkeypatch.setattr('networkd_dispatcher.Dispatcher.'
                                'get_scripts_list',
                                lambda x, y: (['/etc/networkd-dispatcher/'
                                              'routable.d/10openvpn']))
            monkeypatch.setattr('networkd_dispatcher.parse_address_strings',
                                lambda x: addrs)
            old_environ = os.environ
            os.environ.clear()
            self.dp.run_hooks_for_state(self.dp.ifaces_by_name['wlan0'],
                                        'routable')
            mock_subprocess.assert_called_with(('/etc/networkd-dispatcher/'
                                                'routable.d/10openvpn'),
                                               env=e_env)
            # bad exit status from script
            mock_subprocess.wait.return_value = -1
            os.environ = old_environ
            caplog.clear()
            self.dp.run_hooks_for_state(self.dp.ifaces_by_name['wlan0'],
                                        'routable')
            caplog.set_level(logging.WARNING)
            _, _, warn = caplog.record_tuples[0]
            assert not warn.startswith('Exist status')
            # no scripts
            monkeypatch.setattr(Dispatcher, 'get_scripts_list',
                                lambda x, y: None)
            caplog.clear()
            caplog.set_level(logging.DEBUG)
            assert self.dp.run_hooks_for_state(self.dp.ifaces_by_name['wlan0'],
                                               'routable') is None
            _, _, debug = caplog.record_tuples[0]
            assert debug == ('Ignoring notification for interface '
                             'NetworkctlListState(idx=2, name=\'wlan0\', '
                             'type=\'wlan\', operational=\'routable\', '
                             'administrative=\'configured\') entering state '
                             '\'routable\': no triggers')

        @patch.object(networkd_dispatcher.Dispatcher, 'handle_state')
        @patch.object(networkd_dispatcher.Dispatcher, '_interface_scan')
        def test__receive_signal(self, mock_interface_scan, mock_handle_state,
                                 caplog):
            self.dp.ifaces_by_name = {'lo':
                                      NetworkctlListState(idx=1,
                                                          name='lo',
                                                          type='loopback',
                                                          operational='carrier',
                                                          administrative='unmanaged'),
                                      'eth0': NetworkctlListState(idx=3,
                                                                  name='eth0',
                                                                  type='eth',
                                                                  operational='dormant',
                                                                  administrative='configured')}
            # invalid typ
            caplog.clear()
            caplog.set_level(logging.DEBUG)
            assert (self.dp._receive_signal('org.freedesktop.'
                                            'whatever', '',
                                            '', '')
                    is None)
            _, _, debug = caplog.record_tuples[1]
            assert 'Ignoring signal received with unexpected typ' in debug
            # invalid path
            caplog.clear()
            caplog.set_level(logging.DEBUG)
            assert (self.dp._receive_signal('org.freedesktop.'
                                            'network1.Link',
                                            '', None,
                                            '/org/freedesktop/whatever')
                    is None)
            _, _, debug = caplog.record_tuples[1]
            assert 'Ignoring signal received with unexpected path' in debug
            # unknown iface idx seen
            caplog.clear()
            caplog.set_level(logging.DEBUG)
            self.dp.iface_names_by_idx = {}
            mock_interface_scan.return_value = {1: 'lo', 2: 'eth0', 3: 'wlan0'}
            assert (self.dp._receive_signal('org.freedesktop.'
                                            'network1.Link',
                                            '', None,
                                            '/org/freedesktop/network1/'
                                            'link/_33')
                    is None)
            _, _, warn = caplog.record_tuples[1]
            assert warn == 'Unknown index 3 seen, reloading interface list'
            mock_interface_scan.assert_called_with()
            # unknown iface idx even after reload
            caplog.clear()
            mock_interface_scan.return_value = {1: 'lo', 2: 'eth0'}
            assert (self.dp._receive_signal('org.freedesktop.'
                                            'network1.Link',
                                            '', None,
                                            '/org/freedesktop/network1/'
                                            'link/_33')
                    is None)
            _, _, warn = caplog.record_tuples[2]
            mock_interface_scan.assert_called_with()
            assert warn == 'Unknown interface index 3 seen even after reload'
            # handle_state called with right things
            self.dp.iface_names_by_idx = {1: 'lo', 2: 'eth0', 3: 'wlan0'}
            data = dbus.Dictionary(
                {dbus.String('OperationalState'):
                 dbus.String('routable', variant_level=1)},
                signature=dbus.Signature('sv'))
            assert (self.dp._receive_signal('org.freedesktop.'
                                            'network1.Link',
                                            data, None,
                                            '/org/freedesktop/network1/'
                                            'link/_33')
                    is None)
            mock_handle_state.assert_called_with('wlan0',
                                                 administrative_state=None,
                                                 operational_state='routable')
            # remove ifaces (ifaces_by_name and iface_names_by_idx pop'd)
            self.dp.iface_names_by_idx = {1: 'lo', 2: 'eth0', 3: 'wlan0'}
            data = dbus.Dictionary(
                {dbus.String('AdministrativeState'):
                 dbus.String('linger', variant_level=1)},
                signature=dbus.Signature('sv'))
            assert (self.dp._receive_signal('org.freedesktop.'
                                            'network1.Link',
                                            data, None,
                                            '/org/freedesktop/network1/'
                                            'link/_33')
                    is None)
            mock_handle_state.assert_called_with('wlan0',
                                                 administrative_state='linger',
                                                 operational_state=None)
            _, _, warn = caplog.record_tuples[1]
            assert warn == 'Unknown index 3 seen, reloading interface list'
            assert 3 not in self.dp.iface_names_by_idx.keys()
            assert 'wlan0' not in self.dp.ifaces_by_name.keys()
            # keyerror when removing iface
            caplog.clear()
            self.dp.iface_names_by_idx = {1: 'lo', 2: 'eth0', 3: 'wlan0'}
            data = dbus.Dictionary(
                {dbus.String('AdministrativeState'):
                 dbus.String('linger', variant_level=1)},
                signature=dbus.Signature('sv'))
            self.dp.ifaces_by_name = {}
            assert (self.dp._receive_signal('org.freedesktop.'
                                            'network1.Link',
                                            data, None,
                                            '/org/freedesktop/network1/'
                                            'link/_33')
                    is None)
            mock_handle_state.assert_called_with('wlan0',
                                                 administrative_state='linger',
                                                 operational_state=None)
            _, _, err = caplog.record_tuples[1]
            assert err == 'Unable to remove interface at index 3.'


@patch('networkd_dispatcher.main')
def test___main__(mock_main, monkeypatch):
    monkeypatch.setattr(networkd_dispatcher, '__name__', '__main__')
    networkd_dispatcher.init()
    mock_main.assert_called_with()


def test_parse_args(monkeypatch):
    # script_dir
    parser = networkd_dispatcher.parse_args(['-S', '/etc/custom'])
    assert parser.script_dir == '/etc/custom'
    # trigger-all
    parser = networkd_dispatcher.parse_args(['-T'])
    assert parser.run_startup_triggers
    # verbosity
    parser = networkd_dispatcher.parse_args(['-vvvv'])
    assert parser.verbose == 4
    # quiet
    parser = networkd_dispatcher.parse_args(['-qqqqq'])
    assert parser.quiet == 5


@patch.object(networkd_dispatcher, 'sd_notify')
@patch.object(glib, 'MainLoop')
@patch.object(logging, 'basicConfig')
@patch.object(Dispatcher, 'trigger_all')
@patch.object(Dispatcher, 'register')
@patch.object(Dispatcher, '_interface_scan')
def test_main(mock_iface_scan, mock_register, mock_trigger_all,
              mock_logging_basicconfig, mock_glib_mainloop, mock_sd_notify,
              monkeypatch, caplog):
    # networkctl is None
    monkeypatch.setattr(sys, 'argv', ['networkd-dispatcher'])
    monkeypatch.setattr(networkd_dispatcher, 'NETWORKCTL', None)
    with pytest.raises(SystemExit) as e:
        networkd_dispatcher.main()
        assert e.type == SystemExit
        mock_sd_notify.assert_called_with(ERRNO=errno.ENOENT)
        _, _, crit = caplog.record_tuples[1]
        assert crit == 'Unable to find networkctl command; cannot continue'
    monkeypatch.setattr(networkd_dispatcher, 'NETWORKCTL',
                        '/usr/bin/networkctl')
    # test verbosity config
    monkeypatch.setattr(sys, 'argv', ['networkd-dispatcher', '-v'])
    networkd_dispatcher.main()
    mock_logging_basicconfig.assert_called_with(level=logging.INFO,
                                                format=LOG_FORMAT)
    monkeypatch.setattr(sys, 'argv', ['networkd-dispatcher', '-vv'])
    networkd_dispatcher.main()
    mock_logging_basicconfig.assert_called_with(level=logging.DEBUG,
                                                format=LOG_FORMAT)
    monkeypatch.setattr(sys, 'argv', ['networkd-dispatcher', '-qqv'])
    networkd_dispatcher.main()
    mock_logging_basicconfig.assert_called_with(level=logging.ERROR,
                                                format=LOG_FORMAT)
    monkeypatch.setattr(sys, 'argv', ['networkd-dispatcher', '-vvqqqq'])
    networkd_dispatcher.main()
    mock_logging_basicconfig.assert_called_with(level=logging.CRITICAL,
                                                format=LOG_FORMAT)
    monkeypatch.setattr(sys, 'argv', ['networkd-dispatcher', '-vvqq'])
    networkd_dispatcher.main()
    mock_logging_basicconfig.assert_called_with(level=logging.WARNING,
                                                format=LOG_FORMAT)
    # run_startup_triggers
    monkeypatch.setattr(sys, 'argv', ['networkd-dispatcher', '-T'])
    networkd_dispatcher.main()
    mock_sd_notify.assert_called_with(READY=1)
    mock_trigger_all.assert_called_with()
