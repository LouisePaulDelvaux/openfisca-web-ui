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
import datetime

from openfisca_web_ui import conf, model, urls
%>


<%inherit file="/site.mako"/>


<%def name="breadcrumb()" filter="trim">
</%def>


<%def name="container_content()" filter="trim">
        <div class="page-header">
            <h1>${_(u'Edit a Legislation')} <small>${legislation.get_title(ctx)}</small></h1>
        </div>
        <form method="post" role="form">
            <%self:hidden_fields/>
            <%self:error_alert/>
            <%self:form_fields/>
            <button class="btn btn-primary" name="submit" type="submit">${_(u'Save')}</button>
            <a class="btn btn-default" href="${legislation.get_user_url(ctx)}">${_(u'Cancel')}</a>
        </form>
</%def>


<%def name="form_fields()" filter="trim">
<%
    error = errors.get('title') if errors is not None else None
%>\
                <div class="form-group${' has-error' if error else ''}">
                    <label for="title">${_(u'Title')} *</label>
                    <input class="form-control" id="title" name="title" required type="text" value="${inputs['title'] or ''}">
    % if error:
                    <span class="help-block alert-danger">${error}</span>
    % endif
                </div>
<%
    error = errors.get('description') if errors is not None else None
%>\
                <div class="form-group${' has-error' if error else ''}">
                    <label for="description">${_(u'Description')}</label>
                    <textarea class="form-control" id="description" name="description">${
                        inputs['description'] or ''}</textarea>
    % if error:
                    <span class="help-block alert-danger">${error}</span>
    % endif
                </div>
<%
    error = errors.get('datetime_begin') if errors is not None else None
%>\
                <div class="form-group${' has-error' if error else ''}">
                    <label for="datetime_begin">${_(u'Begin Date')}</label>
                    <input class="form-control" id="datetime_begin" name="datetime_begin" placeholder="dd/mm/yy"
                        type="text" value="${inputs['datetime_begin'] or ''}">
    % if error:
                    <span class="help-block alert-danger">${error}</span>
    % endif
                </div>
<%
    error = errors.get('datetime_end') if errors is not None else None
%>\
                <div class="form-group${' has-error' if error else ''}">
                    <label for="datetime_end">${_(u'End Date')}</label>
                    <input class="form-control" id="datetime_end" name="datetime_end" placeholder="dd/mm/yy"
                        type="text" value="${inputs['datetime_end'] or ''}">
    % if error:
                    <span class="help-block alert-danger">${error}</span>
    % endif
                </div>
<%
    json_error = errors.get('json') if errors is not None else None
%>\
    % if json_error:
                    <p class="help-block alert-danger">${_(u'Error with source JSON')}</p>
    % endif
                <ul class="nav nav-tabs">
                    <li class="active"><a data-toggle="tab" href="#legislation-url">${_(u"URL")}</a></li>
                    <li><a data-toggle="tab" href="#legislation-json">${_(u"Source")}</a></li>
                </ul>
                <div class="tab-content">
                    <div class="active tab-pane" id="legislation-url">
<%
    error = errors.get('url') if errors is not None else None
%>\
                        <div class="form-group${' has-error' if error else ''}">
                            <label for="url">${_(u'Legislation URL')}</label>
                            <input class="form-control" id="url" name="url" type="text" value="${inputs['url'] or ''}">
    % if error:
                            <pre class="help-block alert-danger">${error | n, js, h}</pre>
    % endif
                        </div>
                    </div>
                    <div class="tab-pane" id="legislation-json">
<%
    error = errors.get('json') if errors is not None else None
%>\
                        <div class="form-group${' has-error' if error else ''}">
                            <label for="json">${_(u'Legislation JSON')}</label>
        % if inputs['json']:
                            <textarea class="form-control" id="json" name="json" rows="20">${inputs['json']}</textarea>
        % else:
                            <textarea class="form-control" id="json" name="json" rows="20"></textarea>
        % endif
    % if error:
                            <pre class="help-block alert-danger">${error | n, js, h}</pre>
    % endif
                        </div>
                    </div>
                </div>
</%def>


<%def name="hidden_fields()" filter="trim">
</%def>


<%def name="title_content()" filter="trim">
${_(u'Edit')} - ${legislation.get_title(ctx)} - ${parent.title_content()}
</%def>
