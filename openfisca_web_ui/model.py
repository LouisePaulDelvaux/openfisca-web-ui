# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""The application's model objects"""


import collections
import datetime
import re
import urllib

import babel.dates
from biryani import strings

from . import conv, objects, urls, wsgihelpers


class Account(objects.Initable, objects.JsonMonoClassMapper, objects.Mapper, objects.ActivityStreamWrapper):
    admin = False
    api_key = None
    cnil_conditions_accepted = None
    collection_name = 'accounts'
    current_test_case_id = None
    description = None
    email = None
    full_name = None
    slug = None
    stats_accepted = None

    def compute_words(self):
        self.words = sorted(set(strings.slugify(u'-'.join(
            unicode(fragment)
            for fragment in (
                self._id,
                self.email,
                self.full_name,
                )
            if fragment is not None
            )).split(u'-'))) or None

    @property
    def current_test_case(self):
        return TestCase.find_one(self.current_test_case_id, as_class = collections.OrderedDict) \
            if self.current_test_case_id is not None else None

    @current_test_case.setter
    def current_test_case(self, test_case):
        assert test_case.author_id == self._id
        self.current_test_case_id = test_case._id

    def ensure_test_case(self):
        """Create test case and set as current if not exists."""
        if self.current_test_case_id is None:
            test_case = TestCase(author_id = self._id)
            test_case.save(safe = True)
            self.current_test_case = test_case
            self.save(safe = True)

    @classmethod
    def get_admin_class_full_url(cls, ctx, *path, **query):
        return urls.get_full_url(ctx, 'admin', 'accounts', *path, **query)

    @classmethod
    def get_admin_class_url(cls, ctx, *path, **query):
        return urls.get_url(ctx, 'admin', 'accounts', *path, **query)

    def get_admin_full_url(self, ctx, *path, **query):
        if self._id is None and self.slug is None:
            return None
        return self.get_admin_class_full_url(ctx, self.slug or self._id, *path, **query)

    def get_admin_url(self, ctx, *path, **query):
        if self._id is None and self.slug is None:
            return None
        return self.get_admin_class_url(ctx, self.slug or self._id, *path, **query)

    def get_title(self, ctx):
        return self.full_name or self.slug or self.email or self._id

    def get_user_url(cls, ctx, *path, **query):
        return urls.get_url(ctx, 'account', *path, **query)

    def get_user_full_url(cls, ctx, *path, **query):
        return urls.get_full_url(ctx, 'account', *path, **query)

    @classmethod
    def make_id_or_slug_or_words_to_instance(cls):
        def id_or_slug_or_words_to_instance(value, state = None):
            if value is None:
                return value, None
            if state is None:
                state = conv.default_state
            id, error = conv.str_to_object_id(value, state = state)
            if error is None:
                self = cls.find_one(id, as_class = collections.OrderedDict)
            else:
                self = cls.find_one(dict(slug = value), as_class = collections.OrderedDict)
            if self is None:
                words = sorted(set(value.split(u'-')))
                instances = list(cls.find(
                    dict(
                        words = {'$all': [
                            re.compile(u'^{}'.format(re.escape(word)))
                            for word in words
                            ]},
                        ),
                    as_class = collections.OrderedDict,
                    ).limit(2))
                if not instances:
                    return value, state._(u"No account with ID, slug or words: {0}").format(value)
                if len(instances) > 1:
                    return value, state._(u"Too much accounts with words: {0}").format(u' '.join(words))
                self = instances[0]
            return self, None
        return id_or_slug_or_words_to_instance

    @property
    def test_cases(self):
        return list(TestCase.find({'author_id': self._id}))

    def turn_to_json_attributes(self, state):
        value, error = conv.object_to_clean_dict(self, state = state)
        if error is not None:
            return value, error
        if value.get('draft_id') is not None:
            value['draft_id'] = unicode(value['draft_id'])
        id = value.pop('_id', None)
        if id is not None:
            value['id'] = unicode(id)
        value.pop('api_key', None)
        return value, None


class Session(objects.JsonMonoClassMapper, objects.Mapper, objects.SmartWrapper):
    _user = UnboundLocalError
    collection_name = 'sessions'
    anonymous_token = None  # token given to external application to retrieve simulation data.
    disclaimer_closed = None
    expiration = None
    token = None  # the cookie token
    user_id = None

    @classmethod
    def get_admin_class_full_url(cls, ctx, *path, **query):
        return urls.get_full_url(ctx, 'admin', 'sessions', *path, **query)

    @classmethod
    def get_admin_class_url(cls, ctx, *path, **query):
        return urls.get_url(ctx, 'admin', 'sessions', *path, **query)

    def get_admin_full_url(self, ctx, *path, **query):
        if self.token is None:
            return None
        return self.get_admin_class_full_url(ctx, self.token, *path, **query)

    def get_admin_url(self, ctx, *path, **query):
        if self.token is None:
            return None
        return self.get_admin_class_url(ctx, self.token, *path, **query)

    def get_title(self, ctx):
        user = self.user
        if user is None:
            return ctx._(u'Session {0}').format(self.token)
        return ctx._(u'Session {0} of {1}').format(self.token, user.get_title(ctx))

    @classmethod
    def remove_expired(cls, ctx):
        for self in cls.find(
                dict(expiration = {'$lt': datetime.datetime.utcnow()}),
                as_class = collections.OrderedDict,
                ):
            self.delete()

    def to_bson(self):
        self_bson = self.__dict__.copy()
        self_bson.pop('_user', None)
        return self_bson

    @property
    def user(self):
        if self._user is UnboundLocalError:
            self._user = Account.find_one(self.user_id) if self.user_id is not None else None
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self.user_id = user._id

    @classmethod
    def uuid_to_instance(cls, value, state = None):
        if value is None:
            return value, None
        if state is None:
            state = conv.default_state

        # First, delete expired sessions.
        cls.remove_expired(state)

        self = cls.find_one(dict(token = value), as_class = collections.OrderedDict)
        if self is None:
            return value, state._(u"No session with UUID {0}").format(value)
        return self, None


class Status(objects.Mapper, objects.Wrapper):
    collection_name = 'status'
    last_upgrade_name = None


class TestCase(objects.Initable, objects.JsonMonoClassMapper, objects.Mapper, objects.ActivityStreamWrapper):
    additional_api_data = None
    api_data = None
    author_id = None
    collection_name = 'test_cases'
    description = None
    slug = None
    title = None

    def __init__(self, **attributes):
        super(TestCase, self).__init__(**attributes)
        if self.title is None:
            self.title = babel.dates.format_datetime(datetime.datetime.utcnow())
            self.slug = strings.slugify(self.title)

    def before_delete(self, old_bson):
        account = Account.find_one({'current_test_case_id': self._id})
        if account is not None:
            account.current_test_case_id = None
            account.save(safe = True)

    def compute_words(self):
        self.words = sorted(set(strings.slugify(u'-'.join(
            unicode(fragment)
            for fragment in (
                self._id,
                self.description,
                self.title,
                )
            if fragment is not None
            )).split(u'-'))) or None

    @classmethod
    def get_class_url(cls, ctx, *path, **query):
        return urls.get_url(ctx, 'test_cases', *path, **query)

    @classmethod
    def get_class_full_url(cls, ctx, *path, **query):
        return urls.get_full_url(ctx, 'test_cases', *path, **query)

    @classmethod
    def get_current_test_case_url(cls, ctx):
        test_case_url = urls.get_full_url(ctx, 'api/1/test_cases/current') + '?' + \
            urllib.urlencode({'token': '' if ctx.session is None else ctx.session.anonymous_token})
        return test_case_url

    def get_full_url(self, ctx, *path, **query):
        if self._id is None and self.slug is None:
            return None
        return urls.get_full_url(ctx, 'test_cases', self.slug or self._id, *path, **query)

    def get_url(self, ctx, *path, **query):
        if self._id is None and self.slug is None:
            return None
        return urls.get_url(ctx, 'test_cases', self.slug or self._id, *path, **query)

    def get_title(self, ctx):
        return self.full_name or self.slug or self.email or self._id

    @classmethod
    def make_id_or_slug_or_words_to_instance(cls):
        def id_or_slug_or_words_to_instance(value, state = None):
            if value is None:
                return value, None
            if state is None:
                state = conv.default_state
            id, error = conv.str_to_object_id(value, state = state)
            if error is None:
                self = cls.find_one(dict(_id = id), as_class = collections.OrderedDict)
            else:
                self = cls.find_one(dict(slug = value), as_class = collections.OrderedDict)
            if self is None:
                words = sorted(set(value.split(u'-')))
                instances = list(cls.find(
                    dict(
                        words = {'$all': [
                            re.compile(u'^{}'.format(re.escape(word)))
                            for word in words
                            ]},
                        ),
                    as_class = collections.OrderedDict,
                    ).limit(2))
                if not instances:
                    return value, state._(u"No simulation with ID, slug or words: {0}").format(value)
                if len(instances) > 1:
                    return value, state._(u"Too much simulations with words: {0}").format(u' '.join(words))
                self = instances[0]
            return self, None
        return id_or_slug_or_words_to_instance

    def turn_to_json_attributes(self, state):
        value, error = conv.object_to_clean_dict(self, state = state)
        if error is not None:
            return value, error
        if value.get('draft_id') is not None:
            value['draft_id'] = unicode(value['draft_id'])
        id = value.pop('_id', None)
        if id is not None:
            value['id'] = unicode(id)
        return value, None


def get_user(ctx, check = False):
    user = ctx.user
    if user is UnboundLocalError:
        session = ctx.session
        ctx.user = user = session.user if session is not None else None
    if user is None and check:
        raise wsgihelpers.unauthorized(ctx)
    return user


def init(db):
    objects.Wrapper.db = db


def is_admin(ctx, check = False):
    user = get_user(ctx)
    if user is None or user.email is None:
        if check:
            raise wsgihelpers.unauthorized(ctx,
                message = ctx._(u"You must be authenticated as an administrator to access this page."))
        return False
    if not user.admin:
        if Account.find_one(dict(admin = True), []) is None:
            # When there is no admin, every logged user is an admin.
            return True
        if check:
            raise wsgihelpers.forbidden(ctx, message = ctx._(u"You must be an administrator to access this page."))
        return False
    return True


def setup():
    """Setup MongoDb database."""
    from . import upgrades
    import imp
    import os

    upgrades_dir = os.path.dirname(upgrades.__file__)
    upgrades_name = sorted(
        os.path.splitext(upgrade_filename)[0]
        for upgrade_filename in os.listdir(upgrades_dir)
        if upgrade_filename.endswith('.py') and upgrade_filename != '__init__.py'
        )
    status = Status.find_one(as_class = collections.OrderedDict)
    if status is None:
        status = Status()
        if upgrades_name:
            status.last_upgrade_name = upgrades_name[-1]
        status.save()
    else:
        for upgrade_name in upgrades_name:
            if status.last_upgrade_name is None or status.last_upgrade_name < upgrade_name:
                print 'Upgrading "{0}"'.format(upgrade_name)
                upgrade_file, upgrade_file_path, description = imp.find_module(upgrade_name, [upgrades_dir])
                try:
                    upgrade_module = imp.load_module(upgrade_name, upgrade_file, upgrade_file_path, description)
                finally:
                    if upgrade_file:
                        upgrade_file.close()
                upgrade_module.upgrade(status)

    Account.ensure_index('admin', sparse = True)
    Account.ensure_index('api_key', sparse = True, unique = True)
    Account.ensure_index('email', sparse = True, unique = True)
    Account.ensure_index('slug', sparse = True, unique = True)
    Account.ensure_index('updated')
    Account.ensure_index('words')

    Session.ensure_index('expiration')
    Session.ensure_index('token', unique = True)
