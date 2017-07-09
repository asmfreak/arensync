all:	arensync/i18n/ru/LC_MESSAGES/arensync.mo

arensync/i18n/messages.pot: arensync/*.py
	sh -c "xgettext -L python --keyword=N_ -o $@ arensync/*.py"

arensync/i18n/new_ru.po: arensync/i18n/messages.pot arensync/i18n/ru.po
	msgmerge arensync/i18n/ru.po arensync/i18n/messages.pot > $@

arensync/i18n/ru/LC_MESSAGES/arensync.mo: arensync/i18n/new_ru.po
	mkdir -p arensync/i18n/ru/LC_MESSAGES/
	msgfmt -o $@ $<

clean:
	rm -f arensync/i18n/messages.pot arensync/i18n/new_ru.po
