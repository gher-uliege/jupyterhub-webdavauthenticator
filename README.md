# WebDAV JupyterHub Authenticator

WebDAV authenticator for [JupyterHub](http://github.com/jupyter/jupyterhub/).

## Installation ##

To installation run:

```bash
sudo python3 -m pip install  ~/src/jupyterhub-webdavauthenticator/
```

This module uses https://pypi.org/project/webdavclient/.

To upgrade run:

```bash
sudo python3 -m pip install --upgrade  ~/src/jupyterhub-webdavauthenticator/
```

## Configuration

See the example `jupyterhub_config.py` file. In particular you need to adapt:

* `c.JupyterHub.authenticator_class`
* `c.Authenticator.enable_auth_state`
* `c.WebDAVAuthenticator.allowed_webdav_servers`
* `c.WebDAVAuthenticator.custom_html`

You need to set the environement variable `JUPYTERHUB_CRYPT_KEY` to enable persisent authentication state as desribed [here](https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html).
If systemd is used for jupterhub, then this can be done by runnning:

```bash
cat > /etc/systemd/system/jupyterhub.service.d/myenv.conf <<EOF
[Service]
Environment="JUPYTERHUB_CRYPT_KEY=copy_random_key_here"
EOF
```

