# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014 OpenFisca Team
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


"""Controllers for legislations"""


import collections
import datetime
import json
import logging
import re
import requests

import babel.dates
import pymongo
import webob
import webob.multidict

from biryani import strings

from .. import contexts, conf, conv, model, paginations, templates, urls, wsgihelpers


N_ = lambda message: message
inputs_to_legislation_data = conv.pipe(
    conv.struct(
        dict(
            datetime_begin = conv.pipe(
                conv.cleanup_line,
                conv.french_formatted_str_to_datetime,
                ),
            datetime_end = conv.pipe(
                conv.cleanup_line,
                conv.french_formatted_str_to_datetime,
                ),
            description = conv.cleanup_text,
            json = conv.make_input_to_json(),
            url = conv.make_input_to_url(full = True),
            title = conv.pipe(
                conv.cleanup_line,
                conv.not_none,
                ),
            ),
        default = 'drop',
        ),
    conv.test(lambda struct: struct.get('url') is not None or struct.get('json') is not None, error = {
        'url': N_(u'Either URL or JSON must be provided.')}),
    )
log = logging.getLogger(__name__)


@wsgihelpers.wsgify
def admin_delete(req):
    ctx = contexts.Ctx(req)
    model.is_admin(ctx, check = True)
    legislation = ctx.node
    if req.method == 'POST':
        legislation.delete(safe = True)
        return wsgihelpers.redirect(ctx, location = model.Legislation.get_admin_class_url(ctx))
    return templates.render(ctx, '/legislations/admin-delete.mako', legislation = legislation)


@wsgihelpers.wsgify
def admin_edit(req):
    ctx = contexts.Ctx(req)
    model.is_admin(ctx, check = True)
    legislation = ctx.node
    if req.method == 'GET':
        errors = None
        inputs = dict(
            datetime_begin = babel.dates.format_date(legislation.datetime_begin, format = 'short'),
            datetime_end = babel.dates.format_date(legislation.datetime_end, format = 'short'),
            description = legislation.description,
            json = json.dumps(legislation.json, encoding = 'utf-8', ensure_ascii = False, indent = 2),
            url = legislation.url,
            title = legislation.title,
        )
    else:
        assert req.method == 'POST'
        inputs = extract_legislation_inputs_from_params(ctx, req.POST)
        data, errors = inputs_to_legislation_data(inputs, state = ctx)
        if errors is None:
            data['slug'], error = conv.pipe(
                conv.input_to_slug,
                conv.not_none,
                )(data['title'], state = ctx)
            if error is not None:
                errors = dict(title = error)
        if errors is None:
            legislation_json, error = None, None
            if data['url'] is not None:
                legislation_json, error = conv.pipe(
                    conv.legislations.retrieve_legislation,
                    conv.legislations.validate_legislation_json,
                    )(data['url'], state = ctx)
            else:
                legislation_json, error = conv.legislations.validate_legislation_json(data['json'], state = ctx)
            if error is not None:
                errors = dict(json = error['error']) if data['url'] is None else dict(url = error)
            else:
                data['json'] = legislation_json
        if errors is None:
            if model.Legislation.find(
                    dict(
                        _id = {'$ne': legislation._id},
                        slug = data['slug'],
                        ),
                    as_class = collections.OrderedDict,
                    ).count() > 0:
                errors = dict(title = ctx._(u'A legislation with the same name already exists.'))
        if errors is None:
            legislation.set_attributes(**data)
            legislation.compute_words()
            legislation.save(safe = True)

            # View legislation.
            return wsgihelpers.redirect(ctx, location = legislation.get_admin_url(ctx))
    return templates.render(ctx, '/legislations/admin-edit.mako', errors = errors, inputs = inputs,
        legislation = legislation)


@wsgihelpers.wsgify
def admin_extract(req):
    ctx = contexts.Ctx(req)
    user = model.get_user(ctx, check = True)
    model.is_admin(ctx, check = True)
    legislation = ctx.node
    if legislation.is_owner(ctx) and legislation.is_dated:
        return wsgihelpers.bad_request(ctx, explanation = ctx._(u'This legislation is already dated.'))

    params = req.GET
    inputs = {
        'date': params.get('date'),
        }
    data, errors = conv.struct({
        'date': conv.pipe(
            conv.french_formatted_str_to_datetime,
            conv.default(datetime.datetime.utcnow()),
            ),
        })(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.bad_request(ctx, explanation = errors)

    new_legislation = None
    new_legislation_title = ctx._(u'{} (copy {})').format(legislation.title, user.email)
    new_legislation_slug = strings.slugify(new_legislation_title)
    existing_legislations_cursor = model.Legislation.find(
        dict(
            slug = new_legislation_slug,
            ),
        as_class = collections.OrderedDict,
        )
    if existing_legislations_cursor.count() > 0:
        for existing_legislation in existing_legislations_cursor:
            if existing_legislation.is_owner(ctx):
                return wsgihelpers.redirect(ctx, location = existing_legislation.get_admin_url(ctx))
        if new_legislation is None:
            return wsgihelpers.bad_request(
                ctx,
                explanation = ctx._(u'A legislation with the same name already exists.'),
                )
    else:
        new_legislation = model.Legislation(
            author_id = user._id,
            datetime_begin = legislation.datetime_begin,
            datetime_end = legislation.datetime_end,
            description = ctx._(u'Copy of legislation "{}"').format(legislation.title),
            title = new_legislation_title,
            slug = new_legislation_slug,
            )
        response = requests.post(
            conf['api.urls.legislations'],
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': conf['app_name'],
                },
            data = json.dumps(dict(date = data['date'].isoformat(), legislation = legislation.json)),
            )
        new_legislation.json = response.json(object_pairs_hook = collections.OrderedDict).get('dated_legislation')
        new_legislation.save(safe = True)
    return wsgihelpers.redirect(ctx, location = new_legislation.get_admin_url(ctx))


@wsgihelpers.wsgify
def admin_index(req):
    ctx = contexts.Ctx(req)
    model.is_admin(ctx, check = True)

    params = req.GET
    inputs = dict(
        advanced_search = params.get('advanced_search'),
        page = params.get('page'),
        sort = params.get('sort'),
        term = params.get('term'),
        )
    data, errors = conv.pipe(
        conv.struct(
            dict(
                advanced_search = conv.guess_bool,
                page = conv.pipe(
                    conv.input_to_int,
                    conv.test_greater_or_equal(1),
                    conv.default(1),
                    ),
                sort = conv.pipe(
                    conv.cleanup_line,
                    conv.test_in(['slug', 'updated']),
                    ),
                term = conv.input_to_words,
                ),
            ),
        conv.rename_item('page', 'page_number'),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.bad_request(ctx, explanation = errors)

    criteria = {}
    if data['term'] is not None:
        criteria['words'] = {'$all': [
            re.compile(u'^{}'.format(re.escape(word)))
            for word in data['term']
            ]}
    cursor = model.Legislation.find(criteria, as_class = collections.OrderedDict)
    pager = paginations.Pager(item_count = cursor.count(), page_number = data['page_number'])
    if data['sort'] == 'slug':
        cursor.sort([('slug', pymongo.ASCENDING)])
    elif data['sort'] == 'updated':
        cursor.sort([(data['sort'], pymongo.DESCENDING), ('slug', pymongo.ASCENDING)])
    legislations = cursor.skip(pager.first_item_index or 0).limit(pager.page_size)
    return templates.render(ctx, '/legislations/admin-index.mako', data = data, errors = errors,
        legislations = legislations, inputs = inputs, pager = pager)


@wsgihelpers.wsgify
def admin_new(req):
    ctx = contexts.Ctx(req)
    model.is_admin(ctx, check = True)
    legislation = model.Legislation()
    if req.method == 'GET':
        errors = None
        inputs = extract_legislation_inputs_from_params(ctx)
    else:
        assert req.method == 'POST'
        inputs = extract_legislation_inputs_from_params(ctx, req.POST)
        data, errors = inputs_to_legislation_data(inputs, state = ctx)
        if errors is None:
            data['slug'], error = conv.pipe(
                conv.input_to_slug,
                conv.not_none,
                )(data['title'], state = ctx)
            if error is not None:
                errors = dict(title = error)
        if errors is None:
            legislation_json, error = None, None
            if data['json'] is None:
                legislation_json, error = conv.pipe(
                    conv.legislations.retrieve_legislation,
                    conv.legislations.validate_legislation_json,
                    )(data['url'], state = ctx)
            else:
                legislation_json, error = conv.legislations.validate_legislation_json(data['json'], state = ctx)
            if error is not None:
                errors = dict(json = error) if data['url'] is None else dict(url = error)
            else:
                data['json'] = legislation_json
        if errors is None:
            if model.Legislation.find(
                    dict(
                        slug = data['slug'],
                        ),
                    as_class = collections.OrderedDict,
                    ).count() > 0:
                errors = dict(full_name = ctx._(u'A legislation with the same name already exists.'))
        if errors is None:
            legislation.set_attributes(**data)
            legislation.compute_words()
            legislation.save(safe = True)

            # View legislation.
            return wsgihelpers.redirect(ctx, location = legislation.get_admin_url(ctx))
    return templates.render(ctx, '/legislations/admin-new.mako', errors = errors, inputs = inputs,
        legislation = legislation)


@wsgihelpers.wsgify
def admin_view(req):
    ctx = contexts.Ctx(req)
    model.is_admin(ctx, check = True)
    legislation = ctx.node
    params = req.GET
    date, error = conv.french_formatted_str_to_datetime(params.get('date'), state = ctx)
    dated_legislation_json = None
    if date is not None and not legislation.is_dated:
        response = requests.post(
            conf['api.urls.legislations'],
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': conf['app_name'],
                },
            data = json.dumps(dict(date = date.isoformat(), legislation = legislation.json)),
            )
        if not response.ok:
            error = ctx._(u'Unable to compute dated legislation')
        else:
            dated_legislation_json = response.json()
    elif legislation.is_dated:
        dated_legislation_json = legislation.json
    if error is not None:
        return wsgihelpers.bad_request(ctx, explanation = error)
    return templates.render(
        ctx,
        '/legislations/admin-view.mako',
        date = date,
        legislation = legislation,
        dated_legislation_json = dated_legislation_json,
        )


@wsgihelpers.wsgify
def api1_edit(req):
    """Used by X-editable in legislation admin-edit and user-edit templates."""
    ctx = contexts.Ctx(req)
    params = req.params
    model.get_user(ctx, check = True)

    legislation = ctx.node
    if not legislation.is_owner(ctx) and not model.is_admin(ctx):
        return wsgihelpers.respond_json(
            ctx,
            {'status': 'error', 'message': ctx._(u'You are not authorized to edit this legislation.')},
            )
    if legislation.is_dated:
        return wsgihelpers.respond_json(
            ctx,
            {'status': 'error', 'message': ctx._(u'A non-dated legislation is read-only.')},
            )

    inputs = {
        'name': params.getall('name[]'),
        'value': params.get('value'),
        }
    data, errors = conv.pipe(
        conv.struct({
            'name': conv.uniform_sequence(
                conv.cleanup_line
                ),
            'value': conv.cleanup_line,
            }),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.respond_json(
            ctx,
            {'status': 'error', 'errors': errors, 'inputs': inputs},
            )

    def get_deep_key(data, layers):
        if data is None:
            return None
        layer = layers[0]
        next_layers = layers[1:]
        if isinstance(data, list):
            layer_data = data[int(layer)]
        elif data.get('children') is not None:
            layer_data = data['children'].get(layer)
        else:
            layer_data = data.get(layer)
        return get_deep_key(data=layer_data, layers=next_layers) if next_layers else layer_data

    node_key = 'value' if data['name'][-1] not in ['base', 'rate', 'threshold'] else data['name'].pop()
    node = get_deep_key(legislation.json, data['name'])
    if data['name'][-1] in ['base', 'rate', 'threshold']:
        value, error = conv.switch(
            conv.function(lambda value: node_key),
            {
                'base': conv.pipe(
                    conv.input_to_float,
                    conv.test_greater_or_equal(0),
                    ),
                'rate': conv.pipe(
                    conv.input_to_float,
                    conv.test_greater_or_equal(0),
                    conv.test_less_or_equal(1),
                    ),
                'threshold': conv.input_to_float,
                },
            )(data['value'], state = ctx)
    else:
        value, error = conv.switch(
            conv.function(lambda value: node.get('format', 'float')),
            {
                'float': conv.input_to_float,
                'integer': conv.input_to_int,
                'rate': conv.pipe(
                    conv.input_to_float,
                    conv.test_greater_or_equal(0),
                    conv.test_less_or_equal(1),
                    ),
                },
            )(data['value'], state = ctx)
    if error is not None:
        return wsgihelpers.error(ctx, body = error, code = 400)
    node[node_key] = value
    legislation.save(safe = True)
    return wsgihelpers.respond_json(ctx, data['value'])


@wsgihelpers.wsgify
def api1_json(req):
    ctx = contexts.Ctx(req)
    legislation = ctx.node
    return wsgihelpers.respond_json(ctx, legislation.json)


@wsgihelpers.wsgify
def api1_search(req):
    ctx = contexts.Ctx(req)

    params = req.GET
    inputs = dict(
        page = params.get('page'),
        sort = params.get('sort'),
        term = params.get('term'),
        )
    data, errors = conv.pipe(
        conv.struct(
            dict(
                page = conv.pipe(
                    conv.input_to_int,
                    conv.test_greater_or_equal(1),
                    conv.default(1),
                    ),
                sort = conv.pipe(
                    conv.cleanup_line,
                    conv.test_in(['slug', 'updated']),
                    ),
                term = conv.input_to_words,
                ),
            ),
        conv.rename_item('page', 'page_number'),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.bad_request(ctx, explanation = errors)

    criteria = {}
    if data['term'] is not None:
        criteria['words'] = {'$all': [
            re.compile(u'^{}'.format(re.escape(word)))
            for word in data['term']
            ]}
    cursor = model.Legislation.find(criteria, as_class = collections.OrderedDict)
    pager = paginations.Pager(item_count = cursor.count(), page_number = data['page_number'])
    if data['sort'] == 'slug':
        cursor.sort([('slug', pymongo.ASCENDING)])
    elif data['sort'] == 'updated':
        cursor.sort([(data['sort'], pymongo.DESCENDING), ('slug', pymongo.ASCENDING)])
    legislations = cursor.skip(pager.first_item_index or 0).limit(pager.page_size)

    return wsgihelpers.respond_json(
        ctx,
        [
            {
                'description': legislation.description,
                'datetimeBegin': legislation.datetime_begin.isoformat(),
                'datetimeEnd': legislation.datetime_end.isoformat(),
                'published': legislation.published.isoformat(),
                'slug': legislation.slug,
                'title': legislation.title,
                'updated': legislation.updated.isoformat(),
                'url': legislation.url,
                }
            for legislation in legislations
            ],
        )


@wsgihelpers.wsgify
def api1_typeahead(req):
    ctx = contexts.Ctx(req)
    headers = wsgihelpers.handle_cross_origin_resource_sharing(ctx)

    params = req.GET
    inputs = dict(
        q = params.get('q'),
        )
    data, errors = conv.struct(
        dict(
            q = conv.input_to_words,
            ),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.bad_request(ctx, explanation = errors)

    criteria = {}
    if data['q'] is not None:
        criteria['words'] = {'$all': [
            re.compile(u'^{}'.format(re.escape(word)))
            for word in data['q']
            ]}
    cursor = model.Legislation.get_collection().find(criteria, ['title'])
    return wsgihelpers.respond_json(ctx,
        [
            legislation_attributes['title']
            for legislation_attributes in cursor.limit(10)
            ],
        headers = headers,
        )


def extract_legislation_inputs_from_params(ctx, params = None):
    if params is None:
        params = webob.multidict.MultiDict()
    return dict(
        datetime_begin = params.get('datetime_begin'),
        datetime_end = params.get('datetime_end'),
        description = params.get('description'),
        json = params.get('json'),
        title = params.get('title'),
        url = params.get('url'),
        )


def route_admin(environ, start_response):
    req = webob.Request(environ)
    ctx = contexts.Ctx(req)

    legislation, error = conv.pipe(
        conv.input_to_slug,
        conv.not_none,
        model.Legislation.make_id_or_slug_or_words_to_instance(),
        )(req.urlvars.get('id_or_slug_or_words'), state = ctx)
    if error is not None:
        return wsgihelpers.not_found(ctx, explanation = error)(environ, start_response)

    ctx.node = legislation

    router = urls.make_router(
        ('GET', '^/?$', admin_view),
        (('GET', 'POST'), '^/delete/?$', admin_delete),
        (('GET', 'POST'), '^/edit/?$', admin_edit),
        ('GET', '^/extract/?$', admin_extract),
        )
    return router(environ, start_response)


def route_admin_class(environ, start_response):
    router = urls.make_router(
        ('GET', '^/?$', admin_index),
        (('GET', 'POST'), '^/new/?$', admin_new),
        (None, '^/(?P<id_or_slug_or_words>[^/]+)(?=/|$)', route_admin),
        )
    return router(environ, start_response)


def route_api1(environ, start_response):
    req = webob.Request(environ)
    ctx = contexts.Ctx(req)

    legislation, error = conv.pipe(
        conv.input_to_slug,
        conv.not_none,
        model.Legislation.make_id_or_slug_or_words_to_instance(),
        )(req.urlvars.get('id_or_slug_or_words'), state = ctx)
    if error is not None:
        return wsgihelpers.not_found(ctx, explanation = error)(environ, start_response)

    ctx.node = legislation

    router = urls.make_router(
        ('POST', '^/edit/?$', api1_edit),
        ('GET', '^/json/?$', api1_json),
        )
    return router(environ, start_response)


def route_api1_class(environ, start_response):
    router = urls.make_router(
        ('GET', '^/search/?$', api1_search),
        ('GET', '^/typeahead/?$', api1_typeahead),
        (None, '^/(?P<id_or_slug_or_words>[^/]+)(?=/|$)', route_api1),
        )
    return router(environ, start_response)


def route_user(environ, start_response):
    req = webob.Request(environ)
    ctx = contexts.Ctx(req)

    legislation, error = conv.pipe(
        conv.input_to_slug,
        conv.not_none,
        model.Legislation.make_id_or_slug_or_words_to_instance(),
        )(req.urlvars.get('id_or_slug_or_words'), state = ctx)
    if error is not None:
        return wsgihelpers.not_found(ctx, explanation = error)(environ, start_response)

    ctx.node = legislation

    router = urls.make_router(
        (('GET', 'POST'), '^/delete/?$', user_delete),
        (('GET', 'POST'), '^/edit/?$', user_edit),
        ('GET', '^/extract/?$', user_extract),
        ('GET', '^/?$', user_view),
        )
    return router(environ, start_response)


def route_user_class(environ, start_response):
    router = urls.make_router(
        ('GET', '^/?$', user_index),
        (('GET', 'POST'), '^/new/?$', user_new),
        (None, '^/(?P<id_or_slug_or_words>[^/]+)(?=/|$)', route_user),
        )
    return router(environ, start_response)


@wsgihelpers.wsgify
def user_delete(req):
    ctx = contexts.Ctx(req)
    legislation = ctx.node
    model.get_user(ctx, check = True)
    if not legislation.is_owner(ctx):
        return wsgihelpers.forbidden(ctx)
    if req.method == 'POST':
        legislation.delete(safe = True)
        return wsgihelpers.redirect(ctx, location = model.Legislation.get_class_url(ctx))
    return templates.render(ctx, '/legislations/user-delete.mako', legislation = legislation)


@wsgihelpers.wsgify
def user_edit(req):
    ctx = contexts.Ctx(req)
    legislation = ctx.node
    model.get_user(ctx, check = True)
    if not legislation.is_owner(ctx):
        return wsgihelpers.forbidden(ctx)
    if req.method == 'GET':
        errors = None
        inputs = dict(
            datetime_begin = babel.dates.format_date(legislation.datetime_begin, format = 'short'),
            datetime_end = babel.dates.format_date(legislation.datetime_end, format = 'short'),
            description = legislation.description,
            json = json.dumps(legislation.json, encoding = 'utf-8', ensure_ascii = False, indent = 2),
            url = legislation.url,
            title = legislation.title,
        )
    else:
        assert req.method == 'POST'
        inputs = extract_legislation_inputs_from_params(ctx, req.POST)
        data, errors = inputs_to_legislation_data(inputs, state = ctx)
        if errors is None:
            data['slug'], error = conv.pipe(
                conv.input_to_slug,
                conv.not_none,
                )(data['title'], state = ctx)
            if error is not None:
                errors = dict(title = error)
        if errors is None:
            legislation_json, error = None, None
            if data['url'] is not None:
                legislation_json, error = conv.pipe(
                    conv.legislations.retrieve_legislation,
                    conv.legislations.validate_legislation_json,
                    )(data['url'], state = ctx)
            else:
                legislation_json, error = conv.legislations.validate_legislation_json(data['json'], state = ctx)
            if error is not None:
                errors = dict(json = error['error']) if data['url'] is None else dict(url = error)
            else:
                data['json'] = legislation_json
        if errors is None:
            if model.Legislation.find(
                    dict(
                        _id = {'$ne': legislation._id},
                        slug = data['slug'],
                        ),
                    as_class = collections.OrderedDict,
                    ).count() > 0:
                errors = dict(title = ctx._(u'A legislation with the same name already exists.'))
        if errors is None:
            legislation.set_attributes(**data)
            legislation.compute_words()
            legislation.save(safe = True)

            # View legislation.
            return wsgihelpers.redirect(ctx, location = legislation.get_user_url(ctx))
    return templates.render(ctx, '/legislations/user-edit.mako', errors = errors, inputs = inputs,
        legislation = legislation)


@wsgihelpers.wsgify
def user_extract(req):
    ctx = contexts.Ctx(req)
    user = model.get_user(ctx, check = True)
    if user.email is None:
        return wsgihelpers.forbidden(ctx)
    legislation = ctx.node
    if legislation.is_owner(ctx) and legislation.is_dated:
        return wsgihelpers.bad_request(ctx, explanation = ctx._(u'This legislation is already dated.'))

    params = req.GET
    inputs = {
        'date': params.get('date'),
        }
    data, errors = conv.struct({
        'date': conv.pipe(
            conv.french_formatted_str_to_datetime,
            conv.default(datetime.datetime.utcnow()),
            ),
        })(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.bad_request(ctx, explanation = errors)

    new_legislation = None
    new_legislation_title = ctx._(u'{} (copy {})').format(legislation.title, user.email)
    new_legislation_slug = strings.slugify(new_legislation_title)
    existing_legislations_cursor = model.Legislation.find(
        dict(
            slug = new_legislation_slug,
            ),
        as_class = collections.OrderedDict,
        )
    if existing_legislations_cursor.count() > 0:
        for existing_legislation in existing_legislations_cursor:
            if existing_legislation.is_owner(ctx):
                return wsgihelpers.redirect(ctx, location = existing_legislation.get_user_url(ctx))
        if new_legislation is None:
            return wsgihelpers.bad_request(
                ctx,
                explanation = ctx._(u'A legislation with the same name already exists.'),
                )
    else:
        new_legislation = model.Legislation(
            author_id = user._id,
            datetime_begin = legislation.datetime_begin,
            datetime_end = legislation.datetime_end,
            description = ctx._(u'Copy of legislation "{}"').format(legislation.title),
            title = new_legislation_title,
            slug = new_legislation_slug,
            )
        response = requests.post(
            conf['api.urls.legislations'],
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': conf['app_name'],
                },
            data = json.dumps(dict(date = data['date'].isoformat(), legislation = legislation.json)),
            )
        new_legislation.json = response.json(object_pairs_hook = collections.OrderedDict).get('dated_legislation')
        new_legislation.save(safe = True)
    return wsgihelpers.redirect(ctx, location = new_legislation.get_user_url(ctx))


@wsgihelpers.wsgify
def user_index(req):
    ctx = contexts.Ctx(req)

    params = req.GET
    inputs = dict(
        advanced_search = params.get('advanced_search'),
        page = params.get('page'),
        sort = params.get('sort'),
        term = params.get('term'),
        )
    data, errors = conv.pipe(
        conv.struct(
            dict(
                advanced_search = conv.guess_bool,
                page = conv.pipe(
                    conv.input_to_int,
                    conv.test_greater_or_equal(1),
                    conv.default(1),
                    ),
                sort = conv.pipe(
                    conv.cleanup_line,
                    conv.test_in(['slug', 'updated']),
                    ),
                term = conv.input_to_words,
                ),
            ),
        conv.rename_item('page', 'page_number'),
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.bad_request(ctx, explanation = errors)
    criteria = {}
    if data['term'] is not None:
        criteria['words'] = {'$all': [
            re.compile(u'^{}'.format(re.escape(word)))
            for word in data['term']
            ]}
    cursor = model.Legislation.find(criteria, as_class = collections.OrderedDict)
    pager = paginations.Pager(item_count = cursor.count(), page_number = data['page_number'])
    if data['sort'] == 'slug':
        cursor.sort([('slug', pymongo.ASCENDING)])
    elif data['sort'] == 'updated':
        cursor.sort([(data['sort'], pymongo.DESCENDING), ('slug', pymongo.ASCENDING)])
    legislations = cursor.skip(pager.first_item_index or 0).limit(pager.page_size)
    return templates.render(ctx, '/legislations/user-index.mako', data = data, errors = errors,
        legislations = legislations, inputs = inputs, pager = pager)


@wsgihelpers.wsgify
def user_new(req):
    ctx = contexts.Ctx(req)
    legislation = model.Legislation()
    if req.method == 'GET':
        errors = None
        inputs = extract_legislation_inputs_from_params(ctx)
    else:
        assert req.method == 'POST'
        inputs = extract_legislation_inputs_from_params(ctx, req.POST)
        data, errors = inputs_to_legislation_data(inputs, state = ctx)
        if errors is None:
            data['slug'], error = conv.pipe(
                conv.input_to_slug,
                conv.not_none,
                )(data['title'], state = ctx)
            if error is not None:
                errors = dict(title = error)
        if errors is None:
            legislation_json, error = None, None
            if data['json'] is None:
                legislation_json, error = conv.pipe(
                    conv.legislations.retrieve_legislation,
                    conv.legislations.validate_legislation_json,
                    )(data['url'], state = ctx)
            else:
                legislation_json, error = conv.legislations.validate_legislation_json(data['json'], state = ctx)
            if error is not None:
                errors = dict(json = error) if data['url'] is None else dict(url = error)
            else:
                data['json'] = legislation_json
        if errors is None:
            if model.Legislation.find(
                    dict(
                        slug = data['slug'],
                        ),
                    as_class = collections.OrderedDict,
                    ).count() > 0:
                errors = dict(full_name = ctx._(u'A legislation with the same name already exists.'))
        if errors is None:
            legislation.set_attributes(**data)
            legislation.compute_words()
            legislation.save(safe = True)

            # View legislation.
            return wsgihelpers.redirect(ctx, location = legislation.get_user_url(ctx))
    return templates.render(ctx, '/legislations/user-new.mako', errors = errors, inputs = inputs,
        legislation = legislation)


@wsgihelpers.wsgify
def user_view(req):
    ctx = contexts.Ctx(req)
    params = req.GET
    legislation = ctx.node
    date, error = conv.french_formatted_str_to_datetime(params.get('date'), state = ctx)
    if error is not None:
        return wsgihelpers.bad_request(ctx, explanation = error)
    dated_legislation_json = None
    if date is not None and not legislation.is_dated:
        response = requests.post(
            conf['api.urls.legislations'],
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': conf['app_name'],
                },
            data = json.dumps(dict(date = date.isoformat(), legislation = legislation.json)),
            )
        if not response.ok:
            error = ctx._(u'Unable to compute dated legislation')
        else:
            dated_legislation_json = response.json()
    elif legislation.is_dated:
        dated_legislation_json = legislation.json
    if error is not None:
        return wsgihelpers.bad_request(ctx, explanation = error)
    return templates.render(
        ctx,
        '/legislations/user-view.mako',
        date = date,
        legislation = legislation,
        dated_legislation_json = dated_legislation_json,
        )
