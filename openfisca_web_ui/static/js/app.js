/** @jsx React.DOM */
'use strict';


var React = require('react');

var logger = require('./logger'),
  webservices = require('./webservices');


var appconfig = global.appconfig;


function init() {
  if (appconfig.alertOnJsError) {
    window.onerror = function(/*errorMsg, url, lineNumber*/) {
      alert(appconfig.i18n.onerrorMessage);
      // TODO call send mail webservice.
      return false;
    };
  }

  var enabledModules = appconfig.enabledModules;
  if (enabledModules.auth) {
    var auth = require('./auth');
    auth.init(enabledModules.auth);
  }
  var jsModal = document.getElementById('js-modal');
  if (enabledModules.acceptCookiesModal) {
    var AcceptCookiesModal = require('./components/accept-cookies-modal');
    webservices.fetchCurrentLocaleMessages(messages => {
      React.render(
        <AcceptCookiesModal
          actionUrlPath={enabledModules.acceptCookiesModal.actionUrlPath}
          messages={messages}
        />,
        jsModal
      );
    });
  }
  else if (enabledModules.acceptCnilConditionsModal) {
    var AcceptCnilConditionsModal = require('./components/accept-cnil-conditions-modal');
    webservices.fetchCurrentLocaleMessages(messages => {
      React.render(
        <AcceptCnilConditionsModal
          actionUrlPath={enabledModules.acceptCnilConditionsModal.actionUrlPath}
          messages={messages}
          privacyPolicyUrlPath={enabledModules.acceptCnilConditionsModal.privacyPolicyUrlPath}
        />,
        jsModal
      );
    });
  }
  if ( ! enabledModules.acceptCookiesModal && ! enabledModules.acceptCnilConditionsModal) {
    if (enabledModules.disclaimer) {
      var disclaimer = require('./disclaimer');
      disclaimer.init(enabledModules.disclaimer);
    }
  }
  if (enabledModules.situationForm) {
    var renderSimulator = (entitiesMetadata, fields, messages, reforms, testCaseData) => {
      var Simulator = require('./components/simulator');
      var mountElement = document.getElementById('simulator-container');
      var {columns, columnsTree} = fields;
      var formats = {
        number: {
          currencyStyle: {
            currency: 'EUR', // TODO parametrize in appconfig
            style: 'currency',
          },
        },
      };
      React.render(
        <Simulator
          columns={columns}
          columnsTree={columnsTree}
          defaultTestCase={testCaseData && testCaseData.test_case}
          defaultTestCaseAdditionalData={testCaseData && testCaseData.test_case_additional_data}
          disableSave={Boolean(enabledModules.acceptCookiesModal)}
          entitiesMetadata={entitiesMetadata}
          formats={formats}
          locales={appconfig.i18n.lang}
          messages={messages}
          reforms={reforms}
        />,
        mountElement
      );
    };
    var fetchCurrentTestCaseIfNeeded = (onSuccess, onError) => {
      if (enabledModules.acceptCookiesModal) {
        onSuccess(null);
      } else {
        webservices.fetchCurrentTestCase(onSuccess, onError);
      }
    };
    // TODO use promise.all()
    webservices.fetchEntitiesMetadata(
      (entitiesMetadata) => {
        webservices.fetchCurrentLocaleMessages(
          (messages) => {
            // TODO fetch fields after loading app?
            webservices.fetchFields(
              entitiesMetadata,
              (fields) => {
                fetchCurrentTestCaseIfNeeded(
                  (testCaseData) => {
                    webservices.fetchReforms(
                      (reforms) => renderSimulator(entitiesMetadata, fields, messages, reforms, testCaseData),
                      (error) => {
                        logger.error(error);
                        alert('Error: unable to fetch reforms.');
                      }
                    );
                  },
                  (error) => {
                    logger.error(error);
                    alert('Error: unable to fetch current test case.');
                  }
                );
              },
              (error) => {
                logger.error(error);
                alert('Error: unable to fetch fields.');
              }
            );
          },
          (error) => {
            logger.error(error);
            alert('Error: unable to load language files.');
          }
        );
      },
      (error) => {
        logger.error(error);
        alert('Error: unable to fetch entities metadata.');
      }
    );
  }
}

module.exports = {init: init};
