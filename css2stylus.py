#!/usr/bin/env python
"""
Dependencies:
- cssutils (http://pypi.python.org/pypi/cssutils/)
"""

from __future__ import print_function
import cssutils
import re
from StringIO import StringIO
import sys

# Browser specific name => Stylus function name
# If a -moz- or -webkit- key is mapped, the official name must be mapped also (even if the official name differs)
NIB_SHORTHANDS = {
    # Rules that are common , i.e. may have -moz- and -webkit- prefixes
    'background-clip' : 'background-clip',
    'border-radius' : 'border-radius',
    'box-shadow' : 'box-shadow',
    'border-top-left-radius' : 'border-top-left-radius',

    # Mozilla-specific (specific name without -moz- prefix varies from official name)
    '-moz-border-radius-topleft' : 'border-top-left-radius',
}

JQM_EXTRACT_VARIABLES = {}

for swatch in 'abcde':
    JQM_EXTRACT_VARIABLES['.ui-bar-%s' % swatch] = {'background-image' : ((r'linear-gradient\(<COLOR>', '%s-bar-background-gradient-start' % swatch),)}

def main(filename):
    with open(filename, 'rb') as f:
        css = cssutils.parseString(f.read(), validate=False)

    out = []

    # Variable name => (value, number of occurrences of that value)
    extractedVariables = {}

    for rule in css:
        if rule.type == rule.COMMENT:
            out.append({'type' : 'comment',
                        'text' : rule.cssText})
        elif rule.type == rule.STYLE_RULE:
            selectorList = tuple(selector.selectorText for selector in rule.selectorList)

            properties = []
            out.append({'type' : 'style',
                        'selectorList' : selectorList,
                        'properties' : properties})

            for property in rule.style:
                properties.append((property.name, property.value, property.priority))
        elif rule.type == rule.MEDIA_RULE:
            continue
        else:
            print('Unsupported rule type: %d' % rule.type, file=sys.stderr)

    print('Creating Stylus file')
    first = True

    with open(filename + '.autogen.styl', 'wb') as outFile:
        writeLine = lambda line='': print(line, file=outFile)

        writeLine('THIS FILE IS AUTOGENERATED BY CSS2STYLUS')
        writeLine('----------------------------------------')
        writeLine()
        writeLine('/* Functions that are not in nib library */')
        writeLine('border-top-left-radius()')
        writeLine('  border-top-left-radius: arguments')
        writeLine('  -webkit-border-top-left-radius: arguments')
        writeLine('  -moz-border-radius-topleft: arguments')
        writeLine()
        writeLine("@import 'nib'")
        writeLine()

        buffer = StringIO()
        writeLineBuffered = lambda line='': print(line, file=buffer)

        for rule in out:
            if first:
                first = False
            else:
                writeLineBuffered()

            if rule['type'] == 'style':
                writeStyleRule(rule, writeLineBuffered, extractedVariables)
            elif rule['type'] == 'comment':
                writeCommentRule(rule, writeLineBuffered)
            else:
                raise AssertionError

        # Write out variables in alphabetical order
        extractedVariablesList = list(extractedVariables.items())
        extractedVariablesList.sort()
        for variableName, (variableValue, numOccurrences) in extractedVariablesList:
            print('Variable $%s: %-10s (x%d)' % (variableName, variableValue, numOccurrences))
            writeLine('$%s = %s' % (variableName, variableValue))

        if extractedVariablesList:
            writeLine()

        buffer.seek(0)
        writeLine(buffer.read())

def writeCommentRule(rule, writeLine):
    writeLine(rule['text'])

def writeStyleRule(rule, writeLine, extractedVariables):
    extractVariablesMapping = {}

    for selector in rule['selectorList']:
        writeLine(selector)

        if selector in JQM_EXTRACT_VARIABLES:
            extractVariablesMapping.update(JQM_EXTRACT_VARIABLES[selector])

    # Stores the Stylus function names that were already written out for this rule
    hadShorthand = set()

    for property in rule['properties']:
        name, value, priority = property

        if name in extractVariablesMapping:
            for searchRegex, variableName in extractVariablesMapping[name]:
                # Match colors #fff, #123456, red, white, etc.
                searchRegex = searchRegex.replace('<COLOR>', r'(?P<color>#[a-fA-F0-9]{3,6}|[a-z]{3,20})')

                match = re.search(searchRegex, value)

                if match:
                    variableValue = None

                    for groupName in ('color',):
                        if match.group(groupName):
                            if variableValue is not None:
                                raise AssertionError('Two groups in the regex matched!')

                            # Inject variable name instead of the value
                            variableValue = match.group(groupName)
                            start, end = match.span(groupName)
                            value = value[:start] + '$' + variableName + value[end:]

                    if variableName in extractedVariables:
                        expectedVariableValue = extractedVariables[variableName][0]

                        if expectedVariableValue != variableValue:
                            raise Exception("Variable %s has ambiguous values '%s' and '%s', maybe you need to be more "
                                            "specific in your variable definiton or create two variables"
                                            % (variableName, expectedVariableValue, variableValue))

                        # Increment number of occurrences
                        extractedVariables[variableName] += 1
                    else:
                        extractedVariables[variableName] = (variableValue, 1)

        if name.startswith('-') and name.count('-') >= 2:
            officialName = name[2 + name[1:].index('-'):]
        else:
            officialName = None

        if ((name.startswith('-moz-') or name.startswith('-webkit-')) and
            officialName is not None and (officialName in NIB_SHORTHANDS or name in NIB_SHORTHANDS)):
            stylusFunction = NIB_SHORTHANDS[officialName] if officialName in NIB_SHORTHANDS else NIB_SHORTHANDS[name]

            if not stylusFunction in hadShorthand:
                writeLine('  %s(%s%s%s)' % (stylusFunction,
                                            value,
                                            ' ' if priority else '',
                                            priority))

                hadShorthand.add(stylusFunction)
        elif name not in NIB_SHORTHANDS or NIB_SHORTHANDS[name] not in hadShorthand:
            nameToWrite = name if name not in NIB_SHORTHANDS else NIB_SHORTHANDS[name]

            propertyFormatted = '  %s: %s%s%s' % (nameToWrite,
                                                  value,
                                                  ' ' if priority else '',
                                                  priority)
            writeLine(propertyFormatted)

            if name in NIB_SHORTHANDS:
                hadShorthand.add(NIB_SHORTHANDS[name])

if __name__ == '__main__':
    main('jquery.mobile.theme-1.1.0.css')