/** @jsx React.DOM */
'use strict';

var React = require('react');

var VisualizationSelect = require('./visualization-select'),
  YearInput = require('./year-input');


var VisualizationToolbar = React.createClass({
  propTypes: {
    onVisualizationChange: React.PropTypes.func.isRequired,
    onYearChange: React.PropTypes.func.isRequired,
    visualizationSlug: React.PropTypes.string,
    year: React.PropTypes.number.isRequired,
  },
  render: function() {
    return (
      <div className="form-inline" role="form">
        <div className="form-group" style={{marginRight: 5}}>
          <VisualizationSelect
            visualizations={this.props.visualizations}
            onChange={this.props.onVisualizationChange}
            value={this.props.visualizationSlug}
          />
        </div>
        <div className="form-group" style={{marginRight: 5}}>
          <YearInput onChange={this.props.onYearChange} value={this.props.year} />
        </div>
      </div>
    );
  }
});

module.exports = VisualizationToolbar;
