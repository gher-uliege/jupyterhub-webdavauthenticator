import mechanicalsoup
import warnings
import requests
from urllib.parse import parse_qs, urlparse, urlencode
import xml.etree.ElementTree as ET
import sys
import os
import subprocess

from tornado import gen
from traitlets import Unicode, List, Bool

from jupyterhub.auth import Authenticator
import webdav.client as wc
from urllib.parse import urlparse

WEBDAV_URL = "https://b2drop.eudat.eu/remote.php/webdav"

def mount_webdav(webdav_username,webdav_password,userdir_owner_id,userdir_group_id,webdav_url,webdav_fullmount):

    if not os.path.isdir(webdav_fullmount):
        os.mkdir(webdav_fullmount)

    p = subprocess.run(['mount.davfs','-o','uid=%d,gid=%d,username=%s' % (userdir_owner_id,userdir_group_id,webdav_username),webdav_url,webdav_fullmount],
                       stdout=subprocess.PIPE,input=webdav_password.encode("ascii"))

def check_webdav(username,password,url):
    purl = urlparse(url)

    client = wc.Client({
        'webdav_hostname': purl.scheme + "://" + purl.hostname,
        'webdav_login':    username,
        'webdav_password': password})

    success = client.check(purl.path)
    if success:
        print("credentials accepted for user",username,file=sys.stderr)
        return username
    else:
        print("credentials refused for user",username,file=sys.stderr)
        return None


def check_token(token):
    UNITY_URL = "https://unity.eudat-aai.fz-juelich.de:443/oauth2/userinfo"

    resp = requests.get(UNITY_URL, headers = {
        "Authorization": "Bearer " + token,
        "Content-type": "application/json"})

    success = resp.status_code == 200

    if success:
        data = resp.json()
        return True, data
    else:
        return False, {}


def prep_dir(validuser,userdir = None):
    basedir = "/mnt/data/jupyterhub-user/"
    userdir_owner_id = 1000
    userdir_group_id = 100

    if userdir == None:
        # warning username might be escaped
        userdir = os.path.join(basedir,"jupyterhub-user-" + validuser)

    print("userdir",userdir,file=sys.stderr)
    print("dir before",os.listdir(basedir),file=sys.stderr)

    if not os.path.isdir(userdir):
        print("create",userdir,file=sys.stderr)
        os.mkdir(userdir)

    print("dir after",os.listdir(basedir),file=sys.stderr)
    print("stat before",os.stat(userdir),file=sys.stderr)
    os.chown(userdir,userdir_owner_id,userdir_group_id)
    print("stat after",os.stat(userdir),file=sys.stderr)

    return userdir,userdir_owner_id,userdir_group_id

class WebDAVAuthenticator(Authenticator):

    custom_html = Unicode(
        "",
        config = True)

    allowed_webdav_servers = List(
        [WEBDAV_URL],
        config = True)

    mount = Bool(
        False,
        config = True)

    @gen.coroutine
    def authenticate(self, handler, data):
        token = data.get("token","") # "" if missing

        # token authentication
        if token != "":
            success,data = check_token(token)

            if success:
                username = data["unity:persistent"]
                prep_dir(username)
                return username

        # username/password authentication

        password = data.get("password","") # "" if missing
        username = data['username']
        webdav_url = data.get('webdav_url', WEBDAV_URL)
        webdav_username = data.get('webdav_username',username)
        webdav_password = data.get('webdav_password',password)
        webdav_mount = data.get('webdav_mount',"WebDAV")

        print("URL2",webdav_url,file=sys.stderr)

        if webdav_url not in self.allowed_webdav_servers:
            print("only allow connections to ",self.allowed_webdav_servers,
                  " and not to ",webdav_url,file=sys.stderr)
            return None

        #validuser = check_webdav(username,password,webdav_url)
        # debugging
        print("allowing using",username,file=sys.stderr)
        validuser = username
        print("validuser",username, validuser,file=sys.stderr)
        if validuser == username:
            # safty check
            if "/" in validuser:
                return None

            #userdir,userdir_owner_id,userdir_group_id = prep_dir(validuser)

            # webdav
            if not self.mount:
                webdav_mount = ""

            #if self.mount and webdav_url != "" and webdav_username != "" and webdav_password != "" and webdav_mount != "":
            #    webdav_fullmount = os.path.join(userdir,webdav_mount)
            #    mount_webdav(webdav_username,webdav_password,userdir_owner_id,userdir_group_id,webdav_url,webdav_fullmount)


        print("return dict",file=sys.stderr)
        return {"name": validuser, "auth_state": {
            "webdav_password": webdav_password,
            "webdav_username": webdav_username,
            "webdav_url": webdav_url,
            "webdav_mount": webdav_mount,
        }}

    @gen.coroutine
    def pre_spawn_start(self, user, spawner):
        print("pre_spawn_start user",user.name,file=sys.stderr)
        # Write the WebDAV token to the users' environment variables
        auth_state = yield user.get_auth_state()

        if not auth_state:
            print("auth state not enabled",file=sys.stderr)
            # auth_state not enabled
            return

        print("DEBUG: spawner.escaped_name ",spawner.escaped_name,file=sys.stderr)
        print("DEBUG: spawner.volume_mount_points ",spawner.volume_mount_points,file=sys.stderr)
        print("DEBUG: spawner.volume_binds ",spawner.volume_binds,file=sys.stderr)

        userdir = list(spawner.volume_binds.keys())[0]
        dummy,userdir_owner_id,userdir_group_id = prep_dir(user.name,userdir = userdir)

        webdav_mount = auth_state['webdav_mount']
        webdav_username = auth_state['webdav_username']
        webdav_password = auth_state['webdav_password']
        webdav_url = auth_state['webdav_url']

        if webdav_mount != "":
            webdav_fullmount = os.path.join(userdir,webdav_mount)
            mount_webdav(webdav_username,
                         webdav_password,
                         userdir_owner_id,
                         userdir_group_id,
                         webdav_url,
                         webdav_fullmount)

        print("setting env variable",user,file=sys.stderr)
        #spawner.environment['WEBDAV_USERNAME'] = auth_state['webdav_username']
        spawner.environment['WEBDAV_USERNAME'] = user.name
        spawner.environment['WEBDAV_PASSWORD'] = webdav_password
        spawner.environment['WEBDAV_URL'] = webdav_url
        spawner.environment['WEBDAV_MOUNT'] = webdav_mount



if __name__ == "__main__":
    # Test with
    # python3 webdavauthenticator.py <username> <password>
    username=sys.argv[1]
    password=sys.argv[2]

    print(check_webdav(username,password))

    WebDAVAuth = WebDAVAuthenticator()
