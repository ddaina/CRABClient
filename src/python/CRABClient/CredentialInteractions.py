"""
Contains the logic and wraps calls to WMCore.Credential.Proxy
"""

from WMCore.Credential.Proxy import Proxy

class CredentialInteractions(object):
    '''
    CredentialInteraction

    Takes care of wrapping Proxy interaction and defining common behaviour
    for all the client commands.
    '''

    def __init__(self, serverdn, myproxy, role, group, logger):
        '''
        Constructor
        '''
        self.logger = logger
        self.defaultDelegation = {
                                  'logger':          self.logger,
                                  'vo':              'cms',
                                  'myProxySvr':      myproxy,
                                  'proxyValidity'  : '24:00',
                                  'myproxyValidity': '7',
                                  'serverDN' :       serverdn,
                                  'group' :          group,
                                  'role':            role
                                  }
        self.proxyChanged = False


    def createNewVomsProxy(self, timeleftthreshold = 0):
        """
        Handles the proxy creation:
           - checks if a valid proxy still exists
           - performs the creation if it is expired
        """
        ## TODO add the change to have user-cert/key defined in the config.
        userproxy = Proxy( self.defaultDelegation )

        proxytimeleft = 0
        self.logger.debug("Getting proxy life time left")
        # does it return an integer that indicates?
        proxytimeleft = userproxy.getTimeLeft()
        self.logger.debug("Proxy is valid: %i" % proxytimeleft)

        #if it is not expired I check if role and/or group are changed
        if not proxytimeleft < timeleftthreshold and self.defaultDelegation['role']!=None and  self.defaultDelegation['group']!=None:
            group , role = userproxy.getUserGroupAndRoleFromProxy( userproxy.getProxyFilename())
            self.defaultDelegation['role'] = self.defaultDelegation['role'] if self.defaultDelegation['role']!='' else 'NULL'
            if group != self.defaultDelegation['group'] or role != self.defaultDelegation['role']:
                self.proxyChanged = True

        #if the proxy is expired, or we changed role and/or group, we need to create a new one
        if proxytimeleft < timeleftthreshold or self.proxyChanged:
            # creating the proxy
            self.logger.debug("Creating a proxy for %s hours" % self.defaultDelegation['proxyValidity'] )
            userproxy.create()
            proxytimeleft = userproxy.getTimeLeft()

            if proxytimeleft > 0:
                self.logger.debug("Proxy created.")
            else:
                raise Exception("Problems creating proxy.")

        return userproxy.getSubject( )

    def createNewMyProxy(self, timeleftthreshold = 0):
        """
        Handles the MyProxy creation
        """
        myproxy = Proxy ( self.defaultDelegation )

        myproxytimeleft = 0
        self.logger.debug("Getting myproxy life time left for %s" % self.defaultDelegation["myProxySvr"])
        # does it return an integer that indicates?
        myproxytimeleft = myproxy.getMyProxyTimeLeft( serverRenewer = True )
        self.logger.debug("Myproxy is valid: %i" % myproxytimeleft)

        if myproxytimeleft < timeleftthreshold or self.proxyChanged:
            # creating the proxy
            self.logger.debug("Delegating a myproxy for %s days" % self.defaultDelegation['myproxyValidity'] )
            myproxy.delegate( serverRenewer = True )
            myproxytimeleft = myproxy.getMyProxyTimeLeft( serverRenewer = True )

            if myproxytimeleft > 0:
                self.logger.debug("My-proxy delegated.")
            else:
                raise Exception("Problems delegating My-proxy.")
