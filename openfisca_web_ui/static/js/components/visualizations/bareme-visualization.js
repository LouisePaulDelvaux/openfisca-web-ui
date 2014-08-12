/** @jsx React.DOM */
'use strict';

var Lazy = require('lazy.js'),
  React = require('react'),
  strformat = require('strformat');

var axes = require('../../axes'),
  Curve = require('./svg/curve'),
  HGrid = require('./svg/h-grid'),
  Link = require('./svg/link'),
  VariablesTree = require('./variables-tree'),
  VGrid = require('./svg/v-grid'),
  XAxis = require('./svg/x-axis'),
  YAxis = require('./svg/y-axis');


var BaremeVisualization = React.createClass({
  propTypes: {
    expandedVariables: React.PropTypes.object.isRequired,
    formatNumber: React.PropTypes.func.isRequired,
    height: React.PropTypes.number.isRequired,
    marginRight: React.PropTypes.number.isRequired,
    marginTop: React.PropTypes.number.isRequired,
    onXValuesChange: React.PropTypes.func.isRequired,
    onVariableToggle: React.PropTypes.func,
    variablesTree: React.PropTypes.object.isRequired, // OpenFisca API simulation results.
    // variablesTree.values key is a list. This tells which index to use.
    width: React.PropTypes.number.isRequired,
    xAxisHeight: React.PropTypes.number.isRequired,
    xLabel: React.PropTypes.string.isRequired,
    xMaxValue: React.PropTypes.number.isRequired,
    xMinValue: React.PropTypes.number.isRequired,
    yAxisWidth: React.PropTypes.number.isRequired,
    xNbSteps: React.PropTypes.number.isRequired,
    yNbSteps: React.PropTypes.number.isRequired,
  },
  computeValuesBounds: function(variables) {
    var maxValue = 0;
    var minValue = 0;
    variables.forEach(function(variable) {
      var variableMaxValue = Math.max.apply(null, this.highValues(variable));
      if (variableMaxValue > maxValue) {
        maxValue = variableMaxValue;
      }
      var variableMinValue = Math.min.apply(null, variable.baseValues);
      if (variableMinValue < minValue) {
        minValue = variableMinValue;
      }
    }.bind(this));
    return {maxValue: maxValue, minValue: minValue};
  },
  formatHint: function(variables) {
    var variableName;
    if (this.state.activeVariableCode) {
      var variable = Lazy(variables).find({code: this.state.activeVariableCode});
      variableName = variable.name;
    } else {
      variableName = 'Survolez le graphique';
    }
    return variableName;
  },
  getDefaultProps: function() {
    return {
      marginRight: 10,
      marginTop: 10,
      xAxisHeight: 90,
      xAxisLabelFontSize: 14,
      yAxisWidth: 80,
      xNbSteps: 10,
      yNbSteps: 8,
    };
  },
  getInitialState: function() {
    return {activeVariableCode: null};
  },
  getVariables: function() {
    var processNode = function(variable, baseValues, depth, hidden) {
      var newVariables = [];
      var isCollapsed = variable.code in this.props.expandedVariables && this.props.expandedVariables[variable.code];
      if (variable.children) {
        var childrenVariables = [];
        var childBaseValues = baseValues;
        Lazy(variable.children).each(function(child) {
          var childVariables = processNode(child, childBaseValues, depth + 1, hidden || isCollapsed);
          childrenVariables = childrenVariables.concat(childVariables);
          childBaseValues = Lazy(childBaseValues).zip(child.values).map(function(pair) {
            return Lazy(pair).sum();
          }).toArray();
        });
        newVariables = newVariables.concat(childrenVariables);
      }
      var hasValue = Lazy(variable.values).any(function(value) { return value !== 0; });
      if (! hidden && hasValue) {
        var newVariableSequence = Lazy(variable).omit(['children']);
        var hasChildren = !! variable.children;
        newVariableSequence = newVariableSequence.assign({
          baseValues: baseValues,
          depth: depth,
          hasChildren: hasChildren,
          isCollapsed: isCollapsed,
          isSubtotal: hasChildren && depth > 0,
        });
        var newVariable = newVariableSequence.toObject();
        newVariables.push(newVariable);
      }
      return newVariables;
    }.bind(this);
    var initBaseValues = Lazy.repeat(0, this.props.variablesTree.values.length).toArray();
    var variables = processNode(this.props.variablesTree, initBaseValues, 0, false);
    return variables;
  },
  gridPointToPixel: function(point) {
    var pixel = {
      x: axes.convertLinearRange({
        newMax: this.gridWidth,
        newMin: 0,
        oldMax: this.props.xMaxValue,
        oldMin: this.props.xMinValue,
      }, point.x),
      y: axes.convertLinearRange({
        newMax: 0,
        newMin: this.gridHeight,
        oldMax: this.ySmartValues.maxValue,
        oldMin: this.ySmartValues.minValue,
      }, point.y),
    };
    return pixel;
  },
  handleModifyLinkClick: function() {
    function promptValue(message, defaultValue) {
      var newValue = prompt(message, defaultValue);
      if (newValue === null) {
        newValue = defaultValue;
      } else {
        newValue = Number(newValue);
        if (isNaN(newValue)) {
          alert('Valeur invalide');
          newValue = null;
        }
      }
      return newValue;
    }
    var newXMinValue = promptValue('Valeur minimum', this.props.xMinValue);
    var newXMaxValue = promptValue('Valeur maximum', this.props.xMaxValue);
    if (newXMinValue !== null && newXMaxValue !== null) {
      if (newXMinValue < newXMaxValue) {
        this.props.onXValuesChange(newXMinValue, newXMaxValue);
      } else {
        alert('La valeur minimum doit être inférieure à la valeur maximum.');
      }
    }
  },
  handleVariableHover: function(variable, event) {
    this.setState({activeVariableCode: event.type === 'mouseover' && variable ? variable.code : null});
  },
  highValues: function(variable) {
    return Lazy(variable.baseValues).zip(variable.values).map(pair => Lazy(pair).sum()).toArray();
  },
  render: function() {
    this.gridHeight = this.props.height - this.props.xAxisHeight - this.props.marginTop;
    this.gridWidth = this.props.width - this.props.yAxisWidth - this.props.marginRight;
    var variables = this.getVariables();
    var yBounds = this.computeValuesBounds(variables);
    this.ySmartValues = axes.smartValues(yBounds.minValue, yBounds.maxValue, this.props.yNbSteps);
    return (
      <div>
        <svg height={this.props.height} width={this.props.width}>
          <g transform={
            'translate(' + this.props.yAxisWidth + ', ' + (this.props.height - this.props.xAxisHeight) + ')'
          }>
            <HGrid
              height={this.gridHeight}
              nbSteps={this.props.yNbSteps}
              startStep={1}
              width={this.gridWidth}
            />
          </g>
          <g transform={'translate(' + this.props.yAxisWidth + ', ' + this.props.marginTop + ')'}>
            <VGrid
              height={this.gridHeight}
              nbSteps={this.props.xNbSteps}
              startStep={1}
              width={this.gridWidth}
            />
          </g>
          <g transform={'translate(' + this.props.yAxisWidth + ', ' + this.props.marginTop + ')'}>
            {
              variables.map(function(variable) {
                var toDomainValue = axes.convertLinearRange.bind(null, {
                  newMax: this.props.xMaxValue,
                  newMin: this.props.xMinValue,
                  oldMax: variable.values.length - 1,
                  oldMin: 0,
                });
                var lowPoints = Lazy.range(0, variable.values.length)
                  .map(toDomainValue)
                  .zip(variable.baseValues)
                  .toArray();
                var isFilled = ! variable.hasChildren && variable.depth > 0;
                var pointsSequence;
                var highPoints = Lazy.range(0, variable.values.length)
                  .map(toDomainValue)
                  .zip(this.highValues(variable))
                  .toArray();
                if (isFilled) {
                  pointsSequence = Lazy(lowPoints).concat(Lazy(highPoints).reverse().toArray());
                } else {
                  pointsSequence = Lazy(highPoints);
                }
                var points = pointsSequence.map(function(pair) { return {x: pair[0], y: pair[1]}; }).toArray();
                return (! variable.hasChildren || variable.isCollapsed || variable.depth === 0) && (
                  <Curve
                    active={this.state.activeVariableCode === variable.code}
                    fill={isFilled}
                    key={variable.code}
                    onHover={this.handleVariableHover.bind(null, variable)}
                    points={points}
                    pointToPixel={this.gridPointToPixel}
                    style={{
                      fill: isFilled ? strformat('rgb({0}, {1}, {2})', variable.color) : 'none',
                      stroke: strformat('rgb({0}, {1}, {2})', variable.color),
                    }}
                  />
                );
              }.bind(this))
            }
            <YAxis
              formatNumber={this.props.formatNumber}
              height={this.gridHeight}
              maxValue={this.ySmartValues.maxValue}
              minValue={this.ySmartValues.minValue}
              nbSteps={this.props.yNbSteps}
              unit='€'
              width={this.props.yAxisWidth}
            />
          </g>
          <g transform={
            'translate(' + this.props.yAxisWidth + ', ' + (this.props.height - this.props.xAxisHeight) + ')'
          }>
            <XAxis
              formatNumber={this.props.formatNumber}
              height={this.props.xAxisHeight}
              label={this.props.xLabel}
              labelFontSize={this.props.xAxisLabelFontSize}
              maxValue={this.props.xMaxValue}
              minValue={this.props.xMinValue}
              nbSteps={this.props.xNbSteps}
              rotateLabels={true}
              unit='€'
              width={this.gridWidth}
            />
            <Link
              onClick={this.handleModifyLinkClick}
              style={{textAnchor: 'end'}}
              x={this.gridWidth}
              y={this.props.xAxisHeight - this.props.xAxisLabelFontSize}>
              Modifier
            </Link>
          </g>
        </svg>
        <p className='well' style={{textAlign: 'center'}}>
          {this.formatHint(variables)}
        </p>
        <VariablesTree
          activeVariableCode={this.state.activeVariableCode}
          formatNumber={this.props.formatNumber}
          onToggle={this.props.onVariableToggle}
          onHover={this.handleVariableHover}
          variables={variables}
        />
      </div>
    );
  },
});

module.exports = BaremeVisualization;
