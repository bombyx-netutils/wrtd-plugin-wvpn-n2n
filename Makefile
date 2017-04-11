PACKAGE_VERSION=0.0.1
prefix=/usr

all:

clean:
	fixme

install:
	install -d -m 0755 "$(DESTDIR)/$(prefix)/sbin"
	install -m 0755 fpemud-wrt "$(DESTDIR)/$(prefix)/sbin"

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib/fpemud-wrt"
	cp -r lib/* "$(DESTDIR)/$(prefix)/lib/fpemud-wrt"
	find "$(DESTDIR)/$(prefix)/lib/fpemud-wrt" -type f | xargs chmod 644
	find "$(DESTDIR)/$(prefix)/lib/fpemud-wrt" -type d | xargs chmod 755

	install -d -m 0755 "$(DESTDIR)/etc/fpemud-wrt"
	cp -r etc/* "$(DESTDIR)/etc/fpemud-wrt"
	find "$(DESTDIR)/etc/fpemud-wrt" -type f | xargs chmod 600

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib/systemd/system"
	install -m 0644 data/fpemud-wrt.service "$(DESTDIR)/$(prefix)/lib/systemd/system"

	install -d -m 0755 "$(DESTDIR)/etc/dbus-1/system.d"
	install -m 0644 data/org.fpemud.WRT.conf "$(DESTDIR)/etc/dbus-1/system.d"
	install -m 0644 data/org.fpemud.IpForward.conf "$(DESTDIR)/etc/dbus-1/system.d"

uninstall:
	rm -f "$(DESTDIR)/$(prefix)/sbin/fpemud-wrt"
	rm -f "$(DESTDIR)/$(prefix)/lib/systemd/system/fpemud-wrt.service"
	rm -f "$(DESTDIR)/$(prefix)/etc/dbus-1/system.d/org.fpemud.WRT.conf"
	rm -rf "$(DESTDIR)/$(prefix)/lib/fpemud-wrt"
	rm -rf "$(DESTDIR)/etc/fpemud-wrt"

.PHONY: all clean install uninstall
