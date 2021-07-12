"""
Handles client interactions with remote REST interface
"""

import os
import time
import random
import subprocess
from ServerUtilities import encodeRequest
import json

try:
    from urllib import quote as urllibQuote  # Python 2.X
except ImportError:
    from urllib.parse import quote as urllibQuote  # Python 3+

import logging

try:
    from TaskWorker import __version__
except:  # pylint: disable=bare-except
    try:
        from CRABClient import __version__
    except:  # pylint: disable=bare-except
        __version__ = '0.0.0'

EnvironmentException = Exception

class HTTPRequests(dict):
    """
    This code is a simplified version of WMCore.Services.Requests - we don't
    need all the bells and whistles here since data is always sent via json we
    also move the encoding of data out of the makeRequest.

    HTTPRequests does no logging or exception handling, these are managed by the
    Client class that instantiates it.

    NOTE: This class should be replaced by the WMCore.Services.JSONRequests if WMCore
    is used more in the client.
    """

    def __init__(self, hostname='localhost', localcert=None, localkey=None, version=__version__,
                 retry=0, logger=None, verbose=False, userAgent='CRAB?'):
        """
        Initialise an HTTP handler
        """
        dict.__init__(self)
        #set up defaults
        self.setdefault("host", hostname)
        # setup port 8443 for cmsweb services (leave them alone things like personal private VM's)
        if self['host'].startswith("https://cmsweb") or self['host'].startswith("cmsweb"):
            if self['host'].endswith(':8443'):
                # good to go
                pass
            elif ':' in self['host']:
                # if there is a port number already, trust it
                pass
            else:
                # add port 8443
                self['host'] = self['host'].replace(".cern.ch", ".cern.ch:8443", 1)
        self.setdefault("cert", localcert)
        self.setdefault("key", localkey)
        self.setdefault("version", version)
        self.setdefault("retry", retry)
        self.setdefault("verbose", verbose)
        self.setdefault("userAgent", userAgent)
        self.logger = logger if logger else logging.getLogger()

    def get(self, uri=None, data=None):
        """
        GET some data
        """
        return self.makeRequest(uri=uri, data=data, verb='GET')

    def post(self, uri=None, data=None):
        """
        POST some data
        """
        return self.makeRequest(uri=uri, data=data, verb='POST')

    def put(self, uri=None, data=None):
        """
        PUT some data
        """
        return self.makeRequest(uri=uri, data=data, verb='PUT')

    def delete(self, uri=None, data=None):
        """
        DELETE some data
        """
        return self.makeRequest(uri=uri, data=data, verb='DELETE')

    def makeRequest(self, uri=None, data=None, verb='GET'):
        """
        Make a request to the remote database for a given URI. The type of
        request will determine the action take by the server (be careful with
        DELETE!).

        Returns a tuple of the data from the server, decoded using the
        appropriate method, the response status and the response reason, to be
        used in error handling.

        You can override the method to encode/decode your data by passing in an
        encoding/decoding function to this method. Your encoded data must end up
        as a string.
        """

        data = data or {}

        #Quoting the uri since it can contain the request name, and therefore spaces (see #2557)
        uri = urllibQuote(uri)
        caCertPath = self.getCACertPath()
        url = 'https://' + self['host'] + uri

        #if it is a dictionary, we need to encode it to string
        if isinstance(data, dict):
            data = encodeRequest(data)

        if verb in ['GET', 'HEAD']:
            url = url + '?' + data

        command = ''
        #command below will return 2 values separated by comma: 1) curl result and 2) HTTP code
        command += 'curl -sS -w ",%{{http_code}}\\n" -f -X {0}'.format(verb)
        command += ' -H "User-Agent: %s/%s"' % (self['userAgent'], self['version'])
        command += ' -H "Accept: */*"'
        command += ' --data "%s"' % data
        command += ' --cert "%s"' % self['cert']
        command += ' --key "%s"' % self['key']
        command += ' --capath "%s"' % caCertPath
        command += ' "%s"' % url

        # retries this up at least 3 times, or up to self['retry'] times for range of exit codes
        # retries are counted AFTER 1st try, so call is made up to nRetries+1 times !
        nRetries = max(2, self['retry'])
        for i in range(nRetries +1):
            self.logger.debug("Will execute command: %s" % command)
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            stdout, stderr = process.communicate()
            exitcode = process.returncode
            #split the output returned into actual result and HTTP code
            result, http_code = stdout.rsplit(',', 1)
            http_code = int(http_code)


            if http_code != 200:
                #429 Too Many Requests. When client hits the throttling limit
                #500 Internal sever error. For some errors retries it helps
                #502 CMSWEB frontend answers with this when the CMSWEB backends are overloaded
                #503 Usually that's the DatabaseUnavailable error
                if (i < 2) or (http_code in [429, 500, 502, 503] and (i < self['retry'])):
                    sleeptime = 20 * (i + 1) + random.randint(-10, 10)
                    msg = "Sleeping %s seconds after HTTP error.\nError:\n:%s" % (sleeptime, stderr)
                    self.logger.debug(msg)
                else:
                    #this was the last retry
                    msg = "Fatal error trying to connect to %s using %s. Error details: \n%s " % (url, data, stderr)
                    raise Exception(msg)
            else:
                try:
                    curlResult = json.loads(result)
                except Exception as ex:
                    msg = "Fatal error reading data from %s using %s" % (url, data)
                    raise Exception(msg)
                else:
                    break
        return curlResult, http_code, 'dummyReason'


    @staticmethod
    def getCACertPath():
        """ Get the CA certificate path. It looks for it in the X509_CERT_DIR variable if present
            or return /etc/grid-security/certificates/ instead (if it exists)
            If a CA certificate path cannot be found throws a EnvironmentException exception
        """
        caDefault = '/etc/grid-security/certificates/'
        if "X509_CERT_DIR" in os.environ:
            return os.environ["X509_CERT_DIR"]
        if os.path.isdir(caDefault):
            return caDefault
        raise EnvironmentException("The X509_CERT_DIR variable is not set and the %s directory cannot be found.\n" % caDefault +
                                   "Cannot find the CA certificate path to authenticate the server.")

class CRABRest:
    """
    A convenience class to communicate with CRABServer REST
    Encapsulates an HTTPRequest object (which can be used also with other HTTP servers)
    together with the CRAB DB instance and allows to specify simply the CRAB Server API in
    the various HTTP methods.

    Add two methods to set and get the DB instance
    """
    def __init__(self, hostname='localhost', localcert=None, localkey=None, version=__version__,
                 retry=0, logger=None, verbose=False, userAgent='CRAB?'):
        self.server = HTTPRequests(hostname, localcert, localkey, version,
                                   retry, logger, verbose, userAgent)
        instance = 'prod'
        self.uriNoApi = '/crabserver/' + instance + '/'

    def setDbInstance(self, dbInstance='prod'):
        self.uriNoApi = '/crabserver/' + dbInstance + '/'

    def getDbInstance(self):
        return self.uriNoApi.rstrip('/').split('/')[-1]

    def get(self, api=None, data=None):
        uri = self.uriNoApi + api
        return self.server.get(uri, data)

    def post(self, api=None, data=None):
        uri = self.uriNoApi + api
        return self.server.post(uri, data)

    def put(self, api=None, data=None):
        uri = self.uriNoApi + api
        return self.server.put(uri, data)

    def delete(self, api=None, data=None):
        uri = self.uriNoApi + api
        return self.server.delete(uri, data)

