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


"""Conversion functions related to familles"""


from biryani1.states import default_state

from .. import questions, uuidhelpers
from . import base


def api_data_to_page_korma_data(values, state = None):
    if values is None:
        return None, None
    if state is None:
        state = default_state
    new_familles = []
    if values.get('familles') is not None:
        roles = ('parents', 'enfants')
        for famille_id, famille in values['familles'].iteritems():
            new_famille = {
                u'id': famille_id,
                u'individus': [],
                }
            for role in roles:
                if famille.get(role) is not None:
                    for individu_id in famille[role]:
                        new_individu = {
                            u'categories': base.build_categories(
                                columns=values['individus'][individu_id], entity_name = u'individus'),
                            u'id': individu_id,
                            u'role': role,
                            }
                        new_famille['individus'].append({u'individu': new_individu})
            columns = {key: value for key, value in famille.iteritems() if key not in roles}
            new_famille[u'categories'] = base.build_categories(columns = columns, entity_name = u'familles')
            new_familles.append({u'famille': new_famille})
    return {u'familles': new_familles}, None


def korma_data_to_page_api_data(values, state = None):
    if values is None:
        return None, None
    if state is None:
        state = default_state
    new_individus = {}
    new_familles = {}
    if values['familles'] is not None:
        for famille_group_values in values['familles']:
            famille = famille_group_values['famille']
            new_famille_id = uuidhelpers.generate_uuid() if famille['id'] is None else famille['id']
            new_famille = {}
            if famille['categories'] is not None:
                for category in famille['categories'].itervalues():
                    new_famille.update(category)
            if famille['individus'] is not None:
                for individu_group_values in famille['individus']:
                    individu = individu_group_values['individu']
                    new_individu_id = uuidhelpers.generate_uuid() if individu['id'] is None else individu['id']
                    new_individu = {}
                    if individu['categories'] is not None:
                        for category in individu['categories'].itervalues():
                            new_individu.update(category)
                    new_individus[new_individu_id] = new_individu
                    new_famille.setdefault(individu['role'], []).append(new_individu_id)
            if famille.get('add'):
                new_individu_id = uuidhelpers.generate_uuid()
                new_individus[new_individu_id] = questions.individus.build_default_values(
                    existing_individus_count=len(famille['individus']))
                new_individu_role = u'parents' if len(new_famille.get(u'parents') or []) < 2 else u'enfants'
                new_famille.setdefault(new_individu_role, []).append(new_individu_id)
            new_familles[new_famille_id] = new_famille
    if values.get('add'):
        new_famille_id = uuidhelpers.generate_uuid()
        new_familles[new_famille_id] = {}
    return {
        u'familles': new_familles,
        u'individus': new_individus,
        }, None