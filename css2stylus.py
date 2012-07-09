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
import unittest

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

OPERATORS = ('>', '*', '+')

TREE_ATTRIBUTE_NAMES = ('_properties', '_order_index')

JQM_EXTRACT_VARIABLES = {}

for swatch in 'abcde':
    JQM_EXTRACT_VARIABLES[r'.ui-bar-%s' % swatch] = {r'background-image' : ((r'linear-gradient\(<COLOR>', '%s-bar-background-gradient-start' % swatch),
                                                                            (r'bar-background-start\}\*/, <COLOR> /', '%s-bar-background-gradient-end' % swatch)),
                                                     r'text-shadow' : [(r'<VALUE>', '%s-bar-text-shadow' % swatch)]}
    JQM_EXTRACT_VARIABLES[r'.ui-body-%s .ui-link(:.*)?' % swatch] = {r'color' : [(r'<COLOR>', '%s-body-link-color' % swatch)]}
    JQM_EXTRACT_VARIABLES[r'.ui-bar-%s .ui-link' % swatch] = {r'color' : [(r'<COLOR>', '%s-bar-link-color' % swatch)]}
    JQM_EXTRACT_VARIABLES[r'.ui-bar-%s .ui-link:.*' % swatch] = {r'color' : [(r'<COLOR>', '%s-bar-link-color-hoveractivevisited' % swatch)]}
    JQM_EXTRACT_VARIABLES[r'.ui-body-%s' % swatch] = {r'border' : [(r'solid\s+<COLOR>', '%s-body-border' % swatch)],
                                                      r'background-image' : [(r'linear-gradient\(\s*<COLOR>', '%s-body-background-gradient-start' % swatch),
                                                                             (r'-start\}\*/,\s*<COLOR>', '%s-body-background-gradient-end' % swatch)]}
    for button_state in ('up', 'down', 'hover'):
        JQM_EXTRACT_VARIABLES[r'.ui-btn-%s-%s' % (button_state, swatch)] = {r'border' : [(r'solid\s+<COLOR>', '%s-btn-%s-border' % (swatch, button_state))],
                                                                            r'background-image' : [(r'linear-gradient\(\s*<COLOR>', '%s-btn-%s-gradient-start' % (swatch, button_state)),
                                                                                                   (r'-start\}\*/,\s*<COLOR>', '%s-btn-%s-gradient-end' % (swatch, button_state))]}

class Css2Stylus(object):
    def _addStyleRule(self, rule, extractedVariables, variablesToExtract):
        extractVariablesMapping = {}

        # If there's exactly one selector, it can be merged with other rules
        if self._use_indented_style and len(rule['selectorList']) == 1:
            selector = rule['selectorList'][0]

            node = self._find_or_create_nested_node(selector)
        else:
            node = {'_properties': [], '_order_index' : self._order_index}
            self._order_index += 1
            self._tree[tuple(rule['selectorList'])] = node

        for selector in rule['selectorList']:
            #write_line(selector)

            if selector in variablesToExtract:
                extractVariablesMapping.update(variablesToExtract[selector])
            else:
                for selectorMatchRegex in variablesToExtract:
                    originalSelectorMatchRegex = selectorMatchRegex

                    # Force full matching
                    if not selectorMatchRegex.endswith('$'):
                        selectorMatchRegex += '$'

                    if re.match(selectorMatchRegex, selector):
                        extractVariablesMapping.update(variablesToExtract[originalSelectorMatchRegex])
                        break

        # Stores the Stylus function names that were already written out for this rule
        hadShorthand = set()

        for property in rule['properties']:
            name, value, priority = property

            # Store parts of 'value' where we inserted variable names already. These parts are excluded from regex
            # searching so that variable names are not matched accidentally.
            value_variable_ranges = []

            if name in extractVariablesMapping:
                for searchRegex, variableName in extractVariablesMapping[name]:
                    # Match colors #fff, #123456, red, white, etc.
                    searchRegex = (searchRegex.replace('<COLOR>', r'(?P<color>#[a-fA-F0-9]{3,6}|[a-z]{3,20})')
                                              .replace('<VALUE>', r'\s*(?P<value>.*)\s*'))

                    # Replace any inserted variables by underscores so that they won't get matched
                    match = re.search(searchRegex, self.replace_variable_ranges(value, value_variable_ranges))

                    if match:
                        variableValue = None

                        for groupName in ('color', 'value'):
                            if match.groupdict().get(groupName, None):
                                if variableValue is not None:
                                    raise AssertionError('Two groups in the regex matched!')

                                variableValue = match.group(groupName)
                                start, end = match.span(groupName)

                                for vstart, vend in value_variable_ranges:
                                    if self.overlaps((start, end), (vstart, vend)):
                                        raise AssertionError('Regex search overlaps with inserted variable')

                                # Inject variable name instead of the value
                                value = value[:start] + '$' + variableName + value[end:]

                                for vrange in value_variable_ranges:
                                    if vrange[0] >= start:
                                        diff = (end-start) + len('$' + variableName)
                                        vrange[0] += diff
                                        vrange[1] += diff

                                value_variable_ranges.append([start, start + len('$' + variableName)])

                        if variableValue is None:
                            raise AssertionError('Variable value of %s not found' % variableName)

                        if variableName in extractedVariables:
                            expectedVariableValue = extractedVariables[variableName][0]

                            if expectedVariableValue != variableValue:
                                raise Exception("Variable %s has ambiguous values '%s' and '%s', maybe you need to be more "
                                                "specific in your variable definiton or create two variables"
                                                % (variableName, expectedVariableValue, variableValue))

                            # Increment number of occurrences
                            extractedVariables[variableName][1] += 1
                        else:
                            extractedVariables[variableName] = [variableValue, 1]

            if name.startswith('-') and name.count('-') >= 2:
                officialName = name[2 + name[1:].index('-'):]
            else:
                officialName = None

            if (((name.startswith('-moz-') or name.startswith('-webkit-')) and
                 officialName is not None and (officialName in NIB_SHORTHANDS or name in NIB_SHORTHANDS)) or
                name in NIB_SHORTHANDS):
                stylusFunction = NIB_SHORTHANDS[officialName] if officialName in NIB_SHORTHANDS else NIB_SHORTHANDS[name]

                if stylusFunction not in hadShorthand:
                    node['_properties'].append('%s(%s%s%s)' % (stylusFunction,
                                                               value,
                                                               ' ' if priority else '',
                                                               priority))
                    #write_line('  %s(%s%s%s)' % (stylusFunction,
                    #                            value,
                    #                            ' ' if priority else '',
                    #                            priority))

                    # TODO: hadShorthand doesn't work anymore in tree mode, should be stored inside the tree
                    hadShorthand.add(stylusFunction)
            else:
                assert(name not in NIB_SHORTHANDS)
                propertyFormatted = '%s: %s%s%s' % (name,
                                                    value,
                                                    ' ' if priority else '',
                                                    priority)
                node['_properties'].append(propertyFormatted)

    def convert(self, filename, use_indented_style=False):
        """
        @param use_indented_style:
            Put rules like 'body p { color: red }' as follows:

                body
                  p
                    color: red

            The default is the CSS-like syntax:

                body p
                  color: red
        @todo:
            use_colon parameter to define whether to write 'font-size: 14px' or 'font-size 14px' (both valid Stylus syntax)
        """

        self._reset()
        self._use_indented_style = use_indented_style # TODO: actually use this setting

        with open(filename, 'rb') as f:
            css = cssutils.parseString(f.read(), validate=False)

        out = []

        # Variable name => (value, number of occurrences of that value)
        extractedVariables = {}
        variablesToExtract = JQM_EXTRACT_VARIABLES

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
            write_line = lambda line='': print(line, file=outFile)

            write_line('// THIS FILE IS AUTOGENERATED BY CSS2STYLUS')
            write_line('// ----------------------------------------')
            write_line()
            write_line('/* Functions that are not in nib library */')
            write_line('border-top-left-radius()')
            write_line('  border-top-left-radius: arguments')
            write_line('  -webkit-border-top-left-radius: arguments')
            write_line('  -moz-border-radius-topleft: arguments')
            write_line()
            write_line("@import 'nib'")

            for rule in out:
                if rule['type'] == 'style':
                    self._addStyleRule(rule, extractedVariables, variablesToExtract)
                elif rule['type'] == 'comment':
                    # TODO: does not work anymore with tree structure, rewrite to insert comments in correct order
                    self._writeCommentRule(rule, write_line)
                else:
                    raise AssertionError

            # Write out variables in alphabetical order
            extractedVariablesList = list(extractedVariables.items())
            extractedVariablesList.sort()
            for variableName, (variableValue, numOccurrences) in extractedVariablesList:
                print('Variable $%-32s = %-10s (x%d)' % (variableName, variableValue, numOccurrences))
                write_line('$%s = %s' % (variableName, variableValue))

            if extractedVariablesList:
                write_line()

            self._write_tree(write_line)

        extractedVariableNames = set(extractedVariables.keys())

        for mapping in variablesToExtract.values():
            for extractionInfos in mapping.values():
                for unusedSearchRegex, variableName in extractionInfos:
                    if variableName not in extractedVariableNames:
                        print('Warning: Variable %s not extracted, check regex' % variableName,
                              file=sys.stderr)

    @staticmethod
    def find_common_selector_parent(a, b):
        if ',' in a or ',' in b:
            raise AssertionError

        aSplit = list(filter(bool, a.split(' ')))
        bSplit = list(filter(bool, b.split(' ')))

        if any((op in aSplit or op in bSplit) for op in OPERATORS):
            # Merging rules with operators such as '>' not supported. Can they be written indented in Stylus? If so, then
            # 1) that's awesome and 2) one could just merge each operator with the next list item here.
            return None

        if aSplit == bSplit:
            raise AssertionError

        lastEqualIndex = -1
        for i in range(max(len(aSplit), len(bSplit))):
            if aSplit[i] != bSplit[i]:
                break

            lastEqualIndex = i

        if lastEqualIndex == -1:
            # No common parent
            return None

        # Some in-code unit testing :D
        assert(aSplit[:lastEqualIndex + 1] == bSplit[:lastEqualIndex + 1])

        return ' '.join(aSplit[:lastEqualIndex + 1])

    def _find_existing_parent(selector, _tree=None, _depth=0, _existingMatches=None):
        raise AssertionError("abandoned")
        """
        Recursively find node with a single selector that shares the same parent with the given selector. For example,
        if selector is 'body p ul', and the current tree is self._tree={'body':{'p':{...}}}, then the 'p' dictionary
        value should be returned.

        In other words:

            self._tree =
              body
                p
                  ...

            self._find_existing_parent('body p ul') =>

        The reverse example must work as well:

            self._tree =
              body
                p
                  ul
                    ...

            self._find_existing_parent('body p') => 'p'
        """

        # Start recursion with the top :)
        if _tree is None:
            outerRecursion = True
            _tree = self._tree

            # Tuples (depth, found dictionary)
            _existingMatches = []
        else:
            outerRecursion

        for selectorList in _tree:
            if len(selectorList) == 1 and self.find_common_selector_parent(selector, selectorList[0]):
                _existingMatches.append((_depth))

        if outerRecursion:
            # Sort by depth
            _existingMatches.sort()
            if _existingMatches:
                return _existingMatches[0]

            return None

    def _find_or_create_nested_node(self, selector):
        selectorSplit = self._split_selector(selector)

        node = self._tree

        for selectorPart in selectorSplit:
            if (selectorPart,) not in node:
                node[(selectorPart,)] = {'_properties' : [], '_order_index' : self._order_index}
                self._order_index += 1

            node = node[(selectorPart,)]

        return node

    @staticmethod
    def overlaps(range1, range2):
        s1, e1 = range1
        s2, e2 = range2

        if (e1 - s1) == 0 or (e2 - s2) == 0:
            raise AssertionError

        if e1 == s2 or e2 == s1:
            return False

        if s1 >= s2:
            if e1 <= e2:
                return True
            else:
                return e2 > s1
        elif s2 >= s1:
            if e1 <= e2:
                return e1 > s2
            else:
                return True

        return False

    @staticmethod
    def replace_variable_ranges(value, value_variable_ranges):
        ret = value

        for start, end in value_variable_ranges:
            ret = ret[:start] + (end - start) * '_' + ret[end:]

        return ret

    def _reset(self):
        # Nested dictionary where the key '_properties' represents lists of property strings (full lines). Note that keys in the
        # dictionaries are tuples of selectors. Nesting is only possible if that tuple contains exactly one selector.
        # TODO: store the order of keys somehow (in a nested way, e.g. by subclassing dict and adding a list of keys defining the order)
        self._tree = {}

        # Helper for sorting output
        self._order_index = 0

    @staticmethod
    def _split_selector(selector):
        return list(filter(bool, selector.split(' ')))

    def _writeCommentRule(self, rule, write_line):
        write_line(rule['text'])

    def _write_tree(self, write_line, _tree=None):
        if _tree is None:
            _tree = self._tree

        l = list(_tree.items())

        # Sort, and ignore any additional attributes such as k=_order_index v=0
        l.sort(key=lambda (k, v): v['_order_index'] if k not in TREE_ATTRIBUTE_NAMES else -1)


        for selectorList, sub_tree in l:
            if selectorList in TREE_ATTRIBUTE_NAMES:
                # This should not happen at top level
                assert(_tree is not self._tree)

                # This is not a selector list, but additional attributes
                continue

            write_line()

            for selector in selectorList:
                write_line(selector)

            for propertyLine in sub_tree['_properties']:
                write_line('  ' + propertyLine)

            self._write_tree(lambda s='': write_line('  ' + s), _tree=sub_tree)

class UnitTest(unittest.TestCase):
    def test_find_common_selector_parent(self):
        f = Css2Stylus.find_common_selector_parent

        self.assertEqual('body',
                         f('body p', 'body div'))

        # Should work with more whitespace
        self.assertEqual('body',
                         f(' body   p ', 'body div '))
        self.assertEqual('body',
                         f(' body   p ', ' body     div'))

        # Should return None if there is no common parent selector
        self.assertIsNone(f('p', 'body div'))

        # Operators - should be supported at some point
        self.assertIsNone(f('body p', 'body > p'))

    def test_overlaps(self):
        o = lambda s1, e1, s2, e2: Css2Stylus.overlaps((s1, e1), (s2, e2))

        self.assertRaises(AssertionError, lambda: o(1, 1, 1, 2))

        self.assertTrue(o(1, 2, 1, 2))

        self.assertTrue(o(1, 2, 1, 3))

        self.assertTrue(o(2, 3, 1, 4))
        self.assertTrue(o(1, 4, 2, 3))

        self.assertTrue(o(1, 3, 2, 3))

        self.assertTrue(o(1, 3, 2, 4))
        self.assertTrue(o(2, 4, 1, 3))

        self.assertFalse(o(1, 2, 2, 3))
        self.assertFalse(o(2, 3, 1, 2))

        self.assertFalse(o(1, 2, 3, 4))
        self.assertFalse(o(3, 4, 1, 2))

if __name__ == '__main__':
    #unittest.main()
    Css2Stylus().convert('jquery.mobile.theme-1.1.0.css', use_indented_style=True)
    #Css2Stylus().convert('test.css', use_indented_style=True)