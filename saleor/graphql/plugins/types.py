from typing import TYPE_CHECKING, Optional

import graphene

from ...core.tracing import traced_resolver
from ...plugins import models
from ...plugins.base_plugin import ConfigurationTypeField
from ..core.connection import CountableDjangoObjectType
from .enums import ConfigurationTypeFieldEnum

if TYPE_CHECKING:
    # flake8: noqa
    from ...plugins.base_plugin import PluginConfigurationType


def hide_private_configuration_fields(configuration, config_structure):
    for field in configuration:
        name = field["name"]
        value = field["value"]
        if value is None:
            continue
        field_type = config_structure.get(name, {}).get("type")
        if field_type == ConfigurationTypeField.PASSWORD:
            field["value"] = "" if value else None

        if field_type in [
            ConfigurationTypeField.SECRET,
            ConfigurationTypeField.SECRET_MULTILINE,
        ]:
            if not value:
                field["value"] = None
            elif len(value) > 4:
                field["value"] = value[-4:]
            else:
                field["value"] = value[-1:]


class ConfigurationItem(graphene.ObjectType):
    name = graphene.String(required=True, description="Name of the field.")
    value = graphene.String(required=False, description="Current value of the field.")
    type = graphene.Field(ConfigurationTypeFieldEnum, description="Type of the field.")
    help_text = graphene.String(required=False, description="Help text for the field.")
    label = graphene.String(required=False, description="Label for the field.")

    class Meta:
        description = "Stores information about a single configuration field."


class Plugin(CountableDjangoObjectType):
    id = graphene.Field(type=graphene.ID, required=True)
    configuration = graphene.List(ConfigurationItem)

    class Meta:
        description = "Plugin."
        model = models.PluginConfiguration
        interfaces = [graphene.relay.Node]
        only_fields = ["id", "name", "description", "active", "configuration"]

    def resolve_id(self: models.PluginConfiguration, _info):
        return self.identifier

    @staticmethod
    @traced_resolver
    def resolve_configuration(
        root: models.PluginConfiguration, info
    ) -> Optional["PluginConfigurationType"]:
        plugin = info.context.plugins.get_plugin(root.identifier)
        if not plugin:
            return None
        configuration = plugin.configuration
        if plugin.CONFIG_STRUCTURE and configuration:
            hide_private_configuration_fields(configuration, plugin.CONFIG_STRUCTURE)
        return configuration
