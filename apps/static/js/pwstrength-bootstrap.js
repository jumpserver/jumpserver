/*!
* jQuery Password Strength plugin for Twitter Bootstrap
* Version: 2.2.1
*
* Copyright (c) 2008-2013 Tane Piper
* Copyright (c) 2013 Alejandro Blanco
* Dual licensed under the MIT and GPL licenses.
*/

(function (jQuery) {
// Source: src/i18n.js




var i18n = {};

(function (i18n, i18next) {
    'use strict';

    i18n.fallback = {
        "wordMinLength": "Your password is too short",
        "wordMaxLength": "Your password is too long",
        "wordInvalidChar": "Your password contains an invalid character",
        "wordNotEmail": "Do not use your email as your password",
        "wordSimilarToUsername": "Your password cannot contain your username",
        "wordTwoCharacterClasses": "Use different character classes",
        "wordRepetitions": "Too many repetitions",
        "wordSequences": "Your password contains sequences",
        "errorList": "Errors:",
        "veryWeak": "Very Weak",
        "weak": "Weak",
        "normal": "Normal",
        "medium": "Medium",
        "strong": "Strong",
        "veryStrong": "Very Strong"
    };

    i18n.t = function (key) {
        var result = '';

        // Try to use i18next.com
        if (i18next) {
            result = i18next.t(key);
        } else {
            // Fallback to english
            result = i18n.fallback[key];
        }

        return result === key ? '' : result;
    };
}(i18n, window.i18next));

// Source: src/rules.js




var rulesEngine = {};

try {
    if (!jQuery && module && module.exports) {
        var jQuery = require("jquery"),
            jsdom = require("jsdom").jsdom;
        jQuery = jQuery(jsdom().defaultView);
    }
} catch (ignore) {}

(function ($, rulesEngine) {
    "use strict";
    var validation = {};

    rulesEngine.forbiddenSequences = [
        "0123456789", "abcdefghijklmnopqrstuvwxyz", "qwertyuiop", "asdfghjkl",
        "zxcvbnm", "!@#$%^&*()_+"
    ];

    validation.wordNotEmail = function (options, word, score) {
        if (word.match(/^([\w\!\#$\%\&\'\*\+\-\/\=\?\^\`{\|\}\~]+\.)*[\w\!\#$\%\&\'\*\+\-\/\=\?\^\`{\|\}\~]+@((((([a-z0-9]{1}[a-z0-9\-]{0,62}[a-z0-9]{1})|[a-z])\.)+[a-z]{2,6})|(\d{1,3}\.){3}\d{1,3}(\:\d{1,5})?)$/i)) {
            return score;
        }
        return 0;
    };

    validation.wordMinLength = function (options, word, score) {
        var wordlen = word.length,
            lenScore = Math.pow(wordlen, options.rules.raisePower);
        if (wordlen < options.common.minChar) {
            lenScore = (lenScore + score);
        }
        return lenScore;
    };

    validation.wordMaxLength = function (options, word, score) {
        var wordlen = word.length,
            lenScore = Math.pow(wordlen, options.rules.raisePower);
        if (wordlen > options.common.maxChar) {
            return score;
        }
        return lenScore;
    };

    validation.wordInvalidChar = function (options, word, score) {
        if (options.common.invalidCharsRegExp.test(word)) {
            return score;
        }
        return 0;
    };

    validation.wordMinLengthStaticScore = function (options, word, score) {
        return word.length < options.common.minChar ? 0 : score;
    };

    validation.wordMaxLengthStaticScore = function (options, word, score) {
        return word.length > options.common.maxChar ? 0 : score;
    };


    validation.wordSimilarToUsername = function (options, word, score) {
        var username = $(options.common.usernameField).val();
        if (username && word.toLowerCase().match(username.replace(/[\-\[\]\/\{\}\(\)\*\+\=\?\:\.\\\^\$\|\!\,]/g, "\\$&").toLowerCase())) {
            return score;
        }
        return 0;
    };

    validation.wordTwoCharacterClasses = function (options, word, score) {
        if (word.match(/([a-z].*[A-Z])|([A-Z].*[a-z])/) ||
                (word.match(/([a-zA-Z])/) && word.match(/([0-9])/)) ||
                (word.match(/(.[!,@,#,$,%,\^,&,*,?,_,~])/) && word.match(/[a-zA-Z0-9_]/))) {
            return score;
        }
        return 0;
    };

    validation.wordRepetitions = function (options, word, score) {
        if (word.match(/(.)\1\1/)) { return score; }
        return 0;
    };

    validation.wordSequences = function (options, word, score) {
        var found = false,
            j;
        if (word.length > 2) {
            $.each(rulesEngine.forbiddenSequences, function (idx, seq) {
                if (found) { return; }
                var sequences = [seq, seq.split('').reverse().join('')];
                $.each(sequences, function (idx, sequence) {
                    for (j = 0; j < (word.length - 2); j += 1) { // iterate the word trough a sliding window of size 3:
                        if (sequence.indexOf(word.toLowerCase().substring(j, j + 3)) > -1) {
                            found = true;
                        }
                    }
                });
            });
            if (found) { return score; }
        }
        return 0;
    };

    validation.wordLowercase = function (options, word, score) {
        return word.match(/[a-z]/) && score;
    };

    validation.wordUppercase = function (options, word, score) {
        return word.match(/[A-Z]/) && score;
    };

    validation.wordOneNumber = function (options, word, score) {
        return word.match(/\d+/) && score;
    };

    validation.wordThreeNumbers = function (options, word, score) {
        return word.match(/(.*[0-9].*[0-9].*[0-9])/) && score;
    };

    validation.wordOneSpecialChar = function (options, word, score) {
        return word.match(/[!,@,#,$,%,\^,&,*,?,_,~]/) && score;
    };

    validation.wordTwoSpecialChar = function (options, word, score) {
        return word.match(/(.*[!,@,#,$,%,\^,&,*,?,_,~].*[!,@,#,$,%,\^,&,*,?,_,~])/) && score;
    };

    validation.wordUpperLowerCombo = function (options, word, score) {
        return word.match(/([a-z].*[A-Z])|([A-Z].*[a-z])/) && score;
    };

    validation.wordLetterNumberCombo = function (options, word, score) {
        return word.match(/([a-zA-Z])/) && word.match(/([0-9])/) && score;
    };

    validation.wordLetterNumberCharCombo = function (options, word, score) {
        return word.match(/([a-zA-Z0-9].*[!,@,#,$,%,\^,&,*,?,_,~])|([!,@,#,$,%,\^,&,*,?,_,~].*[a-zA-Z0-9])/) && score;
    };

    validation.wordIsACommonPassword = function (options, word, score) {
        if ($.inArray(word, options.rules.commonPasswords) >= 0) {
            return score;
        }
        return 0;
    };

    rulesEngine.validation = validation;

    rulesEngine.executeRules = function (options, word) {
        var totalScore = 0;

        $.each(options.rules.activated, function (rule, active) {
            if (active) {
                var score = options.rules.scores[rule],
                    funct = rulesEngine.validation[rule],
                    result,
                    errorMessage;

                if (!$.isFunction(funct)) {
                    funct = options.rules.extra[rule];
                }

                if ($.isFunction(funct)) {
                    result = funct(options, word, score);
                    if (result) {
                        totalScore += result;
                    }
                    if (result < 0 || (!$.isNumeric(result) && !result)) {
                        errorMessage = options.ui.spanError(options, rule);
                        if (errorMessage.length > 0) {
                            options.instances.errors.push(errorMessage);
                        }
                    }
                }
            }
        });

        return totalScore;
    };
}(jQuery, rulesEngine));

try {
    if (module && module.exports) {
        module.exports = rulesEngine;
    }
} catch (ignore) {}

// Source: src/options.js




var defaultOptions = {};

defaultOptions.common = {};
defaultOptions.common.minChar = 6;
defaultOptions.common.maxChar = 20;
defaultOptions.common.usernameField = "#username";
defaultOptions.common.invalidCharsRegExp = new RegExp(/[\s,'"]/);
defaultOptions.common.userInputs = [
    // Selectors for input fields with user input
];
defaultOptions.common.onLoad = undefined;
defaultOptions.common.onKeyUp = undefined;
defaultOptions.common.onScore = undefined;
defaultOptions.common.zxcvbn = false;
defaultOptions.common.zxcvbnTerms = [
    // List of disrecommended words
];
defaultOptions.common.events = ["keyup", "change", "paste"];
defaultOptions.common.debug = false;

defaultOptions.rules = {};
defaultOptions.rules.extra = {};
defaultOptions.rules.scores = {
    wordNotEmail: -100,
    wordMinLength: -50,
    wordMaxLength: -50,
    wordInvalidChar: -100,
    wordSimilarToUsername: -100,
    wordSequences: -20,
    wordTwoCharacterClasses: 2,
    wordRepetitions: -25,
    wordLowercase: 1,
    wordUppercase: 3,
    wordOneNumber: 3,
    wordThreeNumbers: 5,
    wordOneSpecialChar: 3,
    wordTwoSpecialChar: 5,
    wordUpperLowerCombo: 2,
    wordLetterNumberCombo: 2,
    wordLetterNumberCharCombo: 2,
    wordIsACommonPassword: -100
};
defaultOptions.rules.activated = {
    wordNotEmail: true,
    wordMinLength: true,
    wordMaxLength: false,
    wordInvalidChar: false,
    wordSimilarToUsername: true,
    wordSequences: true,
    wordTwoCharacterClasses: true,
    wordRepetitions: true,
    wordLowercase: true,
    wordUppercase: true,
    wordOneNumber: true,
    wordThreeNumbers: true,
    wordOneSpecialChar: true,
    wordTwoSpecialChar: true,
    wordUpperLowerCombo: true,
    wordLetterNumberCombo: true,
    wordLetterNumberCharCombo: true,
    wordIsACommonPassword: true
};
defaultOptions.rules.raisePower = 1.4;
// List taken from https://github.com/danielmiessler/SecLists (MIT License)
defaultOptions.rules.commonPasswords = [
    '123456',
    'password',
    '12345678',
    'qwerty',
    '123456789',
    '12345',
    '1234',
    '111111',
    '1234567',
    'dragon',
    '123123',
    'baseball',
    'abc123',
    'football',
    'monkey',
    'letmein',
    '696969',
    'shadow',
    'master',
    '666666',
    'qwertyuiop',
    '123321',
    'mustang',
    '1234567890',
    'michael',
    '654321',
    'pussy',
    'superman',
    '1qaz2wsx',
    '7777777',
    'fuckyou',
    '121212',
    '000000',
    'qazwsx',
    '123qwe',
    'killer',
    'trustno1',
    'jordan',
    'jennifer',
    'zxcvbnm',
    'asdfgh',
    'hunter',
    'buster',
    'soccer',
    'harley',
    'batman',
    'andrew',
    'tigger',
    'sunshine',
    'iloveyou',
    'fuckme',
    '2000',
    'charlie',
    'robert',
    'thomas',
    'hockey',
    'ranger',
    'daniel',
    'starwars',
    'klaster',
    '112233',
    'george',
    'asshole',
    'computer',
    'michelle',
    'jessica',
    'pepper',
    '1111',
    'zxcvbn',
    '555555',
    '11111111',
    '131313',
    'freedom',
    '777777',
    'pass',
    'fuck',
    'maggie',
    '159753',
    'aaaaaa',
    'ginger',
    'princess',
    'joshua',
    'cheese',
    'amanda',
    'summer',
    'love',
    'ashley',
    '6969',
    'nicole',
    'chelsea',
    'biteme',
    'matthew',
    'access',
    'yankees',
    '987654321',
    'dallas',
    'austin',
    'thunder',
    'taylor',
    'matrix'
];

defaultOptions.ui = {};
defaultOptions.ui.bootstrap2 = false;
defaultOptions.ui.bootstrap4 = false;
defaultOptions.ui.colorClasses = [
    "danger", "danger", "danger", "warning", "warning", "success"
];
defaultOptions.ui.showProgressBar = true;
defaultOptions.ui.progressBarEmptyPercentage = 1;
defaultOptions.ui.progressBarMinPercentage = 1;
defaultOptions.ui.progressExtraCssClasses = '';
defaultOptions.ui.progressBarExtraCssClasses = '';
defaultOptions.ui.showPopover = false;
defaultOptions.ui.popoverPlacement = "bottom";
defaultOptions.ui.showStatus = false;
defaultOptions.ui.spanError = function (options, key) {
    "use strict";
    var text = options.i18n.t(key);
    if (!text) { return ''; }
    return '<span style="color: #d52929">' + text + '</span>';
};
defaultOptions.ui.popoverError = function (options) {
    "use strict";
    var errors = options.instances.errors,
        errorsTitle = options.i18n.t("errorList"),
        message = "<div>" + errorsTitle + "<ul class='error-list' style='margin-bottom: 0;'>";

    jQuery.each(errors, function (idx, err) {
        message += "<li>" + err + "</li>";
    });
    message += "</ul></div>";
    return message;
};
defaultOptions.ui.showVerdicts = true;
defaultOptions.ui.showVerdictsInsideProgressBar = false;
defaultOptions.ui.useVerdictCssClass = false;
defaultOptions.ui.showErrors = false;
defaultOptions.ui.showScore = false;
defaultOptions.ui.container = undefined;
defaultOptions.ui.viewports = {
    progress: undefined,
    verdict: undefined,
    errors: undefined,
    score: undefined
};
defaultOptions.ui.scores = [0, 14, 26, 38, 50];

defaultOptions.i18n = {};
defaultOptions.i18n.t = i18n.t;

// Source: src/ui.js




var ui = {};

(function ($, ui) {
    "use strict";

    var statusClasses = ["error", "warning", "success"],
        verdictKeys = [
            "veryWeak", "weak", "normal", "medium", "strong", "veryStrong"
        ];

    ui.getContainer = function (options, $el) {
        var $container;

        $container = $(options.ui.container);
        if (!($container && $container.length === 1)) {
            $container = $el.parent();
        }
        return $container;
    };

    ui.findElement = function ($container, viewport, cssSelector) {
        if (viewport) {
            return $container.find(viewport).find(cssSelector);
        }
        return $container.find(cssSelector);
    };

    ui.getUIElements = function (options, $el) {
        var $container, result;

        if (options.instances.viewports) {
            return options.instances.viewports;
        }

        $container = ui.getContainer(options, $el);

        result = {};
        result.$progressbar = ui.findElement($container, options.ui.viewports.progress, "div.progress");
        if (options.ui.showVerdictsInsideProgressBar) {
            result.$verdict = result.$progressbar.find("span.password-verdict");
        }

        if (!options.ui.showPopover) {
            if (!options.ui.showVerdictsInsideProgressBar) {
                result.$verdict = ui.findElement($container, options.ui.viewports.verdict, "span.password-verdict");
            }
            result.$errors = ui.findElement($container, options.ui.viewports.errors, "ul.error-list");
        }
        result.$score = ui.findElement($container, options.ui.viewports.score,
                                       "span.password-score");

        options.instances.viewports = result;
        return result;
    };

    ui.initProgressBar = function (options, $el) {
        var $container = ui.getContainer(options, $el),
            progressbar = "<div class='progress ";

        if (options.ui.bootstrap2) {
            // Boostrap 2
            progressbar += options.ui.progressBarExtraCssClasses +
                "'><div class='";
        } else {
            // Bootstrap 3 & 4
            progressbar += options.ui.progressExtraCssClasses + "'><div class='" +
                options.ui.progressBarExtraCssClasses + " progress-";
        }
        progressbar += "bar'>";

        if (options.ui.showVerdictsInsideProgressBar) {
            progressbar += "<span class='password-verdict'></span>";
        }

        progressbar += "</div></div>";

        if (options.ui.viewports.progress) {
            $container.find(options.ui.viewports.progress).append(progressbar);
        } else {
            $(progressbar).insertAfter($el);
        }
    };

    ui.initHelper = function (options, $el, html, viewport) {
        var $container = ui.getContainer(options, $el);
        if (viewport) {
            $container.find(viewport).append(html);
        } else {
            $(html).insertAfter($el);
        }
    };

    ui.initVerdict = function (options, $el) {
        ui.initHelper(options, $el, "<span class='password-verdict'></span>",
                      options.ui.viewports.verdict);
    };

    ui.initErrorList = function (options, $el) {
        ui.initHelper(options, $el, "<ul class='error-list'></ul >",
                      options.ui.viewports.errors);
    };

    ui.initScore = function (options, $el) {
        ui.initHelper(options, $el, "<span class='password-score'></span>",
                      options.ui.viewports.score);
    };

    ui.initPopover = function (options, $el) {
        $el.popover("destroy");
        $el.popover({
            html: true,
            placement: options.ui.popoverPlacement,
            trigger: "manual",
            content: " "
        });
    };

    ui.initUI = function (options, $el) {
        if (options.ui.showPopover) {
            ui.initPopover(options, $el);
        } else {
            if (options.ui.showErrors) { ui.initErrorList(options, $el); }
            if (options.ui.showVerdicts && !options.ui.showVerdictsInsideProgressBar) {
                ui.initVerdict(options, $el);
            }
        }
        if (options.ui.showProgressBar) {
            ui.initProgressBar(options, $el);
        }
        if (options.ui.showScore) {
            ui.initScore(options, $el);
        }
    };

    ui.updateProgressBar = function (options, $el, cssClass, percentage) {
        var $progressbar = ui.getUIElements(options, $el).$progressbar,
            $bar = $progressbar.find(".progress-bar"),
            cssPrefix = "progress-";

        if (options.ui.bootstrap2) {
            $bar = $progressbar.find(".bar");
            cssPrefix = "";
        }

        $.each(options.ui.colorClasses, function (idx, value) {
            if (options.ui.bootstrap4) {
                $bar.removeClass("bg-" + value);
            } else {
                $bar.removeClass(cssPrefix + "bar-" + value);
            }
        });
        if (options.ui.bootstrap4) {
            $bar.addClass("bg-" + options.ui.colorClasses[cssClass]);
        } else {
            $bar.addClass(cssPrefix + "bar-" + options.ui.colorClasses[cssClass]);
        }
        $bar.css("width", percentage + '%');
    };

    ui.updateVerdict = function (options, $el, cssClass, text) {
        var $verdict = ui.getUIElements(options, $el).$verdict;
        $verdict.removeClass(options.ui.colorClasses.join(' '));
        if (cssClass > -1) {
            $verdict.addClass(options.ui.colorClasses[cssClass]);
        }
        if (options.ui.showVerdictsInsideProgressBar) {
            $verdict.css('white-space', 'nowrap');
        }
        $verdict.html(text);
    };

    ui.updateErrors = function (options, $el, remove) {
        var $errors = ui.getUIElements(options, $el).$errors,
            html = "";

        if (!remove) {
            $.each(options.instances.errors, function (idx, err) {
                html += "<li style='list-style-type:none;'>" + err + "</li>";
            });
        }
        $errors.html(html);
    };

    ui.updateScore = function (options, $el, score, remove) {
        var $score = ui.getUIElements(options, $el).$score,
            html = "";

        if (!remove) { html = score.toFixed(2); }
        $score.html(html);
    };

    ui.updatePopover = function (options, $el, verdictText, remove) {
        var popover = $el.data("bs.popover"),
            html = "",
            hide = true;

        if (options.ui.showVerdicts &&
                !options.ui.showVerdictsInsideProgressBar &&
                verdictText.length > 0) {
            html = "<h5><span class='password-verdict'>" + verdictText +
                "</span></h5>";
            hide = false;
        }
        if (options.ui.showErrors) {
            if (options.instances.errors.length > 0) {
                hide = false;
            }
            html += options.ui.popoverError(options);
        }

        if (hide || remove) {
            $el.popover("hide");
            return;
        }

        if (options.ui.bootstrap2) { popover = $el.data("popover"); }

        if (popover.$arrow && popover.$arrow.parents("body").length > 0) {
            $el.find("+ .popover .popover-content").html(html);
        } else {
            // It's hidden
            popover.options.content = html;
            $el.popover("show");
        }
    };

    ui.updateFieldStatus = function (options, $el, cssClass, remove) {
        var targetClass = options.ui.bootstrap2 ? ".control-group" : ".form-group",
            $container = $el.parents(targetClass).first();

        $.each(statusClasses, function (idx, css) {
            if (!options.ui.bootstrap2) { css = "has-" + css; }
            $container.removeClass(css);
        });

        if (remove) { return; }

        cssClass = statusClasses[Math.floor(cssClass / 2)];
        if (!options.ui.bootstrap2) { cssClass = "has-" + cssClass; }
        $container.addClass(cssClass);
    };

    ui.percentage = function (options, score, maximun) {
        var result = Math.floor(100 * score / maximun),
            min = options.ui.progressBarMinPercentage;

        result = result <= min ? min : result;
        result = result > 100 ? 100 : result;
        return result;
    };

    ui.getVerdictAndCssClass = function (options, score) {
        var level, verdict;

        if (score === undefined) { return ['', 0]; }

        if (score <= options.ui.scores[0]) {
            level = 0;
        } else if (score < options.ui.scores[1]) {
            level = 1;
        } else if (score < options.ui.scores[2]) {
            level = 2;
        } else if (score < options.ui.scores[3]) {
            level = 3;
        } else if (score < options.ui.scores[4]) {
            level = 4;
        } else {
            level = 5;
        }

        verdict = verdictKeys[level];

        return [options.i18n.t(verdict), level];
    };

    ui.updateUI = function (options, $el, score) {
        var cssClass, barPercentage, verdictText, verdictCssClass;

        cssClass = ui.getVerdictAndCssClass(options, score);
        verdictText = score === 0 ? '' : cssClass[0];
        cssClass = cssClass[1];
        verdictCssClass = options.ui.useVerdictCssClass ? cssClass : -1;

        if (options.ui.showProgressBar) {
            if (score === undefined) {
                barPercentage = options.ui.progressBarEmptyPercentage;
            } else {
                barPercentage = ui.percentage(options, score, options.ui.scores[4]);
            }
            ui.updateProgressBar(options, $el, cssClass, barPercentage);
            if (options.ui.showVerdictsInsideProgressBar) {
                ui.updateVerdict(options, $el, verdictCssClass, verdictText);
            }
        }

        if (options.ui.showStatus) {
            ui.updateFieldStatus(options, $el, cssClass, score === undefined);
        }

        if (options.ui.showPopover) {
            ui.updatePopover(options, $el, verdictText, score === undefined);
        } else {
            if (options.ui.showVerdicts && !options.ui.showVerdictsInsideProgressBar) {
                ui.updateVerdict(options, $el, verdictCssClass, verdictText);
            }
            if (options.ui.showErrors) {
                ui.updateErrors(options, $el, score === undefined);
            }
        }

        if (options.ui.showScore) {
            ui.updateScore(options, $el, score, score === undefined);
        }
    };
}(jQuery, ui));

// Source: src/methods.js




var methods = {};

(function ($, methods) {
    "use strict";
    var onKeyUp, onPaste, applyToAll;

    onKeyUp = function (event) {
        var $el = $(event.target),
            options = $el.data("pwstrength-bootstrap"),
            word = $el.val(),
            userInputs,
            verdictText,
            verdictLevel,
            score;

        if (options === undefined) { return; }

        options.instances.errors = [];
        if (word.length === 0) {
            score = undefined;
        } else {
            if (options.common.zxcvbn) {
                userInputs = [];
                $.each(options.common.userInputs.concat([options.common.usernameField]), function (idx, selector) {
                    var value = $(selector).val();
                    if (value) { userInputs.push(value); }
                });
                userInputs = userInputs.concat(options.common.zxcvbnTerms);
                score = zxcvbn(word, userInputs).guesses;
                score = Math.log(score) * Math.LOG2E;
            } else {
                score = rulesEngine.executeRules(options, word);
            }
            if ($.isFunction(options.common.onScore)) {
                score = options.common.onScore(options, word, score);
            }
        }
        ui.updateUI(options, $el, score);
        verdictText = ui.getVerdictAndCssClass(options, score);
        verdictLevel = verdictText[1];
        verdictText = verdictText[0];

        if (options.common.debug) {
            console.log(score + ' - ' + verdictText);
        }

        if ($.isFunction(options.common.onKeyUp)) {
            options.common.onKeyUp(event, {
                score: score,
                verdictText: verdictText,
                verdictLevel: verdictLevel
            });
        }
    };

    onPaste = function (event) {
        // This handler is necessary because the paste event fires before the
        // content is actually in the input, so we cannot read its value right
        // away. Therefore, the timeouts.
        var $el = $(event.target),
            word = $el.val(),
            tries = 0,
            callback;

        callback = function () {
            var newWord = $el.val();

            if (newWord !== word) {
                onKeyUp(event);
            } else if (tries < 3) {
                tries += 1;
                setTimeout(callback, 100);
            }
        };

        setTimeout(callback, 100);
    };

    methods.init = function (settings) {
        this.each(function (idx, el) {
            // Make it deep extend (first param) so it extends also the
            // rules and other inside objects
            var clonedDefaults = $.extend(true, {}, defaultOptions),
                localOptions = $.extend(true, clonedDefaults, settings),
                $el = $(el);

            localOptions.instances = {};
            $el.data("pwstrength-bootstrap", localOptions);

            $.each(localOptions.common.events, function (idx, eventName) {
                var handler = eventName === "paste" ? onPaste : onKeyUp;
                $el.on(eventName, handler);
            });

            ui.initUI(localOptions, $el);
            $el.trigger("keyup");

            if ($.isFunction(localOptions.common.onLoad)) {
                localOptions.common.onLoad();
            }
        });

        return this;
    };

    methods.destroy = function () {
        this.each(function (idx, el) {
            var $el = $(el),
                options = $el.data("pwstrength-bootstrap"),
                elements = ui.getUIElements(options, $el);
            elements.$progressbar.remove();
            elements.$verdict.remove();
            elements.$errors.remove();
            $el.removeData("pwstrength-bootstrap");
        });
    };

    methods.forceUpdate = function () {
        this.each(function (idx, el) {
            var event = { target: el };
            onKeyUp(event);
        });
    };

    methods.addRule = function (name, method, score, active) {
        this.each(function (idx, el) {
            var options = $(el).data("pwstrength-bootstrap");

            options.rules.activated[name] = active;
            options.rules.scores[name] = score;
            options.rules.extra[name] = method;
        });
    };

    applyToAll = function (rule, prop, value) {
        this.each(function (idx, el) {
            $(el).data("pwstrength-bootstrap").rules[prop][rule] = value;
        });
    };

    methods.changeScore = function (rule, score) {
        applyToAll.call(this, rule, "scores", score);
    };

    methods.ruleActive = function (rule, active) {
        applyToAll.call(this, rule, "activated", active);
    };

    methods.ruleIsMet = function (rule) {
        if ($.isFunction(rulesEngine.validation[rule])) {
            if (rule === "wordMinLength") {
                rule = "wordMinLengthStaticScore";
            } else if (rule === "wordMaxLength") {
                rule = "wordMaxLengthStaticScore";
            }

            var rulesMetCnt = 0;

            this.each(function (idx, el) {
                var options = $(el).data("pwstrength-bootstrap");

                rulesMetCnt += rulesEngine.validation[rule](options, $(el).val(), 1);
            });

            return (rulesMetCnt === this.length);
        }

        $.error("Rule " + rule + " does not exist on jQuery.pwstrength-bootstrap.validation");
    };

    $.fn.pwstrength = function (method) {
        var result;

        if (methods[method]) {
            result = methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === "object" || !method) {
            result = methods.init.apply(this, arguments);
        } else {
            $.error("Method " +  method + " does not exist on jQuery.pwstrength-bootstrap");
        }

        return result;
    };
}(jQuery, methods));
}(jQuery));