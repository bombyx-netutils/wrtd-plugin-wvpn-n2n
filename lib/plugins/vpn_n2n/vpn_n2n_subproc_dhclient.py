#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import shutil
import subprocess
sys.path.append('/usr/lib/fpemud-wrt')
from wrt_util import WrtUtil
from wrt_util import NewMountNamespace


assert len(sys.argv) == 4
tmpDir = sys.argv[1]
cfgf = sys.argv[2]
vpnIntfName = sys.argv[3]

tmpEtcDhcpDir = os.path.join(tmpDir, "vpn-n2n-etc-dhcp")
tmpEnterHook = os.path.join(tmpEtcDhcpDir, "dhclient-enter-hooks")
tmpExitHook = os.path.join(tmpEtcDhcpDir, "dhclient-exit-hooks")
proc = None

try:
    os.mkdir(tmpEtcDhcpDir)

    WrtUtil.shell("/bin/cp \"%s/vpn_n2n_dhclient-enter-hooks\" \"%s\"" % (os.path.dirname(os.path.realpath(__file__)), tmpEnterHook))
    WrtUtil.shell("/bin/cp \"%s/vpn_n2n_dhclient-exit-hooks\" \"%s\"" % (os.path.dirname(os.path.realpath(__file__)), tmpExitHook))
    WrtUtil.shell("/bin/chmod 0755 \"%s\"" % (tmpEnterHook))
    WrtUtil.shell("/bin/chmod 0755 \"%s\"" % (tmpExitHook))

    with NewMountNamespace():
        # dhclient read custom scripts from the fixed location /etc/dhcp
        # this behavior sucks so we use mount namespace to workaround it
        WrtUtil.shell("/bin/mount --bind \"%s\" /etc/dhcp" % (tmpEtcDhcpDir))

        cmd = "/sbin/dhclient "
        cmd += "-d --no-pid "
        cmd += "-cf %s " % (cfgf)
        cmd += "-lf %s " % (os.path.join(tmpDir, "vpn-n2n-dhclient.leases"))
        cmd += "%s >/dev/null 2>&1" % (vpnIntfName)

        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)
        proc.wait()
except KeyboardInterrupt:
    if proc is not None and not proc.poll():
        proc.terminate()
        proc.wait()
finally:
    shutil.rmtree(tmpEtcDhcpDir)
