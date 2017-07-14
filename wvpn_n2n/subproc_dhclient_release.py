#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import shutil
import subprocess
from subproc_common import UtilNewMountNamespace


assert len(sys.argv) == 4
tmpDir = sys.argv[1]
cfgf = sys.argv[2]
vpnIntfName = sys.argv[3]

selfDir = os.path.dirname(os.path.realpath(__file__))
tmpEtcDhcpDir = os.path.join(tmpDir, "etc-dhcp-release")
pidFile = os.path.join(tmpDir, "dhclient.pid")
leaseFile = os.path.join(tmpDir, "dhclient.leases")
proc = None

try:
    os.mkdir(tmpEtcDhcpDir)
    with UtilNewMountNamespace():
        # dhclient read custom scripts from the fixed location /etc/dhcp
        # this behavior sucks so we use mount namespace to workaround it
        subprocess.check_call(["/bin/mount", "--bind", tmpEtcDhcpDir, "/etc/dhcp"])

        cmd = "/sbin/dhclient "
        cmd += "-r "
        cmd += "-pf %s " % (pidFile)
        cmd += "-cf %s " % (cfgf)
        cmd += "-lf %s " % (leaseFile)
        cmd += "%s >%s 2>&1" % (vpnIntfName, os.path.join(tmpDir, "dhclient-release.out"))

        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)
        proc.wait()
finally:
    shutil.rmtree(tmpEtcDhcpDir)
