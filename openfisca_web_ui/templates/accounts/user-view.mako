## -*- coding: utf-8 -*-


## OpenFisca -- A versatile microsimulation software
## By: OpenFisca Team <contact@openfisca.fr>
##
## Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
## https://github.com/openfisca
##
## This file is part of OpenFisca.
##
## OpenFisca is free software; you can redistribute it and/or modify
## it under the terms of the GNU Affero General Public License as
## published by the Free Software Foundation, either version 3 of the
## License, or (at your option) any later version.
##
## OpenFisca is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.


<%!
from openfisca_web_ui import model, urls
from openfisca_web_ui.templates import helpers
%>


<%inherit file="/site.mako"/>


<%def name="appconfig_script()" filter="trim">
window.appconfig = ${helpers.user_view_appconfig(ctx) | n, js};
</%def>


<%def name="breadcrumb_content()" filter="trim">
            <%parent:breadcrumb_content/>
            <li class="active">${_(u'My account')}</li>
</%def>


<%def name="container_content()" filter="trim">
        <div class="page-header">
            <h1>${_(u'My account')} <small>${account.get_title(ctx)}</small></h1>
        </div>
        <h2>${_(u'My simulations')}</h2>
        <div class="panel panel-default">
            <%self:view_fields/>
            <div class="panel-footer">
                <a class="btn btn-default" href="#" data-toggle="modal" data-target="#new-test-case-modal">
                    ${_(u'Add a simulation')}
                </a>
            </div>
        </div>

        <h2>${_(u'Delete my account')}</h2>
        <a class="btn btn-danger" href="#" data-toggle="modal" data-target="#delete-user-modal">
            <span class="glyphicon glyphicon-trash"></span> ${_(u'Delete my account')}
        </a>
</%def>


<%def name="delete_test_case_modal(test_case)" filter="trim">
    <div class="modal fade" id="${u'delete-test-case-{}-modal'.format(test_case.slug)}" role="dialog">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h4 class="modal-title">${_(u'Delete simulation?')}</h4>
                </div>
                <div class="modal-body">
                    <p>${_(u'Delete simulation "{}"?').format(test_case.title)}</p>
                    <form method="POST" action="${test_case.get_url(ctx, 'delete')}">
                        <button type="submit" class="btn btn-danger">${_(u'Delete')}</button>
                        <button type="button" class="btn btn-default" data-dismiss="modal">${_(u'Cancel')}</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</%def>


<%def name="delete_user_modal()" filter="trim">
    <div class="modal fade" id="delete-user-modal" role="dialog">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h4 class="modal-title">${_(u'Delete this account?')}</h4>
                </div>
                <div class="modal-body">
                    <form method="POST" action="${account.get_user_url(ctx, 'delete')}">
                        <button type="submit" class="btn btn-danger">${_(u'Delete')}</button>
                        <button type="button" class="btn btn-default" data-dismiss="modal">${_(u'Cancel')}</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</%def>


<%def name="edit_test_case_modal(test_case)" filter="trim">
    <div class="modal fade" id="${u'edit-test-case-{}-modal'.format(test_case.slug)}" role="dialog">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h4 class="modal-title">${_(u'Edit Simulation')} ${test_case.title}</h4>
                </div>
                <form action="${test_case.get_url(ctx, 'edit')}" class="form-horizontal" method="POST">
                    <div class="modal-body">
                        <div class="form-group">
                            <label class="col-sm-2 control-label">${_(u'Name')}</label>
                            <div class="col-sm-10">
                                <input type="text" class="form-control" name="title" value="${test_case.title}">
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="col-sm-2 control-label">${_(u'Description')}</label>
                            <div class="col-sm-10">
                                <textarea class="form-control" name="description">\
${test_case.description or ''}</textarea>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-success" name="submit" type="submit">${_(u'Save')}</button>
                        <button type="button" class="btn btn-default" data-dismiss="modal" aria-hidden="true">
                            ${_(u'Cancel')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</%def>


<%def name="modals()" filter="trim">
    ${new_test_case_modal()}
    % if account is not None:
        % for test_case in account.test_cases:
        ${edit_test_case_modal(test_case = test_case)}
        ${delete_test_case_modal(test_case = test_case)}
        % endfor
    % endif
        <%self:delete_user_modal/>
</%def>


<%def name="new_test_case_modal()" filter="trim">
    <div class="modal fade" id="new-test-case-modal" role="dialog">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h4 class="modal-title">${_(u'New Simulation')}</h4>
                </div>
                <form action="${model.TestCase.get_class_url(ctx, 'new')}" class="form-horizontal" method="POST">
                    <div class="modal-body">
                        <div class="form-group">
                            <label class="col-sm-2 control-label">${_(u'Name')}</label>
                            <div class="col-sm-10">
                                <input type="text" class="form-control" name="title">
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="col-sm-2 control-label">${_(u'Description')}</label>
                            <div class="col-sm-10">
                                <textarea class="form-control" name="description"></textarea>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-success" name="submit" type="submit">${_(u'Save')}</button>
                        <button type="button" class="btn btn-default" data-dismiss="modal" aria-hidden="true">
                            ${_(u'Cancel')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</%def>


<%def name="title_content()" filter="trim">
${account.get_title(ctx)} - ${parent.title_content()}
</%def>


<%def name="view_fields()" filter="trim">
        <table class="table">
            <tbody>
    % for test_case in account.test_cases:
                <tr>
                    <td>
        % if test_case._id == account.current_test_case_id:
                        <span class="glyphicon glyphicon-ok" title="${_(u'Active simulation')}"></span>
        % endif
                    </td>
                    <td><a href="${test_case.get_url(ctx, 'use')}">${test_case.title}</a></td>
                    <td>
                        <a class="btn btn-sm btn-default" \
href="${test_case.get_url(ctx, 'use', redirect = urls.get_url(ctx))}">${_(u'View')}</a>
                        <a class="btn btn-sm btn-default" href="#" data-toggle="modal" \
data-target="#${u'edit-test-case-{}-modal'.format(test_case.slug)}">${_(u'Edit')}</a>
                        <a class="btn btn-sm btn-default" href="${test_case.get_url(ctx, 'duplicate')}">
                            ${_(u'Duplicate')}
                        </a>
                        <a class="btn btn-sm btn-danger" href="#" data-toggle="modal" \
data-target="#${u'delete-test-case-{}-modal'.format(test_case.slug)}">${_(u'Delete')}</a>
                    </td>
                </tr>
    % endfor
            <tbody>
        </table>
</%def>
