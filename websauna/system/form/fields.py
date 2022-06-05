# Standard Library
import enum
import json
import typing as t

# Pyramid
import colander
import deform

# Websauna
from websauna.system.model.json import NestedMutationDict
from websauna.system.model.json import NestedMutationList
from websauna.system.model.json import json_serializer


def defer_widget_values(widget: type, values_callback: t.Callable, **kwargs) -> deform.widget.Widget:
    """Allow select or checkbox widget values construction deferred during the execution time.

    :param widget: Any Deform widget class, see :py:class:`deform.widget.Widget`
    :param value_callback: This callable(node, kw) is called deferredly by Colander
    :param kwargs: Passed to the widget constructed
    """

    _widget = widget

    @colander.deferred
    def _inner(node, kw):
        return _widget(values=values_callback(node, kw), **kwargs)

    return _inner


class UUID(colander.String):
    """UUID field for Colander.

    See also :py:class`websauna.system.form.widgets.FriendlyUUIDWidget`.
    """

    def serialize(self, node, appstruct):
        # Assume widgets can handle raw UUID object
        return appstruct


class EnumValue(colander.String):
    """Allow choice of python enum.Enum in colander schemas.

    Example:

    .. code-block:: python

        class AssetClass(enum.Enum):
        '''What's preferred display format for this asset.'''

            fiat = "fiat"
            cryptocurrency = "cryptocurrency"
            token = "token"
            tokenized_shares = "tokenized_shares"
            ether = "ether"

        class Schema(CSRFSchema):

            asset_class = colander.SchemaNode(
                EnumValue(AssetClass),
                widget=deform.widget.SelectWidget(values=enum_values(AssetClass)))

    """

    def __init__(self, enum_class: type):
        super().__init__()
        assert issubclass(enum_class, enum.Enum), f"Expected Enum, got {enum_class}"
        self.enum_class = enum_class

    def deserialize(self, node: colander.SchemaNode, cstruct: str):
        """Parse incoming form values to Python objects if needed.
        """
        return self.enum_class(cstruct) if cstruct else None

    def serialize(self, node: colander.SchemaNode, _enum: enum.Enum) -> str:
        """Convert Enum object to str for widget processing."""
        if _enum:
            assert isinstance(
                _enum, self.enum_class
            ), f"Expected {self.enum_class}, got {_enum}"

            return _enum.value
        else:
            return _enum


class JSONValue(colander.String):
    """Serialize / deserialize JSON fields.

    Example:

    .. code-block:: python

        class AssetSchema(CSRFSchema):

            name = colander.SchemaNode(colander.String())

            other_data = colander.SchemaNode(
                JSONValue(),
                widget=JSONWidget(),
                description="JSON bag of attributes of the object")

    """

    def deserialize(self, node: colander.SchemaNode, cstruct: str):
        """Parse incoming form values to Python objects if needed.
        """
        if cstruct:
            try:
                return json.loads(cstruct)
            except json.JSONDecodeError as e:
                raise colander.Invalid(node, "Not valid JSON") from e
        else:
            return None

    def serialize(self, node: colander.SchemaNode, data: t.Union[list, dict]) -> str:
        """Convert Python objects to JSON string."""
        if not data:
            # Noneish
            return data
        assert isinstance(
            data, (list, dict, NestedMutationDict, NestedMutationList)
        ), f"Expected list or dict, got {data.__class__}"

        return json_serializer(data)
