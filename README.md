Charmed Cert Manager
====================

See https://cert-manager.io/

Deploying
---------

You can deploy these charms from the charm store:

    juju deploy cert-manager

A default self-signed Issuer will be created for you. If you wish to create additional
Issuers, you can configure the `cert-manager-controller` charm.

You will also need to modify the role associated with the `cert-manager-webhook` charm.
You can store this file file somewhere and run `kubectl apply -n cert-manager -f $FILE`:

```json
{
  "apiVersion": "rbac.authorization.k8s.io/v1",
  "kind": "Role",
  "metadata": {
    "name": "cert-manager-webhook-operator"
  },
  "rules": [
    {
      "apiGroups": [
        ""
      ],
      "resources": [
        "pods",
        "secret"
      ],
      "verbs": [
        "get",
        "list",
      ]
    },
    {
      "apiGroups": [
        ""
      ],
      "resources": [
        "pods/exec"
      ],
      "verbs": [
        "create"
      ]
    }
  ]
}
```

Or run `kubectl edit -n cert-manager role/cert-manager-webhook-operator` and edit the file
manually.

Configuring
-----------

Charmed Cert Manager supports creating 3 types of Issuers natively: Self-signed, CA, and
ACME. They are creating by configuring the `cert-manager-controller` charm, as
`self-signed-issuers`, `ca-issuers`, and `acme-issuers`, respectively. Each configuration
option expects a YAML or JSON dictionary as a string in the form of `name: spec`. Some
formats support more advanced configuration as detailed below.

When configuring `cert-manager-controller`, you may want to write separate YAML files for
readability rather than writing YAML inline in the CLI. You can install the `yq` utility
to easily achieve this:

    sudo snap install yq

Then, in the exapmles below, write a YAML file as specified and configure the charm like
this:

    juju config cert-manager-controller self-signed-issuers=$(yq -j r your-issuers.yaml)

If you'd like to configure an Issuer that isn't supported, manually creating one with
`kubectl` as shown on https://cert-manager.io/docs/ also works.

### Self Signed

To override the default self-signed Issuer, you can configure the `cert-manager-controller`
charm like this:

    juju config cert-manager-controller self-signed-issuers='foo:{}'

where `foo` is the name of the Issuer you'd like to create. If you'd like to configure
additional properties such as `crlDistributionPoints`, you would configure the charm like
this:

    juju config cert-manager-controller self-signed-issuers="foo: crlDistributionPoints: [http://example.com]"

See (test-certs-self-signed.yaml)[test-certs-self-signed.yaml] for more examples.

### CA

To create a CA Issuer, you can configure the `cert-manager-controller` charm like this:

    juju config cert-manager-controller ca-issuers='foo: ca: secretName: foo-secret'

where `foo` is the name of the Issuer you'd like to create. You can also specify the
contents of the secret instead of referencing them, and Juju will create the Secret
for you. As shown above, it's easiest to write this as a separate file, so normal YAML
will be shown:

    your-issuer-name:
      secret:
        tls.crt: ...
        tls.key: ...
      ca: {}

Juju will create the Secret with `tls.crt` and `tls.key`, then create the Issuer so as to
reference the created Secret. If you manually add `secretName` under `ca`, Juju will use
that name. `ca` is otherwise specified as indicated in https://cert-manager.io/docs/configuration/ca/.

See (test-certs-ca.yaml)[test-certs-ca.yaml] for more examples.

### ACME

You can create an ACME Issuer by configuring the `cert-manager-controller` charm's
`acme-issuers` option. It is recommended to write the YAML file separately, and include it
as an argument as shown above, or like this:

    # le-issuers.yaml
    my-le-issuer:
      acme:
        email: user@example.com
        server: https://acme-staging-v02.api.letsencrypt.org/directory
        privateKeySecretRef:
          name: example-issuer-account-key
        solvers:
        - http01:
            ingress:
              class: nginx

    # Conigure Juju like this:
    juju config cert-manager-controller acme-issuers=$(yq -j r le-issuers.yaml)

See [test-certs-acme.yaml](test-certs-acme.yaml) for more examples.
