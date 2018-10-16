import os
import pytest
import sys
myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')
import networkd_dispatcher


@pytest.fixture()
def scripts_etc():
    return {
        'dormant.d': [
            "/etc/networkd-dispatcher/dormant.d/92-mount-netdrive.sh",
            "/etc/networkd-dispatcher/dormant.d/80-show-status-notify.sh",
            "/etc/networkd-dispatcher/dormant.d/80-stop-vpn",
            "/etc/networkd-dispatcher/dormant.d/90-blah.sh",
            "/etc/networkd-dispatcher/dormant.d/20-stop-vpn.sh",
        ],
        'no-carrier.d': [
            "/etc/networkd-dispatcher/no-carrier.d/display-notification",
        ],
        'off.d': [
            "/etc/networkd-dispatcher/off.d/00-stop-net-services.sh",
        ],
        'routable.d': [
            "/etc/networkd-dispatcher/routable.d/enable-tracking-service.sh",
            "/etc/networkd-dispatcher/routable.d/19-whatever.sh",
            "/etc/networkd-dispatcher/routable.d/99-not-important.sh",
            "/etc/networkd-dispatcher/routable.d/50-start-netdrive",
        ],
        }


@pytest.fixture()
def scripts_usr():
    return {
        'dormant.d': [
            "/usr/lib/networkd-dispatcher/dormant.d/92-mount-netdrive.sh",
        ],
        'no-carrier.d': [
            "/usr/lib/networkd-dispatcher/no-carrier.d/50-script",
            "/usr/lib/networkd-dispatcher/no-carrier.d/10-script-important.sh",
        ],
        'off.d': [
            "/usr/lib/networkd-dispatcher/off.d/20-stop-vpn.sh",
        ],
        'routable.d': [
            "/usr/lib/networkd-dispatcher/routable.d/40-enable-ntp.sh",
            "/usr/lib/networkd-dispatcher/routable.d/enable-tracking-service.sh",
        ],
    }


@pytest.fixture()
def scripts_etc_filenames():
    return {
        'dormant.d': [
            "92-mount-netdrive.sh",
            "80-show-status-notify.sh",
            "80-stop-vpn",
            "90-blah.sh",
            "20-stop-vpn.sh",
        ],
        'no-carrier.d': [
            "display-notification",
        ],
        'off.d': [
            "00-stop-net-services.sh",
        ],
        'routable.d': [
            "enable-tracking-service.sh",
            "19-whatever.sh",
            "50-start-netdrive",
            "99-not-important.sh",
        ],
        }


@pytest.fixture()
def scripts_usr_filenames():
    return {
        'dormant.d': [
            "92-mount-netdrive.sh",
        ],
        'no-carrier.d': [
            "50-script",
            "10-script-important.sh",
        ],
        'off.d': [
            "20-stop-vpn.sh",
        ],
        'routable.d': [
            "40-enable-ntp.sh",
            "enable-tracking-service.sh",
        ],
    }


@pytest.fixture()
def scripts_sorted():
    return {
        'dormant.d': [
            "/etc/networkd-dispatcher/dormant.d/20-stop-vpn.sh",
            "/etc/networkd-dispatcher/dormant.d/80-show-status-notify.sh",
            "/etc/networkd-dispatcher/dormant.d/80-stop-vpn",
            "/etc/networkd-dispatcher/dormant.d/90-blah.sh",
            "/etc/networkd-dispatcher/dormant.d/92-mount-netdrive.sh",
        ],
        'no-carrier.d': [
            "/usr/lib/networkd-dispatcher/no-carrier.d/10-script-important.sh",
            "/usr/lib/networkd-dispatcher/no-carrier.d/50-script",
            "/etc/networkd-dispatcher/no-carrier.d/display-notification",
        ],
        'off.d': [
            "/etc/networkd-dispatcher/off.d/00-stop-net-services.sh",
            "/usr/lib/networkd-dispatcher/off.d/20-stop-vpn.sh",
        ],
        'routable.d': [
            "/etc/networkd-dispatcher/routable.d/19-whatever.sh",
            "/usr/lib/networkd-dispatcher/routable.d/40-enable-ntp.sh",
            "/etc/networkd-dispatcher/routable.d/50-start-netdrive",
            "/etc/networkd-dispatcher/routable.d/99-not-important.sh",
            "/etc/networkd-dispatcher/routable.d/enable-tracking-service.sh",
        ],
    }


@pytest.fixture()
def get_networkctl_status_out():
    """ Returns some expected output
    from networkd-dispatcher.get_networkctl_status """
    return {'Link File': ['/etc/systemd/network/10-wifi.link'],
            'Network File': ['/etc/systemd/network/20-wifi.network'],
            'Type': 'wlan',
            'State': ['routable (configured)'],
            'Path': ['pci-0000:3a:00.0'],
            'Driver': ['iwlwifi'],
            'Vendor': ['Intel Corporation'],
            'Model': ['Wireless 8265 / 8275 (Dual Band Wireless-AC 8265)'],
            'HW Address': ['dd:ee:aa:dd:12:34 (Intel Corporate)'],
            'Address': ['1.1.1.100'],
            'Gateway': ['1.1.1.1'],
            'DNS': ['10.10.10.1']}


@pytest.fixture()
def get_interface_data_out():
    return {'Type': 'wlan',
            'OperationalState': 'routable',
            'AdministrativeState': 'configured',
            'Link File': ['/etc/systemd/network/10-wifi.link'],
            'Network File': ['/etc/systemd/network/20-wifi.network'],
            'State': 'routable (configured)',
            'Path': ['pci-0000:3a:00.0'],
            'Driver': ['iwlwifi'],
            'Vendor': ['Intel Corporation'],
            'Model': ['Wireless 8265 / 8275 (Dual Band Wireless-AC 8265)'],
            'HW Address': ['dd:ee:aa:dd:12:34 (Intel Corporate)'],
            'ESSID': 'whatever'}


@pytest.fixture()
def get_networkctl_list_out():
    """Returns some expected output from
    networkd_dispatcher.get_networkctl_list """
    return [
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


@pytest.fixture()
def Dispatcher_ifaces_by_name():
    return {
        'lo': networkd_dispatcher.NetworkctlListState(idx=1, name='lo',
                                                      type='loopback',
                                                      operational='carrier',
                                                      administrative='unmanaged'),
        'wlan0': networkd_dispatcher.NetworkctlListState(idx=2,
                                                         name='wlan0',
                                                         type='wlan',
                                                         operational='routable',
                                                         administrative='configured'),
        'eth0': networkd_dispatcher.NetworkctlListState(idx=3,
                                                        name='eth0',
                                                        type='eth',
                                                        operational='dormant',
                                                        administrative='configured')
    }

@pytest.fixture()
def Dispatcher_iface_names_by_idx():
    return {1: 'lo', 2: 'wlan0', 3: 'eth0'}
