# Copyright 2018 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" This template creates a Cloud Spanner instance and database. """


def append_optional_property(res, properties, prop_name):
    """ If the property is set, it is added to the resource. """

    val = properties.get(prop_name)
    if val:
        res['properties'][prop_name] = val
    return

def get_spanner_instance_id(project_id, base_name):
    """ Generate the instance URL """

    return "projects/{}/instances/{}".format(project_id, base_name)


def get_spanner_instance_config(project_id, config):
    """ Generate the instance config URL """

    return "projects/{}/instanceConfigs/{}".format(project_id, config)


def generate_config(context):
    """
    Generates the config gcloud needs to create a Cloud Spanner instance.
    Input: context - generated by gcloud when loading the input config file.
    Output: dictionary with key resource names - this contains all the
            information gcloud needs to create a spanner instance,
            databases, and permissions.
    """

    resources_list = []
    properties = context.properties
    name = properties.get('name', context.env['name'])
    project_id = properties.get('project', context.env['project'])

    instance_id = get_spanner_instance_id(project_id, name)
    instance_config = get_spanner_instance_config(
        project_id,
        context.properties['instanceConfig']
    )

    resource = {
        'name': name,
        # https://cloud.google.com/spanner/docs/reference/rest/v1/projects.instances
        'type': 'gcp-types/spanner-v1:projects.instances',
        'properties':
            {
                'instanceId': name,
                'parent': 'projects/{}'.format(project_id),
                'instance':
                    {
                        'name': instance_id,
                        'config': instance_config,
                        'nodeCount': context.properties['nodeCount'],
                        'displayName': context.properties['displayName']
                    }
            }
    }

    optional_properties = [
        'labels',
    ]
    for prop in optional_properties:
        append_optional_property(resource, properties, prop)
    resources_list.append(resource)

    if context.properties.get('bindings'):
        policy = {
            'name': "{}{}".format(name, '-setIamPolicy'),
            # https://cloud.google.com/spanner/docs/reference/rest/v1/projects.instances/setIamPolicy
            'action': 'gcp-types/spanner-v1:spanner.projects.instances.setIamPolicy',  # pylint: disable=line-too-long
            'properties':
                {
                    'resource': instance_id,
                    'policy': {
                        'bindings': context.properties['bindings']
                    }
                },
            'metadata': {
                'dependsOn': [name]
            }
        }
        resources_list.append(policy)

    out = {}
    for database in context.properties.get("databases", []):
        database_resource_name = "{}{}{}".format(
            instance_id,
            "/databases/",
            database['name']
        )
        database_resource = {
            'name': database_resource_name,
            # https://cloud.google.com/spanner/docs/reference/rest/v1/projects.instances.databases
            'type': 'gcp-types/spanner-v1:projects.instances.databases',
            'properties':
                {
                    'parent': instance_id,
                    'databaseId': database['name']
                },
            'metadata': {
                'dependsOn': [name]
            }
        }
        resources_list.append(database_resource)

        if database.get('bindings'):
            database_policy = {
                'name':
                    "{}{}".format(database_resource_name,
                                  "-setIamPolicy"),
                # https://cloud.google.com/spanner/docs/reference/rest/v1/projects.instances.databases/setIamPolicy
                'action': 'gcp-types/spanner-v1:spanner.projects.instances.databases.setIamPolicy',  # pylint: disable=line-too-long
                'properties':
                    {
                        'resource': database_resource_name,
                        'policy': {
                            'bindings': database['bindings']
                        }
                    },
                'metadata': {
                    'dependsOn': [database_resource_name]
                }
            }
            resources_list.append(database_policy)

        out[database_resource_name] = {
            'state': '$(ref.' + database_resource_name + '.state)'
        }

    outputs = [
        {
            'name': 'state',
            'value': '$(ref.' + name + '.state)'
        },
        {
            'name': 'databases',
            'value': out
        }
    ]

    return {'resources': resources_list, 'outputs': outputs}
