from marshmallow_jsonapi.fields import Relationship


class IncludableRelationship(Relationship):
    """
    Allows an alternative attribute to be specified for include relationships.

    This allows you to specify a normal foreign key attribute when an relationship is
    not included and a relationship when the data should be included.

    Hopefully this will be PR'd into marshmallow_jsonapi in the near future and this can go away.
    """

    def __init__(self, include_attribute=None, *args, **kwargs):
        self.include_attribute = include_attribute
        super(IncludableRelationship, self).__init__(*args, **kwargs)

    def _serialize(self, value, attr, obj):
        dict_class = self.parent.dict_class if self.parent else dict
        ret = dict_class()
        self_url = self.get_self_url(obj)
        related_url = self.get_related_url(obj)

        if self_url or related_url:
            ret['links'] = dict_class()
            if self_url:
                ret['links']['self'] = self_url
            if related_url:
                ret['links']['related'] = related_url

        # resource linkage is required when including the data
        if self.include_resource_linkage or self.include_data:
            if value is None:
                ret['data'] = [] if self.many else None
            else:
                ret['data'] = self.get_resource_linkage(value)

        if self.include_data:
            if self.include_attribute:
                value = getattr(obj, self.include_attribute, None)

            if value is not None:
                if self.many:
                    for item in value:
                        self._serialize_included(item)
                else:
                    self._serialize_included(value)

        return ret