import os
from pathlib import Path

import yaml

from charmhelpers.core import hookenv
from charms import layer
from charms.reactive import clear_flag, hook, set_flag, when, when_any, when_not


@hook("upgrade-charm")
def upgrade_charm():
    clear_flag("charm.started")


@when("charm.started")
def charm_ready():
    layer.status.active("")


@when_any("layer.docker-resource.oci-image.changed", "config.changed")
def update_image():
    clear_flag("charm.started")


@when("layer.docker-resource.oci-image.available")
@when_not("charm.started")
def start_charm():
    layer.status.maintenance("configuring container")

    image_info = layer.docker_resource.get_info("oci-image")

    namespace = os.environ["JUJU_MODEL_NAME"]

    layer.caas_base.pod_spec_set(
        {
            "version": 2,
            "serviceAccount": {
                "global": True,
                "rules": [
                    {
                        "apiGroups": [""],
                        "resources": ["events"],
                        "verbs": ["create", "patch"],
                    },
                    {
                        "apiGroups": [""],
                        "resources": ["pods", "services"],
                        "verbs": ["get", "list", "watch", "create", "delete"],
                    },
                    {
                        "apiGroups": [""],
                        "resources": ["secrets"],
                        "verbs": ["get", "list", "watch", "create", "update", "delete"],
                    },
                    {
                        "apiGroups": ["extensions", "networking.k8s.io/v1"],
                        "resources": ["ingresses"],
                        "verbs": ["get", "list", "watch", "create", "delete", "update"],
                    },
                    {
                        "apiGroups": ["networking.k8s.io/v1"],
                        "resources": ["ingresses/finalizers"],
                        "verbs": ["update"],
                    },
                    {
                        "apiGroups": ["cert-manager.io"],
                        "resources": ["certificates", "certificaterequests", "issuers"],
                        "verbs": [
                            "get",
                            "list",
                            "watch",
                            "create",
                            "delete",
                            "deletecollection",
                            "patch",
                            "update",
                        ],
                    },
                    {
                        "apiGroups": ["cert-manager.io"],
                        "resources": [
                            "certificaterequests/status",
                            "certificates/finalizers",
                            "certificates/status",
                            "clusterissuers",
                            "clusterissuers/status",
                            "issuers",
                            "issuers/status",
                        ],
                        "verbs": ["update"],
                    },
                    {
                        "apiGroups": ["cert-manager.io"],
                        "resources": [
                            "certificates",
                            "certificaterequests",
                            "clusterissuers",
                            "issuers",
                        ],
                        "verbs": ["get", "list", "watch"],
                    },
                    {
                        "apiGroups": ["acme.cert-manager.io"],
                        "resources": ["orders", "challenges"],
                        "verbs": ["create", "delete", "get", "list", "watch"],
                    },
                    {
                        "apiGroups": ["acme.cert-manager.io"],
                        "resources": [
                            "orders",
                            "orders/status",
                            "orders/finalizers",
                            "challenges",
                            "challenges/status",
                            "challenges/finalizers",
                        ],
                        "verbs": ["update"],
                    },
                ],
            },
            "containers": [
                {
                    "name": "cert-manager-controller",
                    "imageDetails": {
                        "imagePath": image_info.registry_path,
                        "username": image_info.username,
                        "password": image_info.password,
                    },
                    "args": [
                        "--v=2",
                        f"--cluster-resource-namespace={namespace}",
                        "--leader-elect=false",
                        f"--webhook-namespace={namespace}",
                        "--webhook-ca-secret=cert-manager-webhook-ca",
                        "--webhook-serving-secret=cert-manager-webhook-tls",
                        "--webhook-dns-names="
                        + ",".join(
                            [
                                "cert-manager-webhook",
                                f"cert-manager-webhook.{namespace}",
                                f"cert-manager-webhook.{namespace}.svc",
                            ]
                        ),
                    ],
                    "config": {"POD_NAMESPACE": namespace},
                    "ports": [
                        {"name": "http", "containerPort": hookenv.config("port")}
                    ],
                }
            ],
        },
        {
            "kubernetesResources": {
                "customResourceDefinitions": {
                    crd["metadata"]["name"]: crd["spec"]
                    for crd in yaml.safe_load_all(
                        Path("resources/crds.yaml").read_text()
                    )
                },
                "customResources": {
                    "issuers.cert-manager.io": [
                        {
                            "apiVersion": "cert-manager.io/v1alpha2",
                            "kind": "Issuer",
                            "metadata": {"name": name},
                            "spec": spec,
                        }
                        for name, spec in yaml.safe_load(
                            hookenv.config("issuers")
                        ).items()
                    ]
                },
            }
        },
    )

    layer.status.maintenance("creating container")
    set_flag("charm.started")
