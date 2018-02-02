import json

from collections import namedtuple

from unittest import TestCase, mock

from marshmallow_jsonapi import Schema, fields

from pyramid_restful_jsonapi.mixins import IncludableSchemaMixin, IncludableViewMixin

Account = namedtuple('Account', ['id', 'owner_id', 'profile_id', 'owner', 'profile'])
User = namedtuple('User', ['id', 'name'])
Profile = namedtuple('Profile', ['id', 'created_date'])


class UserSchema(Schema):
    id = fields.Integer()
    name = fields.String()

    class Meta:
        type_ = 'user'


class ProfileSchema(Schema):
    id = fields.Integer()
    created_date = fields.Date()

    class Meta:
        type_ = 'user'


class AccountSchema(IncludableSchemaMixin, Schema):
    id = fields.Integer()
    profile = fields.Relationship(
        type_='profile',
        include_resource_linkage=True,
        schema='ProfileSchema'
    )

    owner = fields.Relationship(
        attribute='owner_id',
        type_='user',
        include_resource_linkage=True,
        schema='UserSchema'
    )

    class Meta:
        type_ = 'account'
        includable_fields = {'owner': 'owner'}


class AccountView:
    def get_query(self):
        return mock.Mock()

    def get_schema(self, *args, **kwargs):
        return kwargs


class IncludableAccountView(IncludableViewMixin, AccountView):
    schema_class = AccountSchema
    includable_relationships = {'owner': {'rel': 'owner', 'join': 'join'}}


class IncludableSchemaTests(TestCase):
    """
    IncludableSchemaMixin integration tests.
    """

    def setUp(self):
        self.user = User(id=99, name='test user')
        self.profile = Profile(id=50, created_date='20170214')
        self.account = Account(id=1, owner_id=99, profile_id=50, owner=self.user, profile=self.profile)

    def test_expandable_schema_mixin(self):
        request = mock.Mock()
        request.params = {'include': 'owner'}
        schema = AccountSchema(context={'request': request}, include_data=['owner'])
        content = schema.dump(self.account)[0]

        expected = {
            'data': {
                'type': 'account',
                'relationships': {
                    'owner': {
                        'data': {
                            'type': 'user',
                            'id': '99'
                        }
                    },
                    'profile': {
                        'data': {
                            'type': 'profile',
                            'id': '50'
                        }
                    }
                },
                'id': 1
            },
            'included': [{
                'type': 'user',
                'attributes': {
                    'name': 'test user'
                },
                'id': 99
            }]
        }

        assert content == expected


class IncludableViewTests(TestCase):
    """
    IncludableViewMixin unit tests.
    """

    def test_expandable_view_mixin(self):
        request = mock.Mock()
        request.params = {'include': 'owner'}
        view = IncludableAccountView()
        view.request = request
        query = view.get_query()
        assert query.join.called_once_with('owner')

    def test_expandable_view_mixin_outer_join(self):
        request = mock.Mock()
        request.params = {'include': 'owner'}
        view = IncludableAccountView()
        view.expandable_fields = {'owner': {
            'outerjoin': 'owner',
        }}
        view.request = request
        query = view.get_query()
        assert query.outerjoin.called_once_with('owner')

    def test_expandable_view_mixin_options(self):
        request = mock.Mock()
        request.params = {'include': 'owner'}
        view = IncludableAccountView()
        view.expandable_fields = {'owner': {
            'options': {'preselect': True}
        }}
        view.request = request
        query = view.get_query()
        assert query.options.called_once_with({'preselect': True})

    def test_expandable_view_mixin_get_schema(self):
        request = mock.Mock()
        request.params = {'include': 'owner'}
        view = IncludableAccountView()
        view.request = request
        schema = view.get_schema()

        assert schema == {'include_data': ['owner']}
