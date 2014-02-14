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


"""Conversion functions related to menages"""


from biryani1.states import default_state

from .. import uuidhelpers
from . import base


singleton_roles = (u'personne_de_reference', u'conjoint')


def api_data_to_page_korma_data(values, state = None):
    if values is None:
        return None, None
    if state is None:
        state = default_state
    new_menages = []
    if values.get('menages') is not None:
        roles = (u'personne_de_reference', u'conjoint', u'enfants', u'autres')
        for menage_id, menage in values['menages'].iteritems():
            new_menage = {
                u'id': menage_id,
                u'individus': [],
                }
            for role in roles:
                if role in menage:
                    individu_ids = [menage[role]] if role in singleton_roles else menage[role]
                    for individu_id in individu_ids:
                        new_individu = {
                            u'id': individu_id,
                            u'role': role,
                            }
                        new_menage['individus'].append({u'individu': new_individu})
            columns = {key: value for key, value in menage.iteritems() if key not in roles}
            new_menage[u'categories'] = base.build_categories(columns = columns, entity_name = u'menages')
            new_menages.append({u'menage': new_menage})
    return {u'menages': new_menages}, None


def korma_data_to_page_api_data(values, state = None):
    def add_to(new_menage, role, value):
        if role in singleton_roles:
            assert role not in new_menage
            new_menage[role] = value
        else:
            new_menage.setdefault(role, []).append(value)

    if values is None:
        return None, None
    if state is None:
        state = default_state
    new_menages = {}
    for menage_group_values in values['menages']:
        menage = menage_group_values['menage']
        new_menage_id = uuidhelpers.generate_uuid() if menage['id'] is None else menage['id']
        new_menage = {}
        if menage['categories'] is not None:
            for category in menage['categories'].itervalues():
                new_menage.update(category)
        if menage['individus'] is not None:
            for individu_group_values in menage['individus']:
                individu = individu_group_values['individu']
                add_to(new_menage = new_menage, role = individu['role'], value = individu['id'])
        if menage.get('add'):
            if new_menage.get('personne_de_reference') is None:
                new_individu_role = u'personne_de_reference'
            elif new_menage.get('conjoint') is None:
                new_individu_role = u'conjoint'
            else:
                new_individu_role = u'enfants'
            add_to(new_menage = new_menage, role = new_individu_role, value = None)
        new_menages[new_menage_id] = new_menage
    if values.get('add'):
        new_menage_id = uuidhelpers.generate_uuid()
        new_menages[new_menage_id] = {}
    return {u'menages': new_menages}, None