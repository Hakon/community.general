#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2022, Håkon Lerring
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = '''
module: consul_token
short_description: Manipulate Consul tokens
description:
 - Allows the addition, modification and deletion of tokens in a consul
   cluster via the agent. For more details on using and configuring ACLs,
   see https://www.consul.io/docs/guides/acl.html.
author:
  - Håkon Lerring (@Hakon)
options:
  id:
    description:
      - A GUID used to identify the token. This will become the AccessorID in consul
    required: true
    type: str
  state:
    description:
      - whether the token should be present or absent
    required: false
    choices: ['present', 'absent']
    default: present
    type: str
  local:
    description:
      - whether the token should be restricted to the local datacenter.
    default: False
    type: bool
  token:
    description:
      - the token key identifying an ACL rule set. If generated by consul
        this will be a UUID
    required: false
    type: str
  description:
    description:
      - Description of the token
    required: false
    type: str
  policies:
    type: list
    elements: dict
    description:
      - List of policies to attach to the token.
      - Each element must have a "name" or "id" (or both) to identify the policy. See consul_policy for more info.
    required: false
  roles:
    type: list
    elements: dict
    description:
      - List of roles to attach to the token.
      - Each element must have a "name" or "id" (or both) to identify the role.
    required: false
  service_identities:
    type: list
    elements: dict
    description:
      - List of service identities to attach to the token.
      - Each element must have a "name" and optionally a "datacenters" list of datacenters the policy is valid for.
      - An empty datacenters list allows all datacenters
    required: false
  node_identities:
    type: list
    elements: dict
    description:
      - List of node identities to attach to the token.
      - Each element must have a "name" and optionally a "datacenter" the policy is valid for. An empty datacenter allows all datacenters
    required: false
  host:
    description:
      - host of the consul agent defaults to localhost
    required: false
    default: localhost
    type: str
  port:
    type: int
    description:
      - the port on which the consul agent is running
    required: false
    default: 8500
  scheme:
    description:
      - the protocol scheme on which the consul agent is running
    required: false
    default: http
    type: str
  mgmt_token:
    description:
      - a management token is required to manipulate the policies
    type: str
  validate_certs:
    type: bool
    description:
      - whether to verify the tls certificate of the consul agent
    required: false
    default: True
requirements:
  - requests
'''

EXAMPLES = """
- name: Create a token with 2 policies
  consul_token:
    host: consul1.example.com
    mgmt_token: some_management_acl
    id: 28F86FE2-8F61-46EA-BDD8-2AFE7F2B9F0A
    policies:
      - id: 783beef3-783f-f41f-7422-7087dc272765
      - name: "policy-1"
- name: Create a token with a specific token
  consul_token:
    host: consul1.example.com
    mgmt_token: some_management_acl
    id: F49E877B-2482-4AE1-8D6B-03ACF65097F7
    token: my-token
    policies:
      - id: 783beef3-783f-f41f-7422-7087dc272765
- name: Create a token with service identity
  consul_token:
    host: consul1.example.com
    mgmt_token: some_management_acl
    id: ED8E0D78-2B1B-4CC2-950F-A12956CB50B1
    service_identities:
      - name: web
        datacenters:
          - dc1
- name: Create a token with node identity
  consul_token:
    host: consul1.example.com
    mgmt_token: some_management_acl
    id: E584B772-B2B9-44DC-A06D-DFECA11F6065
    node_identities:
      - name: node-1
        datacenter: dc2
- name: Remove a token
  consul_token:
    host: consul1.example.com
    mgmt_token: some_management_acl
    id: E584B772-B2B9-44DC-A06D-DFECA11F6065
    state: absent
"""

RETURN = """
token:
    description: The token object, containing for example SecretID and AccessorID
    returned: success
    type: str
    sample: |
        {
            "AccessorID": "28F86FE2-8F61-46EA-BDD8-2AFE7F2B9F0A",
            "CreateIndex": 29,
            "CreateTime": "2022-09-29T09:10:35.8117161Z",
            "Description": "",
            "Hash": "+HNHaPJ/mr/PSh6cgtlELFHVrY3Mi/gsEfNB6ODnq5E=",
            "Local": false,
            "ModifyIndex": 29,
            "Policies": [
                {"ID": "8bcfa038-cb1e-51db-d3cb-80758345d23e", "Name": "foo-access"}
            ],
            "SecretID": "3b370630-b374-7c71-93e2-a5fd5eb4deae"
        }
operation:
    description: the operation performed on the token
    returned: changed
    type: str
    sample: update
"""

from ansible.module_utils.basic import to_text, AnsibleModule

try:
    from requests.exceptions import ConnectionError
    import requests
    has_requests = True
except ImportError:
    has_requests = False


MANAGEMENT_PARAMETER_NAME = "mgmt_token"
HOST_PARAMETER_NAME = "host"
SCHEME_PARAMETER_NAME = "scheme"
VALIDATE_CERTS_PARAMETER_NAME = "validate_certs"
ID_PARAMETER_NAME = "id"
DESCRIPTION_PARAMETER_NAME = "description"
PORT_PARAMETER_NAME = "port"
ROLES_PARAMETER_NAME = "roles"
POLICIES_PARAMETER_NAME = "policies"
SERVICE_IDENTITIES_PARAMETER_NAME = "service_identities"
NODE_IDENTITIES_PARAMETER_NAME = "node_identities"
LOCAL_PARAMETER_NAME = "local"
TOKEN_PARAMETER_NAME = "token"
STATE_PARAMETER_NAME = "state"


PRESENT_STATE_VALUE = "present"
ABSENT_STATE_VALUE = "absent"

REMOVE_OPERATION = "remove"
UPDATE_OPERATION = "update"
CREATE_OPERATION = "create"

_ARGUMENT_SPEC = {
    MANAGEMENT_PARAMETER_NAME: dict(no_log=True),
    PORT_PARAMETER_NAME: dict(default=8500, type='int'),
    HOST_PARAMETER_NAME: dict(default='localhost'),
    SCHEME_PARAMETER_NAME: dict(default='http'),
    VALIDATE_CERTS_PARAMETER_NAME: dict(type='bool', default=True),
    ID_PARAMETER_NAME: dict(required=True),
    DESCRIPTION_PARAMETER_NAME: dict(required=False, type='str', default=''),
    ROLES_PARAMETER_NAME: dict(type='list', elements='dict', default=[]),
    POLICIES_PARAMETER_NAME: dict(type='list', elements='dict', default=[]),
    SERVICE_IDENTITIES_PARAMETER_NAME: dict(type='list', elements='dict', default=[]),
    NODE_IDENTITIES_PARAMETER_NAME: dict(type='list', elements='dict', default=[]),
    LOCAL_PARAMETER_NAME: dict(type='bool', default=False),
    TOKEN_PARAMETER_NAME: dict(type='str', no_log=True),
    STATE_PARAMETER_NAME: dict(default=PRESENT_STATE_VALUE, choices=[PRESENT_STATE_VALUE, ABSENT_STATE_VALUE]),
}


def get_consul_url(configuration):
    return '%s://%s:%s/v1' % (configuration.scheme, configuration.host, configuration.port)


def get_auth_headers(configuration):
    if configuration.management_token is None:
        return {}
    else:
        return {'X-Consul-Token': configuration.management_token}


class RequestError(Exception):
    pass


def handle_consul_response_error(response):
    if 400 <= response.status_code < 600:
        raise RequestError('%d %s' % (response.status_code, response.content))


def update_token(token, configuration):
    url = '%s/acl/token/%s' % (get_consul_url(configuration),
                               token['AccessorID'])
    headers = get_auth_headers(configuration)

    update_token_data = {
        'Description': configuration.description,
        'Policies': [x.to_dict() for x in configuration.policies],
        'Roles': [x.to_dict() for x in configuration.roles],
        'Local': configuration.local
    }

    if configuration.version >= ConsulVersion("1.5.0"):
        update_token_data["ServiceIdentities"] = [
            x.to_dict() for x in configuration.service_identities]

    if configuration.version >= ConsulVersion("1.8.0"):
        update_token_data["NodeIdentities"] = [
            x.to_dict() for x in configuration.node_identities]

    response = requests.put(url, headers=headers, json=update_token_data, verify=configuration.validate_certs)
    handle_consul_response_error(response)

    resulting_token = response.json()
    changed = (
        token['Description'] != resulting_token['Description'] or
        token['Local'] != resulting_token['Local'] or
        token.get('Policies', None) != resulting_token.get('Policies', None) or
        token.get('Roles', None) != resulting_token.get('Roles', None) or
        token.get('ServiceIdentities', None) != resulting_token.get('ServiceIdentities', None) or
        token.get(
            'NodeIdentities',
            None) != resulting_token.get(
            'NodeIdentities',
            None)
    )

    return Output(changed=changed, operation=UPDATE_OPERATION, token=resulting_token)


def create_token(configuration):
    url = '%s/acl/token' % get_consul_url(configuration)
    headers = get_auth_headers(configuration)
    create_token_data = {
        'AccessorID': configuration.id,
        'Description': configuration.description,
        'SecretID': configuration.token,
        'Policies': [x.to_dict() for x in configuration.policies],
        'Roles': [x.to_dict() for x in configuration.roles],
        'Local': configuration.local
    }
    if configuration.version >= ConsulVersion("1.5.0"):
        create_token_data["ServiceIdentities"] = [x.to_dict() for x in configuration.service_identities]

    if configuration.version >= ConsulVersion("1.8.0"):
        create_token_data["NodeIdentities"] = [x.to_dict() for x in configuration.node_identities]

    response = requests.put(url, headers=headers, json=create_token_data, verify=configuration.validate_certs)
    handle_consul_response_error(response)

    resulting_token = response.json()

    return Output(changed=True, operation=CREATE_OPERATION, token=resulting_token)


def remove_token(configuration):
    tokens = get_tokens(configuration)

    if configuration.id in tokens:

        token_id = tokens[configuration.id]['AccessorID']

        url = '%s/acl/token/%s' % (get_consul_url(configuration), token_id)
        headers = get_auth_headers(configuration)
        response = requests.delete(url, headers=headers, verify=configuration.validate_certs)
        handle_consul_response_error(response)

        changed = True
    else:
        changed = False
    return Output(changed=changed, operation=REMOVE_OPERATION)


def get_tokens(configuration):
    url = '%s/acl/tokens' % get_consul_url(configuration)
    headers = get_auth_headers(configuration)
    response = requests.get(url, headers=headers, verify=configuration.validate_certs)
    handle_consul_response_error(response)
    tokens = response.json()
    existing_tokens_mapped_by_id = dict(
        (token['AccessorID'],
         token) for token in tokens if token['AccessorID'] is not None)
    return existing_tokens_mapped_by_id


def get_token(id, configuration):
    url = '%s/acl/token/%s' % (get_consul_url(configuration), id)
    headers = get_auth_headers(configuration)
    response = requests.get(url, headers=headers, verify=configuration.validate_certs)
    handle_consul_response_error(response)
    return response.json()


def get_consul_version(configuration):
    url = '%s/agent/self' % get_consul_url(configuration)
    headers = get_auth_headers(configuration)
    response = requests.get(url, headers=headers, verify=configuration.validate_certs)
    handle_consul_response_error(response)
    config = response.json()["Config"]
    return ConsulVersion(config["Version"])


def set_token(configuration):
    tokens = get_tokens(configuration)

    if configuration.id in tokens:
        index_token_object = tokens[configuration.id]
        token_id = tokens[configuration.id]['AccessorID']
        rest_token_object = get_token(token_id, configuration)
        # merge dicts as some keys are only available in the partial token
        token = index_token_object.copy()
        token.update(rest_token_object)
        return update_token(token, configuration)
    else:
        return create_token(configuration)


class ConsulVersion():
    def __init__(self, version_string):
        split = version_string.split('.')
        self.major = split[0]
        self.minor = split[1]
        self.patch = split[2]

    def __ge__(self, other):
        return int(self.major + self.minor +
                   self.patch) >= int(other.major + other.minor + other.patch)

    def __le__(self, other):
        return int(self.major + self.minor +
                   self.patch) <= int(other.major + other.minor + other.patch)


class ServiceIdentity:
    def __init__(self, input):
        if not isinstance(input, dict) or 'name' not in input:
            raise ValueError(
                "Each element of service_identities must be a dict with the keys name and optionally datacenters")
        self.name = input["name"]
        self.datacenters = input["datacenters"] if "datacenters" in input else None

    def to_dict(self):
        return {
            "ServiceName": self.name,
            "Datacenters": self.datacenters
        }


class NodeIdentity:
    def __init__(self, input):
        if not isinstance(input, dict) or 'name' not in input:
            raise ValueError(
                "Each element of node_identities must be a dict with the keys name and optionally datacenter")
        self.name = input["name"]
        self.datacenter = input["datacenter"] if "datacenter" in input else None

    def to_dict(self):
        return {
            "NodeName": self.name,
            "Datacenter": self.datacenter
        }


class RoleLink:
    def __init__(self, dict):
        self.id = dict.get("id", None)
        self.name = dict.get("name", None)

    def to_dict(self):
        return {
            "ID": self.id,
            "Name": self.name
        }


class PolicyLink:
    def __init__(self, dict):
        self.id = dict.get("id", None)
        self.name = dict.get("name", None)

    def to_dict(self):
        return {
            "ID": self.id,
            "Name": self.name
        }


class Configuration:
    """
    Configuration for this module.
    """

    def __init__(self, management_token=None, host=None, scheme=None, validate_certs=None, id=None, description=None, port=None,
                 roles=None, policies=None, service_identities=None, node_identities=None, local=None, token=None, state=None):
        self.management_token = management_token                                    # type: str
        self.host = host                                                            # type: str
        self.port = port                                                            # type: int
        self.scheme = scheme                                                        # type: str
        self.validate_certs = validate_certs                                        # type: bool
        self.id = id                                                                # type: str
        self.description = description                                              # type: str
        self.token = token                                                          # type: str
        self.roles = [RoleLink(r) for r in roles]                                   # type: list(RoleLink)
        self.policies = [PolicyLink(p) for p in policies]                           # type: list(PolicyLink)
        self.service_identities = [ServiceIdentity(s) for s in service_identities]  # type: list(ServiceIdentity)
        self.node_identities = [NodeIdentity(n) for n in node_identities]           # type: list(NodeIdentity)
        self.local = local                                                          # type: bool
        self.state = state                                                          # type: str


class Output:
    """
    Output of an action of this module.
    """

    def __init__(self, changed=None, operation=None, token=None):
        self.changed = changed      # type: bool
        self.operation = operation  # type: str
        self.token = token          # type: dict


def check_dependencies():
    """
    Checks that the required dependencies have been imported.
    :exception ImportError: if it is detected that any of the required dependencies have not been imported
    """

    if not has_requests:
        raise ImportError(
            "requests required for this module. See https://pypi.org/project/requests/")


def main():
    """
    Main method.
    """
    module = AnsibleModule(_ARGUMENT_SPEC, supports_check_mode=False)

    try:
        check_dependencies()
    except ImportError as e:
        module.fail_json(msg=str(e))
    try:
        configuration = Configuration(
            management_token=module.params.get(MANAGEMENT_PARAMETER_NAME),
            host=module.params.get(HOST_PARAMETER_NAME),
            port=module.params.get(PORT_PARAMETER_NAME),
            scheme=module.params.get(SCHEME_PARAMETER_NAME),
            validate_certs=module.params.get(VALIDATE_CERTS_PARAMETER_NAME),
            id=module.params.get(ID_PARAMETER_NAME),
            description=module.params.get(DESCRIPTION_PARAMETER_NAME),
            roles=module.params.get(ROLES_PARAMETER_NAME),
            policies=module.params.get(POLICIES_PARAMETER_NAME),
            service_identities=module.params.get(
                SERVICE_IDENTITIES_PARAMETER_NAME),
            node_identities=module.params.get(NODE_IDENTITIES_PARAMETER_NAME),
            local=module.params.get(LOCAL_PARAMETER_NAME),
            token=module.params.get(TOKEN_PARAMETER_NAME),
            state=module.params.get(STATE_PARAMETER_NAME),

        )
    except ValueError as err:
        module.fail_json(msg='Configuration error: %s' % str(err))
        return

    try:

        version = get_consul_version(configuration)
        configuration.version = version
        if configuration.state == PRESENT_STATE_VALUE:
            output = set_token(configuration)
        else:
            output = remove_token(configuration)
    except ConnectionError as e:
        module.fail_json(msg='Could not connect to consul agent at %s:%s, error was %s' % (
            configuration.host, configuration.port, str(e)))
        raise

    return_values = dict(changed=output.changed, operation=output.operation, token=output.token)
    module.exit_json(**return_values)


if __name__ == "__main__":
    main()
