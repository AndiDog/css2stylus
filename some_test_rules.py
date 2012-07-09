"""
Example for defining your own variable extraction rules. Extracts variables from the jQuery Mobile theme. Each rule
comes with example CSS from which the value is extracted.

In order to test this, issue the following command (you need a jQuery Mobile CSS file):

    css2stylus.py convert --input jquery.mobile.theme-1.1.0.css --vars-output some_test_rules.autogen.vars --output some_test_rules.autogen.rules --vars-module some_test_rules
"""

E = {}

# Here we're extracting the whole property value "0px 0px 12px #387bbe /*...*/". You can define a search regex or just
# "<VALUE>" or "<COLOR>". "<VALUE>" will match the whole property value, while "<COLOR>" will match any valid CSS color.
#
# .ui-focus,
# .ui-btn:focus {
#     -moz-box-shadow: 0px 0px 12px         #387bbe /*{global-active-background-color}*/;
#     -webkit-box-shadow: 0px 0px 12px     #387bbe /*{global-active-background-color}*/;
#     box-shadow: 0px 0px 12px             #387bbe /*{global-active-background-color}*/;
# }
E[r'.ui-focus'] = {r'box-shadow' : [(r'<VALUE>', 'my-box-shadow')]}

# You can also extract multiple variables from one property, e.g. gradients have two values. The "<COLOR>" part of the
# regex is automatically replaced to match valid CSS colors. This example extracts two variables with the start and end
# color of the gradient, respectively.
#
# .ui-bar-a {
#    [...]
#    background-image: -webkit-linear-gradient( #3c3c3c /*{a-bar-background-start}*/, #111 /*{a-bar-background-end}*/); /* Chrome 10+, Saf5.1+ */
#    background-image:    -moz-linear-gradient( #3c3c3c /*{a-bar-background-start}*/, #111 /*{a-bar-background-end}*/); /* FF3.6 */
#    background-image:     -ms-linear-gradient( #3c3c3c /*{a-bar-background-start}*/, #111 /*{a-bar-background-end}*/); /* IE10 */
#    background-image:      -o-linear-gradient( #3c3c3c /*{a-bar-background-start}*/, #111 /*{a-bar-background-end}*/); /* Opera 11.10+ */
#    background-image:         linear-gradient( #3c3c3c /*{a-bar-background-start}*/, #111 /*{a-bar-background-end}*/);
E[r'.ui-bar-a'] = {r'background-image' : [(r'linear-gradient\(\s*<COLOR>', 'my-gradient-start'),
                                          (r'start\}\*/,\s*<COLOR>', 'my-gradient-end')]}

# This rule will give you a warning that the variable could not be extracted because the regex "background-ImAgE" does
# not match.
E[r'.ui-bar-b'] = {r'background-ImAgE' : [(r'linear-gradient\(\s*<COLOR>', 'invalid-regex-example-variable')]}

EXTRACT_VARIABLES = E