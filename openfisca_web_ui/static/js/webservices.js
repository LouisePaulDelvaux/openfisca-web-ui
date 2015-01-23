'use strict';

var $ = require('jquery'),
  Lazy = require('lazy.js'),
  request = require('superagent');

var helpers = require('./helpers');


var appconfig = global.appconfig;


function fetchCommunes(term, onComplete, onError) {
  var url = 'http://ou.comarquage.fr/api/v1/autocomplete-territory',
  data = {
    kind: ['CommuneOfFrance', 'ArrondissementOfCommuneOfFrance', 'AssociatedCommuneOfFrance'],
    term: term,
  };
  $.ajax({
    data: data,
    dataType: 'jsonp',
    jsonp: 'jsonp',
    traditional: true,
    url: url,
  })
  .done(function(data) {
    onComplete(data);
  })
  .fail(function(error) {
    onError(error);
  });
}

function fetchCurrentLocaleMessages(onComplete) {
  // TODO Throw exception, caught by window.onerror.
  var onError = () => alert('Error: unable to load language files.');
  request
    .get(`${appconfig.i18n.baseUrlPath}/${appconfig.i18n.lang}.json`)
    .set('Accept', 'application/json')
    .on('error', function(/*error*/) {
      onError();
    })
    .end(function (res) {
      if (res.error) {
        onError();
      }
      // Workaround: handle case when server returns no Content-Type HTTP header.
      var body = res.body || JSON.parse(res.text);
      onComplete(body);
    });
}

function fetchCurrentTestCase(onComplete) {
  request
    .get(appconfig.enabledModules.situationForm.urlPaths.currentTestCase)
    .on('error', function(error) {
      onComplete({error: error.message});
    })
    .end(function(res) {
      if (res.body && res.body.error) {
        onComplete(res.body);
      } else if (res.error) {
        onComplete(res);
      } else {
        onComplete({
          testCase: res.body ? res.body.test_case : null,
          testCaseAdditionalData: res.body ? res.body.test_case_additional_data : null,
        });
      }
    });
}

function fetchEntitiesMetadata(onComplete) {
  // TODO Throw exception, caught by window.onerror.
  var onError = () => alert('Error: unable to fetch entities metadata.');
  request
    .get(makeUrl(appconfig.api.urlPaths.entities))
    .on('error', function(/*error*/) {
      onError();
    })
    .end(function (res) {
      if (res.error) {
        onError();
      }
      onComplete(res.body.entities);
    });
}

function fetchFields(entitiesMetadata, onComplete) {
  request
    .get(makeUrl(appconfig.api.urlPaths.fields))
    .on('error', function(error) {
      onComplete({error: error.message});
    })
    .end(function(res) {
      if (res.body && res.body.error) {
        onComplete(res.body);
      } else if (res.error) {
        onComplete(res);
      } else if (res.body && 'columns' in res.body && 'columns_tree' in res.body) {
        onComplete({
          columns: patchColumns(res.body.columns, entitiesMetadata),
          columnsTree: res.body.columns_tree,
        });
      } else {
        onComplete({error: 'invalid fields data: no columns or no columns_tree'});
      }
    });
}


function fetchReforms(onComplete) {
  var onError = () => alert('Error: unable to fetch reforms.');
  request
    .get(makeUrl(appconfig.api.urlPaths.reforms))
    .on('error', function(/*error*/) {
      onError();
    })
    .end(function (res) {
      if (res.error) {
        onError();
      }
      onComplete(res.body.reforms);
    });
}


function makeUrl(path) {
  var baseUrl = appconfig.api.baseUrl;
  if (baseUrl.endsWith('/')) {
    baseUrl = baseUrl.slice(0, -1);
  }
  return baseUrl + path;
}

function patchColumns(columns, entitiesMetadata) {
  // Patch columns definitions to match UI specificities.
  var birth = columns.birth;
  var newColumns = {
    birth: {
      '@type': 'Integer',
      default: parseInt(birth.default.slice(0, 4)),
      label: 'Année de naissance',
      max: new Date().getFullYear(),
      min: appconfig.constants.minYear,
      val_type: 'year',
    },
  };
  var entitiesNameKeys = Lazy(entitiesMetadata).pluck('nameKey').toArray();
  var requiredColumns = Lazy(entitiesNameKeys).map(requiredColumnName => [requiredColumnName, {required: true}])
    .toObject();
  newColumns = Lazy(columns).merge(newColumns).merge(requiredColumns).toObject();
  if ('depcom' in newColumns) {
    newColumns.depcom.autocomplete = fetchCommunes;
    newColumns.depcom.label = 'Lieu de résidence';
  }
  return newColumns;
}

function patchValuesForColumns(data) {
  // Change values according to UI-specific columns.
  if (data.individus) {
    var newIndividus = Lazy(data.individus).map(function(individu, id) {
      return [
        id,
        individu.birth ?
          Lazy(individu).assign({birth: parseInt(individu.birth.slice(0, 4))}).toObject() :
          individu
      ];
    }).toObject();
    var newData = Lazy(data).assign({individus: newIndividus}).toObject();
    return newData;
  } else {
    return data;
  }
}

function repair(testCase, year, onComplete) {
  var data = {
    scenarios: [
      {
        test_case: testCase,
        year: year,
      },
    ],
    validate: true,
  };
  request
    .post(makeUrl(appconfig.api.urlPaths.simulate))
    .send(data)
    .on('error', function(error) {
      onComplete({error: error.message});
    })
    .end(function(res) {
      if (res.body && res.body.error) {
        onComplete({
          errors: res.body.error.errors[0].scenarios['0'],
          suggestions: null,
        });
      } else if (res.error) {
        onComplete(res);
      } else {
        var testCase = res.body.repaired_scenarios[0].test_case,
          suggestions = helpers.getObjectPath(res.body, 'suggestions', 'scenarios', '0', 'test_case');
        if (suggestions) {
          suggestions = patchValuesForColumns(suggestions);
        }
        testCase = patchValuesForColumns(testCase);
        onComplete({
          errors: null,
          suggestions: suggestions,
          testCase: testCase,
        });
      }
    });
}

function saveCurrentTestCase(testCase, testCaseAdditionalData, onComplete) {
  request
    .post(appconfig.enabledModules.situationForm.urlPaths.currentTestCase)
    .send({
      test_case: testCase,
      test_case_additional_data: testCaseAdditionalData,
    })
    .on('error', function(error) {
      onComplete({error: error});
    })
    .end(function(res) {
      onComplete(res.error ? res : res.body);
    });
}

function simulate(axes, decomposition, reformName, testCase, year, onComplete) {
  var scenario = {
    period: {
      start: year,
      unit: 'year',
    },
    'test_case': testCase,
  };
  if (axes) {
    scenario.axes = axes;
  }
  var data = {scenarios: [scenario]};
  if (decomposition) {
    data.decomposition = decomposition;
  }
  if (reformName) {
    data.reform_names = [reformName];
  }
  request
    .post(makeUrl(appconfig.api.urlPaths.simulate))
    .send(data)
    .on('error', function(error) {
      onComplete({error: error.message});
    })
    .end(function(res) {
      if (res.body && res.body.error) {
        var errors = res.body.error.errors[0];
        onComplete({errors: typeof errors === 'string' || ! ('scenarios' in errors) ? errors : errors.scenarios['0']});
      } else if (res.error) {
        onComplete(res);
      } else {
        onComplete(res.body.value);
      }
    });
}

module.exports = {
  fetchCurrentLocaleMessages, fetchCurrentTestCase, fetchEntitiesMetadata, fetchFields, fetchReforms, repair,
  saveCurrentTestCase, simulate,
};
