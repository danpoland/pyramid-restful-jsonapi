from marshmallow_jsonapi.fields import Relationship


class IncludeRelationshipsMixin:
    """
    Parses query strings params for related objects that should be included in the serialized response.
    If includable_relationships is None then all relationships can be included.

    includable_relationships = A dictionary where the key is the mapped querystring value and the value is a dict of:
        {'rel': '<relationship name from schema>',
        'join': <optional, sqla join method to use>,
        'options': <optional, sqla query options>}
    """

    QUERY_KEY = 'include'
    includable_relationships = None

    def get_schema(self, *args, **kwargs):
        includable_names = self.includable_relationships.keys() if self.includable_relationships else None
        includes = []

        for key, vals in self.request.params.items():
            if key == self.QUERY_KEY:
                for val in vals.split(','):  # Allow for a comma separated list of include values
                    if includable_names is None or val in includable_names:
                        includes.append(val)

        if includes:
            kwargs['include_data'] = includes

        return super(IncludeDataMixin, self).get_schema(*args, **kwargs)

    def get_query(self):
        """
        Allows for the query to be dynamically updated based on any included relationships.
        Allowing for data to be pre-joined or pre-fetched cutting down on the number of db
        queries required for the request.
        """

        query = super(IncludeDataMixin, self).get_query()
        includables = getattr(self, 'includable_relationships', [])

        if includables:
            requested_includes = []

            for key, val in self.request.params.items():
                if key == self.QUERY_KEY:
                    requested_includes.extend(val.split(','))

            if requested_includes:
                available_includes = self.includable_relationships.keys()

                for name in requested_includes:
                    if name in available_includes:
                        field = self.includable_relationships[name]

                        if field.get('join'):
                            query = getattr(query, field.get('join'))(field['rel'])

                        # Apply optional options
                        options = field.get('options')

                        if options:
                            query = query.options(*options)

        return query


class IncludableRelationship(Relationship):
    """
    Allows an alternative attribute to be specified for include relationships.

    This allows you to specify a normal foreign key attribute when an relationship is
    not included and a relationship when the data should be included.

    Hopefully this will be PR'd into marshmallow_jsonapi in the near future and this can go away.
    """

    def __init__(self, include_attribute=None, *args, **kwargs):
        self.include_attribute = include_attribute
        super(MetaRelationship, self).__init__(*args, **kwargs)

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
