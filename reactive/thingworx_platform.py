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
    # Set JAVA_OPTS
    status_set('maintenance','configuring JAVA_OPTS')
    for line in fileinput.input('/etc/default/tomcat8',inplace=True):
            # Replace JAVA_OPTS with the recommend options
            # TODO: -Dfile.encoding=UTF-8 was removed due to errors on boot, it needs to be fixed and re-added
            if line.startswith('JAVA_OPTS="-Djava'):
                line = 'JAVA_OPTS="-Djava.awt.headless=true -Djava.net.preferIPv4Stack=true -Dserver -Dd64 -XX:+UseNUMA -XX:+UseConcMarkSweepGC"\n' 
            print(line,end='')
    # Generate keystore
    # Remove any existing keystore
    try:
        os.remove("/var/lib/tomcat8/conf/.keystore")
    except FileNotFoundError as e:
        pass
    try:
        os.remove("/root/.keystore")
    except FileNotFoundError as e:
        pass
    # TODO: Look for python library instead of dropping to shell
    status_set('maintenance','generating keystore')
    subprocess.check_call('keytool -genkey -alias tomcat8 -keyalg RSA -storepass {} -keypass {} -dname "CN=Unknown, OU=Unknown, O=Unknown, L=Unknown, S=Unknown, C=Unknown"'.format(config['tomcat-passwd'],config['tomcat-passwd']), shell=True)
    shutil.move('/root/.keystore','/var/lib/tomcat8/conf')
    chownr('/var/lib/tomcat8/conf/.keystore',owner='root',group='tomcat8')
    os.chmod('/var/lib/tomcat8/conf/.keystore',0o640)
    # Uncomment Manager element to prevent sessions from persisting across restarts
    for line in fileinput.input('/var/lib/tomcat8/conf/context.xml',inplace=True):
        #TODO: Look at the default version of this file to see how to uncomment it
        if line.startswith('<Manager pathname="" />'):
            pass
        print(line,end='')
    # Modify shutdown string
    for line in fileinput.input('/var/lib/tomcat8/conf/server.xml',inplace=True):
        if line.startswith('<Server port="8005" shutdown='):
            line = '<Server port="8005" shutdown="TH!nGW0rX">\n'
        print(line,end='')
    status_set('maintenance','restarting tomcat')
    service_restart('tomcat8')
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
    # TODO: Set user via relation or make independent of tomcat user
    shutil.chown(STORAGEDIR,user='tomcat8',group='tomcat8')
    shutil.chown(BACKUPDIR,user='tomcat8',group='tomcat8')
    os.chmod(STORAGEDIR,0o775)
    os.chmod(BACKUPDIR,0o775)

    # Retreive the war file
    platform_file = resource_get('foundation-server')

    if platform_file:
      zip = zipfile.ZipFile(platform_file)
      #TODO: make independent of tomcat version
      for entry in zip.namelist():
        if 'Thingworx.war' in entry:
          rootFolder = entry.split('/')[0]
          #zip.extract(entry,'../resources/')
          log("War file found in " + rootFolder,'INFO')
        #else:
        #  log('skipping '+entry,'INFO') 
      zip.extractall('../resources/')
      shutil.move('../resources/'+rootFolder+'/Thingworx.war','/var/lib/tomcat8/webapps/')
      shutil.chown('/var/lib/tomcat8/webapps/Thingworx.war',user='tomcat8',group='tomcat8')
      os.chmod('/var/lib/tomcat8/webapps/Thingworx.war',0o775)
    else:
      log("Add foundation-server resource, see juju attach",'ERROR')
      status_set('blocked',"Waiting for thingworkx-platform resource")
      raise ValueError('Resources missing, see juju attach')
    status_set('active',"thingworx-platform running")
    set_state('thingworx-platform.installed')
