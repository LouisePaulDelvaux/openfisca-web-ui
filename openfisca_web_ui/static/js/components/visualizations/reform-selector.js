/** @jsx React.DOM */
'use strict';

var React = require('react/addons'),
  ReactIntlMixin = require('react-intl');

var cx = React.addons.classSet;


var ReformSelector = React.createClass({
  mixins: [ReactIntlMixin],
  propTypes: {
    onChange: React.PropTypes.func.isRequired,
    value: React.PropTypes.string,
  },
  render: function() {
    var classes = value => cx({
      active: value === this.props.value,
      btn: true,
      'btn-default': true,
    });
    return (
      <div className='btn-group'>
        <button className={classes(null)} onClick={() => this.props.onChange(null)}>
          {this.getIntlMessage('reference')}
        </button>
        <button
          className={classes('plf2015')}
          onClick={() => this.props.onChange('plf2015')}
          title='Projet de loi de financement rectificative de la sécurité sociale'>
          PLF 2015
        </button>
        <button className={classes('plf2015-diff')} onClick={() => this.props.onChange('plf2015-diff')}>
          {this.getIntlMessage('difference')}
        </button>
      </div>
    );
  }
});

module.exports = ReformSelector;
