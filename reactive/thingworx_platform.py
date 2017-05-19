from charms.reactive import when, when_not, set_state
import os

@when_not('thingworx-platform.installed')
def install_layer_thingworx_platform():
    # Create Thingworx directories
    STORAGEDIR = "/ThingworxStorage"
    BACKUPDIR = "/ThingworkxBackupStorage"
    try:
        os.mkdir(STORAGEDIR)
        os.mkdir(BACKUPDIR)
    except OSError as e:
        if e.errno is 17:
          pass
    # TODO: Set user via relation or make independent of tomcat user
    shutil.chown(STORAGEDIR,user='tomcat7',group='tomcat7')
    shutil.chown(BACKUPDIR,user='tomcat7',group='tomcat7')
    os.chmod(STORAGEDIR,0o775)
    os.chmod(BACKUPDIR,0o775)

    # Retreive the war file
    platform_file = resource_get('thingworx-foundation-server')

    #if platform_file:
    #    shutil.copy(platform_file,privateKey)
    #    shutil.copy(public_path,publicKey)
    #else:
    #    log("Add foundation-server resource, see juju attach",'ERROR')
    #    raise ValueError('Resources missing, see juju attach')


    
    set_state('thingworx-platform.installed')
