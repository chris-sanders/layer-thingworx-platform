# Overview

Describe the intended usage of this charm and anything unique about how this
charm relates to others here.

This charm provides [Thingworx Foundation Server][foundation-server]. The scope of this product is beyond what can be reasonably described here. To learn about Thingworx by PTC you should see their [Developer Portal][portal]. If you are already familiar and just want to try the Foundation Server you will need to get a copy of the trial edition. If you haven't alrady [register][register] for a developer account. After registring download the [Trial Edition][trial] and you're ready to go.

# Deploy
To deploy:

    juju deploy cs:~chris.sanders/thingworx-foundation-server

Check the status of the deploy with:

    juju status

Note the IP Address for the machine in use. By default this will get you up and running with both port 80 and port 443 available to access the tomcat instance. This is intended to let you develop locally not secured for remote or cloud deployments. See the Configuraiton options below if you want to restrict access to https traffic only.

After deployment completes, the tomcat server will load the Thingworx application which can take a minute on the first boot. Once it is ready you can access it at http://ip-address/Thingwox using the Username and Password. The admin username and password are provided in the Thingworx [Installation guide][install-guide] and at the time of this writting are

Username: Administrator

Password: admin

If you can not access the Foundation server you can check the status to see if it is running by accessing http://ip-address/manager/html, the default password for tomcat is "tomcat8" for both the user and password.

## Scale out Usage

This charm does not adderss multi-server configurations at this time.  However, you can add units to stand up multiple servers if you would like to test migrations or simply want multiple indipendent test servers.

## Known Limitations and Issues

This is a first pass at this charm, there are improvements that I would like to make but it is valuable already. Configuration parameters do not alter an already installed server. For example, chaning the HTTP port or setting the charm to HTTPS only will not have any affect on an already deployed server. This is easily addressed, and it's on my to-do list when I have time.

Note this charm is not installing ntp as recommended. When running on a local LXD this is not necessary and ntp can be easily added if your install is on meta intead of a container. If you want to add ntp in your bundle on even after deploy you can run:

  juju deploy ntp
  juju add-relation thingworx-foundation-server:ntp

# Configuration

Configuration options are fairly self explanatory at this time. If you are installing in an insecure environment you should consider setting the follwoing.

  - install-admin=False
  - https-only=True

This will not install the tomcat admin package and not configure tomcat to use port 80 so all traffic is HTTPS.

# Contact Information

## Upstream Project Name

  - https://github.com/chris-sanders/layer-thingworx-platform
  - https://github.com/chris-sanders/layer-thingworx-platform/issues
  - email: sanders.chris@gmail.com


[foundation-server]: https://developer.thingworx.com/resources/trial-editions
[portal]: https://developer.thingworx.com/
[register]: https://developer.thingworx.com/signup
[trial]: https://developer.thingworx.com/resources/trial-editions
[icon guidelines]: https://jujucharms.com/docs/stable/authors-charm-icon
