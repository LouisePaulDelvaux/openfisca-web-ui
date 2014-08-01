/** @jsx React.DOM */
'use strict';

var React = require('react');

var CerfaField = require('./cerfa-field');


var StringControl = React.createClass({
  propTypes: {
    cerfaField: React.PropTypes.any,
    default: React.PropTypes.string,
    error: React.PropTypes.string,
    label: React.PropTypes.component.isRequired,
    name: React.PropTypes.string.isRequired,
    onChange: React.PropTypes.func.isRequired,
    required: React.PropTypes.bool,
    suggestion: React.PropTypes.string,
    suggestionIcon: React.PropTypes.component,
    value: React.PropTypes.string,
  },
  handleChange: function(event) {
    this.props.onChange(event.target.value);
  },
  render: function() {
    return (
      <div>
        {this.props.label}
        {! this.props.error && this.props.suggestion && this.props.suggestionIcon}
        <input
          className="form-control"
          id={this.props.name}
          onChange={this.handleChange}
          placeholder={this.props.suggestion || this.props.default}
          required={this.props.required}
          type="text"
          value={this.props.value}
        />
        {
          this.props.cerfaField && (
            <div className="col-md-8">
              <CerfaField value={this.props.cerfaField} />
            </div>
          )
        }
      </div>
    );
  }
});

module.exports = StringControl;