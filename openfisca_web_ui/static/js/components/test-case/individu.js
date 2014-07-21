/** @jsx React.DOM */
'use strict';

var React = require('react/addons');

var cx = React.addons.classSet;


var Individu = React.createClass({
  propTypes: {
    disabled: React.PropTypes.bool,
    edited: React.PropTypes.bool,
    errors: React.PropTypes.object,
    onDelete: React.PropTypes.func.isRequired,
    onEdit: React.PropTypes.func.isRequired,
    onMove: React.PropTypes.func.isRequired,
    suggestions: React.PropTypes.object,
    value: React.PropTypes.object.isRequired,
  },
  preventDefaultThen: function(callback, event) {
    event.preventDefault();
    callback();
  },
  render: function() {
    var btnColorClass = 'btn-default';
    if (this.props.edited) {
      btnColorClass = 'btn-info';
    } else if (this.props.errors) {
      btnColorClass = 'btn-danger';
    }
    return (
      <div style={{marginBottom: '0.5em'}}>
        <div className="btn-group">
          <button
            className={cx('btn', btnColorClass, 'btn-sm')}
            disabled={this.props.disabled}
            onClick={this.props.onEdit}
            type="button">
            {this.props.value.nom_individu /* jshint ignore:line */}
          </button>
          <button
            className={cx('btn', btnColorClass, 'btn-sm', 'dropdown-toggle', this.props.disabled && 'disabled')}
            data-toggle="dropdown"
            type="button">
            <span className="caret"></span>
            <span className="sr-only">Toggle Dropdown</span>
          </button>
          <ul className="dropdown-menu" role="menu">
            <li role="presentation">
              <a
                href="#"
                onClick={this.preventDefaultThen.bind(null, this.props.onMove)}
                role="menuitem"
                tabIndex="-1">
                Déplacer
              </a>
              <a
                href="#"
                onClick={this.preventDefaultThen.bind(null, this.props.onDelete)}
                role="menuitem"
                tabIndex="-1">
                Supprimer
              </a>
            </li>
          </ul>
        </div>
        {
          this.props.suggestions && (
            <span
              className='glyphicon glyphicon-info-sign'
              style={{marginLeft: 10}}
              title='Cet individu contient des valeurs suggérées par le simulateur.'
            />
          )
        }
      </div>
    );
  }
});

module.exports = Individu;
