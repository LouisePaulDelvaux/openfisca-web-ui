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


"""Root controllers"""


import logging

from formencode import variabledecode
from korma.date import Date
from korma.group import Group, List
from korma.group import Group
from korma.repeat import Repeat
from korma.text import Number, Text

from .. import contexts, conv, matplotlib_helpers, templates, urls, wsgihelpers
from . import accounts, sessions, simulations


log = logging.getLogger(__name__)
router = None


@wsgihelpers.wsgify
def index(req):
    ctx = contexts.Ctx(req)
    first_page_forms = Repeat(
        count = 2,
        question = List(
            name = 'person_data',
            questions = [
                Text(label = u'Revenu (net mensuel)', name = 'maxrev'),
                Text(label = u'Situation'),
                Date(label = u'Date de naissance', name = 'birth'),
                Number(label = u'Année', name = 'year'),
                ]
            ),
        )

    return templates.render(ctx, '/index.mako', first_page_forms = first_page_forms)


def make_router():
    """Return a WSGI application that searches requests to controllers."""
    global router
    router = urls.make_router(
        ('GET', '^/?$', index),
        ('GET', '^/simulation?$', simulation),

        (None, '^/admin/accounts(?=/|$)', accounts.route_admin_class),
        (None, '^/admin/sessions(?=/|$)', sessions.route_admin_class),
        (None, '^/admin/simulations(?=/|$)', simulations.route_admin_class),
        (None, '^/api/1/accounts(?=/|$)', accounts.route_api1_class),
        (None, '^/api/1/simulations(?=/|$)', simulations.route_api1_class),
        ('POST', '^/login/?$', accounts.login),
        ('POST', '^/logout/?$', accounts.logout),
        )
    return router


@wsgihelpers.wsgify
def simulation(req):
    ctx = contexts.Ctx(req)
    params = req.params

    first_page_forms = Repeat(
        count = 2,
        question = List(
            name = 'person_data',
            questions = [
                Text(label = u'Revenu (net mensuel)', name = 'maxrev'),
                Text(label = u'Situation'),
                Date(label = u'Date de naissance', name = 'birth'),
                Number(label = u'Année', name = 'year'),
                ]
            ),
        )
    korma_inputs = variabledecode.variable_decode(params)
    korma_data, errors = first_page_forms.root_input_to_data(korma_inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.bad_request(ctx, explanation = ctx._(u'Error: {0}').format(errors))

    print '--- KORMA DATA {}'.format('-' * 120)
    print korma_data
    inputs = {
        'maxrev': max([person['person_data'].get('maxrev') for person in korma_inputs['repeat']]),
        'nmen': len(korma_inputs['repeat']),
        'scenarios': [{
            'indiv': [
                {
                    'birth': person['person_data'].get('birth'),
                    'noichef': 0,
                    'noidec': 0,
                    'noipref': 0,
#                    'quifam': 'chef',
#                    'quifoy': 'vous',
#                    'quimen': 'pref',
                    }
                for person in korma_inputs['repeat']
                ],
            'year': korma_inputs['repeat'][0]['person_data'].get('year') or 2006,
            }],
        'x_axis': 'sali',
        }
    print '--- INPUTS {}'.format('-' * 120)
    print inputs
    data, errors = conv.struct(
        {
            'maxrev': conv.pipe(conv.input_to_int, conv.default(14000)),
#            'nmen': conv.pipe(conv.input_to_int, conv.default(3)),
            'scenarios': conv.pipe(
                conv.uniform_sequence(
                    conv.struct(
                        {
                            'declar': conv.default({'0': {}}),
                            'famille': conv.default({'0': {}}),
                            'indiv': conv.uniform_sequence(
                                conv.struct(
                                    {
                                        'birth': conv.pipe(conv.cleanup_line, conv.not_none),
                                        'noichef': conv.pipe(conv.input_to_int, conv.default(0)),
#                                        'noidec': conv.pipe(conv.input_to_int, conv.default(0)),
#                                        'noipref': conv.pipe(conv.input_to_int, conv.default(0)),
#                                        'quifam': conv.pipe(conv.cleanup_line, conv.default('chef')),
#                                        'quifoy': conv.pipe(conv.cleanup_line, conv.default('vous')),
#                                        'quimen': conv.pipe(conv.cleanup_line, conv.default('pref')),
                                        },
                                    drop_none_values = False,
                                    ),
                                ),
                            'menage': conv.default({'0': {}}),
                            'year': conv.pipe(
                                conv.input_to_int,
                                conv.test_greater_or_equal(1950),
                                conv.test_less_or_equal(2015),
                                ),
                            },
                        ),
                    drop_none_items = True,
                    ),
                conv.test(lambda l: len(l) > 0, error = ctx._('You must provide at least one scenario')),
                ),
            'x_axis': conv.pipe(conv.default('sali'), conv.test_in(['sali'])),
            },
        )(inputs, state = ctx)
    if errors is not None:
        return wsgihelpers.bad_request(ctx, explanation = ctx._(u'Data Error: {0}').format(errors))

    simulation, errors = conv.data_to_simulation(data, state = ctx)
    if errors is not None:
        # TODO(rsoufflet) Make a real 500 internal error
        return wsgihelpers.bad_request(ctx, explanation = ctx._(u'API Error: {0}').format(errors))
    trees = simulation['value']

    matplotlib_helpers.create_waterfall_png(trees, filename = 'waterfall.png')
    matplotlib_helpers.create_bareme_png(trees, data, filename = 'bareme.png')

    return templates.render(
        ctx,
        '/simulation.mako',
        data = data,
        errors = errors,
        simulation_json = trees[0],
        img_name = '/waterfall.png',
        img2_name = '/bareme.png',
        )
