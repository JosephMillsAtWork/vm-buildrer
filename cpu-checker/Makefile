VERSION=0.2
SCRIPTS=check-bios-nx kvm-ok

all:
	@# nothing to build, it's all scripts

install:
	for i in $(SCRIPTS); do \
		install -D -m 755 $$i $(DESTDIR)/usr/sbin/$$i; \
		install -D -m 644 $$i.1 $(DESTDIR)/usr/share/man/man1/$$i.1; \
	done

tarball:
	mkdir cpu-checker-$(VERSION)
	for i in $(SCRIPTS); do \
		cp -a $$i cpu-checker-$(VERSION)/; \
		cp -a $$i.1 cpu-checker-$(VERSION)/; \
	done
	cp -a Makefile test old update-notifier cpu-checker-$(VERSION)/
	tar --exclude test --exclude old --exclude update-notifier -czf ../cpu-checker-$(VERSION).tar.gz cpu-checker-$(VERSION)
	rm -rf cpu-checker-$(VERSION)
