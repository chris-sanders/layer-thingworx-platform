from charms.reactive import when, when_not, set_state
from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import status_set, resource_get, log
from charmhelpers.fetch import apt_install
from charmhelpers.core.host import service_start, service_restart, chownr
#from os import FileNotFoundError

import shutil
import os
import zipfile
import fileinput
import subprocess

@when_not('tomcat.installed')
def install_tomcat():
    config = hookenv.config()
    # Install tomcat
    status_set('maintenance','installing tomcat8')
    apt_install('tomcat8')
    if config['install-admin']:
      status_set('maintenance','installing tomcat8-admin')
      apt_install('tomcat8-admin')
    status_set('maintenance','')
    set_state('tomcat.installed')

@when('tomcat.installed')
@when_not('tomcat.configured')
def configure_tomcat():
    config = hookenv.config()
    status_set('maintenance','adding tomcat user')

    # Add tomcat user
    if config['install-admin']:
        for line in fileinput.input('/var/lib/tomcat8/conf/tomcat-users.xml',inplace=True):
            # Remove any previous user config
            if line.startswith('<user username="{}"'.format(config['tomcat-user'])):
                continue
            # Add ueser at end of users section
            if line.startswith("</tomcat-users>"):
                if config['install-admin']:
                    print('<user username="{}" password="{}" roles="manager,manager-gui"/>\n'.format(config['tomcat-user'],config['tomcat-passwd']),end='')
                else:
                    print('<user username="{}" password="{}" roles="manager"/>\n'.format(config['tomcat-user'],config['tomcat-passwd']),end='')
            print(line,end='')
        shutil.chown('/var/lib/tomcat8/conf/tomcat-users.xml',user='tomcat8',group='tomcat8')

    # Set JAVA_OPTS
    status_set('maintenance','configuring JAVA_OPTS')
    for line in fileinput.input('/etc/default/tomcat8',inplace=True):
            # Replace JAVA_OPTS with the recommend options
            if line.startswith('JAVA_OPTS="-Djava'):
                line = 'JAVA_OPTS="-Djava.awt.headless=true -Djava.net.preferIPv4Stack=true -Dserver -Dd64 -XX:+UseNUMA -XX:+UseConcMarkSweepGC -Dfile.encoding=UTF-8"\n' 
            if line.startswith('#AUTHBIND'):
                line = 'AUTHBIND=yes\n'
            print(line,end='')

    # Generate or update keystore
    try:
        os.remove("/var/lib/tomcat8/conf/.keystore")
    except FileNotFoundError as e:
        pass
    try:
        os.remove("/root/.keystore")
    except FileNotFoundError as e:
        pass
    status_set('maintenance','generating keystore')
    subprocess.check_call('keytool -genkey -alias tomcat8 -keyalg RSA -storepass {} -keypass {} -dname "CN=Unknown, OU=Unknown, O=Unknown, L=Unknown, S=Unknown, C=Unknown"'.format(config['tomcat-passwd'],config['tomcat-passwd']), shell=True)
    shutil.move('/root/.keystore','/var/lib/tomcat8/conf')
    shutil.chown('/var/lib/tomcat8/conf/.keystore',user='root',group='tomcat8')
    os.chmod('/var/lib/tomcat8/conf/.keystore',0o640)
    
    # Uncomment Manager element to prevent sessions from persisting across restarts
    with open('/var/lib/tomcat8/conf/context.xml','r') as inFile:
        lines = inFile.readlines()
    for index, line in enumerate(lines):
        if '<Manager pathname="" />' in line:
            if '<!--' in lines[index-1]:
                del lines[index-1]
            if '-->' in lines[index+1]:
                del lines[index+1]
    with open('/var/lib/tomcat8/conf/context.xml','w') as outFile:
        outFile.write(''.join(lines))
    shutil.chown('/var/lib/tomcat8/conf/context.xml',user='tomcat8',group='tomcat8')

    # Modify shutdown string and setup connectors
    removeSection = False
    for line in fileinput.input('/var/lib/tomcat8/conf/server.xml',inplace=True):
        if removeSection:
            if '/>' in line:
                removeSection = False
            log('1: Removing server.xml: {}'.format(line),'INFO')
            continue
        if line.strip().startswith('<Connector port="{}"'.format(config['https-port'])):
            if '/>' not in line:
                removeSection = True
            log('2: Removing server.xml: {}'.format(line),'INFO')
            continue
        if line.strip().startswith('<Connector port="{}"'.format(config['http-port'])):
            if '/>' not in line:
                removeSection = True
            log('3: Removing server.xml: {}'.format(line),'INFO')
            continue
        if line.strip().startswith('<Connector port="8080"'):
            if '/>' not in line:
                removeSection = True
            log('4: Removing server.xml: {}'.format(line),'INFO')
            continue
        if line.strip().startswith('<Server port="8005" shutdown='):
            line = '<Server port="8005" shutdown="TH!nGW0rX">\n'
        if line.strip().startswith('<Service'):
            print(line,end='')
            if not config['https-only']:
                print('''\
    <Connector port="{port}" protocol="HTTP/1.1"
               connectionTimeout="20000"
               URIEncoding="UTF-8"
               redirectPort="{redirect}" />\n'''.format(port=config['http-port'],redirect=config['https-port']),end='')
            line = '''\
    <Connector port="{port}"
               protocol="org.apache.coyote.http11.Http11NioProtocol"
               maxThreads="150" SSLEnabled="true" scheme="https" secure="true"
               keystoreFile="/var/lib/tomcat8/conf/.keystore"
               keystorePass="{passwd}" clientAuth="false" sslProtocol="TLS" />\n'''.format(port=config['https-port'],passwd=config['tomcat-passwd'])
        print(line,end='')
    shutil.chown('/var/lib/tomcat8/conf/server.xml',user='tomcat8',group='tomcat8')
    status_set('maintenance','restarting tomcat')
    service_restart('tomcat8')
    hookenv.open_port(config['https-port'],'TCP')
    if not config['https-only']:
        hookenv.open_port(config['http-port'],'TCP')
    set_state('tomcat.configured')

@when_not('thingworx-platform.installed')
@when('tomcat.configured')
def install_thingworx_platform():
    status_set('maintenance','Setting up Thingworx.war')

    # Create Thingworx directories
    STORAGEDIR = "/ThingworxStorage"
    BACKUPDIR = "/ThingworxBackupStorage"
    try:
        os.mkdir(STORAGEDIR)
        os.mkdir(BACKUPDIR)
    except OSError as e:
        if e.errno is 17:
          pass
    shutil.chown(STORAGEDIR,user='tomcat8',group='tomcat8')
    shutil.chown(BACKUPDIR,user='tomcat8',group='tomcat8')
    os.chmod(STORAGEDIR,0o775)
    os.chmod(BACKUPDIR,0o775)

    # Retreive the war file
    platform_file = resource_get('foundation-server')

    if platform_file:
      zip = zipfile.ZipFile(platform_file)
      for entry in zip.namelist():
        if 'Thingworx.war' in entry:
          rootFolder = entry.split('/')[0]
          log("War file found in " + rootFolder,'INFO')
      zip.extractall('../resources/')
      shutil.move('../resources/'+rootFolder+'/Thingworx.war','/var/lib/tomcat8/webapps/')
      shutil.chown('/var/lib/tomcat8/webapps/Thingworx.war',user='tomcat8',group='tomcat8')
      os.chmod('/var/lib/tomcat8/webapps/Thingworx.war',0o775)
    else:
      log("Add foundation-server resource, see juju attach",'ERROR')
      status_set('blocked',"Waiting for thingworkx-platform resource")
      return
      #raise ValueError('Resources missing, see juju attach')
    status_set('active',"thingworx-platform running")
    set_state('thingworx-platform.installed')
