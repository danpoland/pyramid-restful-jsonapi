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

        return super(IncludeRelationshipsMixin, self).get_schema(*args, **kwargs)

    def get_query(self):
        """
        Allows for the query to be dynamically updated based on any included relationships.
        Allowing for data to be pre-joined or pre-fetched cutting down on the number of db
        queries required for the request.
        """

        query = super(IncludeRelationshipsMixin, self).get_query()
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


class NestableSchemaMixin:
    """
    I forget where I left off on this but I think this will only work for a single level of nesting.

    Used when you need to use a Nested field with a JSONAPI Schema.
    It formats the errors so that the nested schemas errors pointers have the correct attribute path.

    For this to work, if a nested schema needs to have many=True, set it on an instance of the schema, not
    as a Nested argument (you will get a Invalid Type error).

    GOOD: fields.Nested(MySchema(many=True), required=True)
    BAD:  fields.Nested(MySchema,many=True, required=True)
    """

    def format_nested_errors(self, key, errors):
        """
        Updates the pointer attribute in an errors object so that it points to the nested attribute.

        :param key: The nested field name.
        :param errors: An array of already jsonapi formatted errors.
        :return: The formatted errors array.
        """

        for error in errors:
            source = error['source']
            source['pointer'] = '/data/attributes/{}'.format(key) + source['pointer']

        return errors

    def format_errors(self, errors, many):
        if not errors:
            return {}
        if isinstance(errors, (list, tuple)):
            return {'errors': errors}

        formatted_errors = []

        if many:  # won't ever be a nested jsonapi schema
            for index, errors in errors.items():
                for field_name, field_errors in errors.items():
                    formatted_errors.extend(
                        [self.format_error(field_name, message, index=index) for message in field_errors])
        else:
            for field_name, field_errors in errors.items():
                if isinstance(field_errors, dict):
                    errors = field_errors.get('errors')

                    if not errors:
                        # Not JSON API formatted, happens when a required nested attribute does not exist in the data
                        errors = self.format_errors(field_errors, False)['errors']

                    formatted_errors.extend(self.format_nested_errors(field_name, errors))
                else:
                    formatted_errors.extend([self.format_error(field_name, message) for message in field_errors])

        return {'errors': formatted_errors}
