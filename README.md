# README #

Diese Software dient der Mitgliederverwaltung der JUSO Schweiz.

### What is this repository for? ###

In diesem Repository befindet sich der Sourcecode, der das Sektionsportal betreibt.
Die Software darf gemäss der GPLv3 verbreitet, verwendet und verteilt werden.

## Installation ###
Das Repository herunterladen und an einem beliebigen Ort entpacken.

Dann ein Virtualenvironment erzeugen und aktivieren, in dieses die benögiten PIP-Pakete installieren:

```
virtualenv env
source env/bin/activate
pip install -r requirements.txt
```
Dann im Unterordner `mysite` die Datei `local_settings.py` erstellen und notwendige Einstellungen vornehmen:
```
SECRET_KEY = ''
```
Ein geheimer Schlüssel.
```
STATIC_ROOT = '/var/www/static'
STATIC_URL = '/static/'
```

Der Ablageort für die Statischen Dateien, die von einem Webserver bereitgestellt werden und die URL, unter der die Dateien bereitgestellt werden.
```
MEDIA_ROOT = '/var/www/media'
MEDIA_URL = '/media/'
```
Der Ablageort für die Benutzer-Dateien, die von einem Webserver bereitgestellt werden und die URL, unter der die Dateien bereitgestellt werden.
```
ALLOWED_HOSTS = ['localhost', '172.0.0.1']
```
Die Addresse(n), unter der die Anwendung verfügbar sein soll.

Einstellungen für den [Mail-Versand](https://docs.djangoproject.com/en/2.0/ref/settings/#std:setting-EMAIL_HOST) kommen ebenfalls in diese Datei.

Gewisse Aufgaben brauchen lange Zeit, diese werden vom Portal im Hintegrund ausgeführt, dafür
müssen wir `Redis` und `Celery` installieren und einrichten. [Redis](https://redis.io/) kümmert sich um die Ausführung im Hintegrund, [Celery](http://www.celeryproject.org/) ist die Verbindung zwischen Redis und dem Portal.
Celery wurde bereits über pip installiert, wir benötigen nur noch Redis. Redis kann entweder über die Pakteveraltung oder direkt aus dem Source-Code installiert werden. Anleitungen dazu gibt es auf der Homepage von Redis. Redis kann entweder über einen TCP-Port kommunizieren oder über ein Socket-File, beides funktioniert mit dem Portal. Die Einstellungen dazu werden wiederum in der Datei `local_settings.py` getätigt und können z. B so aussehen:
```
CELERY_BROKER_URL = 'redis://localhost:6379'

CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

CELERY_TASK_SERIALIZER = 'json'

CELERY_ACCEPT_CONTENT = ['json']

CELERY_RESULT_BACKEND = 'django-cache'
```
Fall Redis über ein Socket kommuniziert sieht der Anfang hingegen so aus:
```
CELERY_BROKER_URL = 'redis+socket://path/to/socket.sock'
```
Jetzt müssen Celery und Redis gestartet werden. Am besten funktioniert das mit Systemd oder ähnlich.
Zu testzecken können celery und redis auch direkt im Terminal gestartet werden:
```
redis-server
celery worker -A mysite
```
Anleitungen zum einrichten von Celery finden sich auf der [Projektseite](http://docs.celeryproject.org/en/latest/userguide/daemonizing.html).

#### Datenbank
Die Datenbankkonfiguration erfolgt gemäss dieser Anleitung wieder in der Datei `local_settings.py`.
Als nächstes müssen die Datenbanktabellen eingerichet werden:
```
python manage.py migrate
```
Um auf die Anwendung zugreien zu können, müssen wir noch einen Admin-User einrichten:
```
python manage.py createsuperuser
```

### Favicon
Das Favicon kann in der Datei `mportal/templates/mportal/favicon.html` geändert werden.

### Server
Für die Verwendung in der Produktion brauchen wir einen Server, der die Applikation bereitstellt.
Dazu eignet sich zum Beispiel [Apache](http://apache.org/). Hinweise zur Einrichtung git es auf der [Django-Website](https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/modwsgi/). Eine Konfiguration kann so aussehen:
```
WSGIProcessGroup portal
WSGIDaemonProcess portal python-home=PATH/mportal/env/ python-path=PATH/mportal/
WSGIScriptAlias / PATH/mportal/mysite/wsgi.py process-group=portal application-group=%{GLOBAL}

WSGIImportScript PATH/mportal/mysite/wsgi.py  process-group=portal application-group=%{GLOBAL}

<Directory PATH/mportal/mysite>
	<Files wsgi.py>
		Require all granted
	</Files>
</Directory>

Alias /media/ /var/www/media/
Alias /static/ /var/www/media/

Alias /.well-known/ /var/www/.well-known/
<Directory   /var/www/vhosts/.well-known>
	Require all granted
</Directory>

<Directory  /var/www/media>
	Require all granted
</Directory>

<Directory /var/www/static>
	Require all granted
</Directory>
```
Nachdem wir mit dem Befehl 
```
python manage.py collectstatic
```
Alle statischen Dateien gesammelt haben, sollte die Anwendung unter dem eingerichteten Server verfügbar sein.

