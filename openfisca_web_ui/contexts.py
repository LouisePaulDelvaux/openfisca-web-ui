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


"""Context loaded and saved in WSGI requests"""


import gettext
import os
import pkg_resources

from biryani.states import State
import webob

from . import conf, conv


__all__ = ['Ctx']


class Ctx(State):
    _parent = None
    default_values = dict(
        _application_path_info = None,
        _lang = None,
        _node = UnboundLocalError,
        _session = UnboundLocalError,
        _translator = None,
        _user = UnboundLocalError,
        req = None,
        )
    env_keys = ('_application_path_info', '_lang', '_node', '_session', '_translator', '_user')

    def __init__(self, req = None):
        if req is not None:
            self.req = req
            openfisca_web_ui_env = req.environ.get('openfisca-web-ui', {})
            for key in object.__getattribute__(self, 'env_keys'):
                value = openfisca_web_ui_env.get(key)
                if value is not None:
                    setattr(self, key, value)

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            parent = object.__getattribute__(self, '_parent')
            if parent is None:
                default_values = object.__getattribute__(self, 'default_values')
                if name in default_values:
                    return default_values[name]
                raise
            return getattr(parent, name)

    @property
    def _(self):
        return self.translator.ugettext

    def application_path_info_del(self):
        del self._application_path_info
        if self.req is not None and self.req.environ.get('openfisca-web-ui') is not None \
                and '_application_path_info' in self.req.environ['openfisca-web-ui']:
            del self.req.environ['openfisca-web-ui']['_application_path_info']

    def application_path_info_get(self):
        application_path_info = self._application_path_info
        assert application_path_info is not None
        return application_path_info

    def application_path_info_set(self, application_path_info):
        self._application_path_info = application_path_info
        if self.req is not None:
            self.req.environ.setdefault('openfisca-web-ui', {})['_application_path_info'] = self._application_path_info

    application_path_info = property(application_path_info_get, application_path_info_set, application_path_info_del)

    def blank_req(self, path, environ = None, base_url = None, headers = None, POST = None, **kw):  # NOQA
        env = environ.copy() if environ else {}
        openfisca_web_ui_env = env.setdefault('openfisca-web-ui', {})
        for key in self.env_keys:
            value = getattr(self, key)
            if value is not None:
                openfisca_web_ui_env[key] = value
        return webob.Request.blank(path, environ = env, base_url = base_url, headers = headers, POST = POST, **kw)

    def get_containing(self, name, depth = 0):
        """Return the n-th (n = ``depth``) context containing attribute named ``name``."""
        ctx_dict = object.__getattribute__(self, '__dict__')
        if name in ctx_dict:
            if depth <= 0:
                return self
            depth -= 1
        parent = ctx_dict.get('_parent')
        if parent is None:
            return None
        return parent.get_containing(name, depth = depth)

    def get_inherited(self, name, default = UnboundLocalError, depth = 1):
        ctx = self.get_containing(name, depth = depth)
        if ctx is None:
            if default is UnboundLocalError:
                raise AttributeError('Attribute %s not found in %s' % (name, self))
            return default
        return object.__getattribute__(ctx, name)

    def iter(self):
        yield self
        parent = object.__getattribute__(self, '_parent')
        if parent is not None:
            for ancestor in parent.iter():
                yield ancestor

    def iter_containing(self, name):
        ctx_dict = object.__getattribute__(self, '__dict__')
        if name in ctx_dict:
            yield self
        parent = ctx_dict.get('_parent')
        if parent is not None:
            for ancestor in parent.iter_containing(name):
                yield ancestor

    def iter_inherited(self, name):
        for ctx in self.iter_containing(name):
            yield object.__getattribute__(ctx, name)

    def lang_del(self):
        del self._lang
        if self.req is not None and self.req.environ.get('openfisca-web-ui') is not None \
                and '_lang' in self.req.environ['openfisca-web-ui']:
            del self.req.environ['openfisca-web-ui']['_lang']

    def lang_get(self):
        return self._lang or conf['languages']

    def lang_set(self, lang):
        self._lang = lang
        if self.req is not None:
            self.req.environ.setdefault('openfisca-web-ui', {})['_lang'] = self._lang
        # Reinitialize translator for new languages.
        if self._translator is not None:
            # Don't del self._translator, because attribute _translator can be defined in a parent.
            self._translator = None
            if self.req is not None and self.req.environ.get('openfisca-web-ui') is not None \
                    and '_translator' in self.req.environ['openfisca-web-ui']:
                del self.req.environ['openfisca-web-ui']['_translator']

    lang = property(lang_get, lang_set, lang_del)

    def new(self, **kwargs):
        ctx = Ctx()
        ctx._parent = self
        for name, value in kwargs.iteritems():
            setattr(ctx, name, value)
        return ctx

    def node_del(self):
        del self._node
        if self.req is not None and self.req.environ.get('openfisca-web-ui') is not None \
                and '_node' in self.req.environ['openfisca-web-ui']:
            del self.req.environ['openfisca-web-ui']['_node']

    def node_get(self):
        return self._node

    def node_set(self, node):
        self._node = node
        if self.req is not None:
            self.req.environ.setdefault('openfisca-web-ui', {})['_node'] = node

    node = property(node_get, node_set, node_del)

    @property
    def parent(self):
        return object.__getattribute__(self, '_parent')

    def session_del(self):
        del self._session
        if self.req is not None and self.req.environ.get('openfisca-web-ui') is not None \
                and '_session' in self.req.environ['openfisca-web-ui']:
            del self.req.environ['openfisca-web-ui']['_session']

    def session_get(self):
        if self._session is UnboundLocalError:
            if self.req is None:
                self.session = None
            else:
                from . import model
                session, error = conv.pipe(
                    conv.input_to_uuid_str,
                    conv.not_none,
                    model.Session.uuid_to_instance,
                    )(self.req.cookies.get(conf['cookie']), state = self)
                self.session = session if error is None else None
        return self._session

    def session_set(self, session):
        self._session = session
        if self.req is not None:
            self.req.environ.setdefault('openfisca-web-ui', {})['_session'] = session

    session = property(session_get, session_set, session_del)

    @property
    def translator(self):
        """Get a valid translator object from one or several languages names."""
        if self._translator is None:
            languages = self.lang
            if not languages:
                return gettext.NullTranslations()
            if not isinstance(languages, list):
                languages = [languages]
            translator = gettext.NullTranslations()
            for name, i18n_dir in [
                    (
                        'biryani',
                        os.path.join(pkg_resources.get_distribution('biryani').location, 'biryani', 'i18n'),
                        ),
                    ]:
                if i18n_dir is not None:
                    translator = new_translator(name, i18n_dir, languages, fallback = translator)
            translator = new_translator(conf['package_name'], conf['i18n_dir'], languages, fallback = translator)
            self._translator = translator
        return self._translator

    def user_del(self):
        del self._user
        if self.req is not None and self.req.environ.get('openfisca-web-ui') is not None \
                and '_user' in self.req.environ['openfisca-web-ui']:
            del self.req.environ['openfisca-web-ui']['_user']

    def user_get(self):
        return self._user

    def user_set(self, user):
        self._user = user
        if self.req is not None:
            self.req.environ.setdefault('openfisca-web-ui', {})['_user'] = user

    user = property(user_get, user_set, user_del)


def new_translator(domain, localedir, languages, fallback = None):
    new = gettext.translation(domain, localedir, fallback = True, languages = languages)
    if fallback is not None:
        new.add_fallback(fallback)
    return new
