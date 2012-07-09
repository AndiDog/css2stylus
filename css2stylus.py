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
    def _addStyleRule(self, rule, extracted_variables, variables_to_extract):
        extract_variables_mapping = {}

        # If there's exactly one selector, it can be merged with other rules
        if self._use_indented_style and len(rule['selector_list']) == 1:
            selector = rule['selector_list'][0]

            node = self._find_or_create_nested_node(selector)
        else:
            node = {'_properties': [], '_order_index' : self._order_index}
            self._order_index += 1
            self._tree[tuple(rule['selector_list'])] = node

        for selector in rule['selector_list']:
            #write_line(selector)

            if selector in variables_to_extract:
                extract_variables_mapping.update(variables_to_extract[selector])
            else:
                for selector_match_regex in variables_to_extract:
                    original_selector_match_regex = selector_match_regex

                    # Force full matching
                    if not selector_match_regex.endswith('$'):
                        selector_match_regex += '$'

                    if re.match(selector_match_regex, selector):
                        extract_variables_mapping.update(variables_to_extract[original_selector_match_regex])
                        break

        # Stores the Stylus function names that were already written out for this rule
        had_shorthand = set()

        for property in rule['properties']:
            name, value, priority = property

            # Store parts of 'value' where we inserted variable names already. These parts are excluded from regex
            # searching so that variable names are not matched accidentally.
            value_variable_ranges = []

            if name in extract_variables_mapping:
                for search_regex, variable_name in extract_variables_mapping[name]:
                    # Match colors #fff, #123456, red, white, etc.
                    search_regex = (search_regex.replace('<COLOR>', r'(?P<color>#[a-fA-F0-9]{3,6}|[a-z]{3,20})')
                                                .replace('<VALUE>', r'\s*(?P<value>.*)\s*'))

                    # Replace any inserted variables by underscores so that they won't get matched
                    match = re.search(search_regex, self.replace_variable_ranges(value, value_variable_ranges))

                    if match:
                        variable_value = None

                        for group_name in ('color', 'value'):
                            if match.groupdict().get(group_name, None):
                                if variable_value is not None:
                                    raise AssertionError('Two groups in the regex matched!')

                                variable_value = match.group(group_name)
                                start, end = match.span(group_name)

                                for vstart, vend in value_variable_ranges:
                                    if self.overlaps((start, end), (vstart, vend)):
                                        raise AssertionError('Regex search overlaps with inserted variable')

                                # Inject variable name instead of the value
                                value = value[:start] + '$' + variable_name + value[end:]

                                for vrange in value_variable_ranges:
                                    if vrange[0] >= start:
                                        diff = (end-start) + len('$' + variable_name)
                                        vrange[0] += diff
                                        vrange[1] += diff

                                value_variable_ranges.append([start, start + len('$' + variable_name)])

                        if variable_value is None:
                            raise AssertionError('Variable value of %s not found' % variable_name)

                        if variable_name in extracted_variables:
                            expected_variable_value = extracted_variables[variable_name][0]

                            if expected_variable_value != variable_value:
                                raise Exception("Variable %s has ambiguous values '%s' and '%s', maybe you need to be more "
                                                "specific in your variable definiton or create two variables"
                                                % (variable_name, expected_variable_value, variable_value))

                            # Increment number of occurrences
                            extracted_variables[variable_name][1] += 1
                        else:
                            extracted_variables[variable_name] = [variable_value, 1]

            if name.startswith('-') and name.count('-') >= 2:
                officialName = name[2 + name[1:].index('-'):]
            else:
                officialName = None

            if (((name.startswith('-moz-') or name.startswith('-webkit-')) and
                 officialName is not None and (officialName in NIB_SHORTHANDS or name in NIB_SHORTHANDS)) or
                name in NIB_SHORTHANDS):
                stylus_function = NIB_SHORTHANDS[officialName] if officialName in NIB_SHORTHANDS else NIB_SHORTHANDS[name]

                if stylus_function not in had_shorthand:
                    node['_properties'].append('%s(%s%s%s)' % (stylus_function,
                                                               value,
                                                               ' ' if priority else '',
                                                               priority))
                    #write_line('  %s(%s%s%s)' % (stylus_function,
                    #                            value,
                    #                            ' ' if priority else '',
                    #                            priority))

                    # TODO: had_shorthand doesn't work anymore in tree mode, should be stored inside the tree
                    had_shorthand.add(stylus_function)
            else:
                assert(name not in NIB_SHORTHANDS)
                property_formatted = '%s: %s%s%s' % (name,
                                                    value,
                                                    ' ' if priority else '',
                                                    priority)
                node['_properties'].append(property_formatted)

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
        extracted_variables = {}
        variables_to_extract = JQM_EXTRACT_VARIABLES

        for rule in css:
            if rule.type == rule.COMMENT:
                out.append({'type' : 'comment',
                            'text' : rule.cssText})
            elif rule.type == rule.STYLE_RULE:
                selector_list = tuple(selector.selectorText for selector in rule.selectorList)

                properties = []
                out.append({'type' : 'style',
                            'selector_list' : selector_list,
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
                    self._addStyleRule(rule, extracted_variables, variables_to_extract)
                elif rule['type'] == 'comment':
                    # TODO: does not work anymore with tree structure, rewrite to insert comments in correct order
                    self._writeCommentRule(rule, write_line)
                else:
                    raise AssertionError

            # Write out variables in alphabetical order
            extracted_variablesList = list(extracted_variables.items())
            extracted_variablesList.sort()
            for variable_name, (variable_value, numOccurrences) in extracted_variablesList:
                print('Variable $%-32s = %-10s (x%d)' % (variable_name, variable_value, numOccurrences))
                write_line('$%s = %s' % (variable_name, variable_value))

            if extracted_variablesList:
                write_line()

            self._write_tree(write_line)

        extractedVariableNames = set(extracted_variables.keys())

        for mapping in variables_to_extract.values():
            for extractionInfos in mapping.values():
                for unusedSearchRegex, variable_name in extractionInfos:
                    if variable_name not in extractedVariableNames:
                        print('Warning: Variable %s not extracted, check regex' % variable_name,
                              file=sys.stderr)

    @staticmethod
    def find_common_selector_parent(a, b):
        if ',' in a or ',' in b:
            raise AssertionError

        a_split = list(filter(bool, a.split(' ')))
        b_split = list(filter(bool, b.split(' ')))

        if any((op in a_split or op in b_split) for op in OPERATORS):
            # Merging rules with operators such as '>' not supported. Can they be written indented in Stylus? If so, then
            # 1) that's awesome and 2) one could just merge each operator with the next list item here.
            return None

        if a_split == b_split:
            raise AssertionError

        last_equal_index = -1
        for i in range(max(len(a_split), len(b_split))):
            if a_split[i] != b_split[i]:
                break

            last_equal_index = i

        if last_equal_index == -1:
            # No common parent
            return None

        # Some in-code unit testing :D
        assert(a_split[:last_equal_index + 1] == b_split[:last_equal_index + 1])

        return ' '.join(a_split[:last_equal_index + 1])

    def _find_existing_parent(selector, _tree=None, _depth=0, _existing_matches=None):
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
            outer_recursion = True
            _tree = self._tree

            # Tuples (depth, found dictionary)
            _existing_matches = []
        else:
            outer_recursion

        for selector_list in _tree:
            if len(selector_list) == 1 and self.find_common_selector_parent(selector, selector_list[0]):
                _existing_matches.append((_depth))

        if outer_recursion:
            # Sort by depth
            _existing_matches.sort()
            if _existing_matches:
                return _existing_matches[0]

            return None

    def _find_or_create_nested_node(self, selector):
        selector_split = self._split_selector(selector)

        node = self._tree

        for selector_part in selector_split:
            if (selector_part,) not in node:
                node[(selector_part,)] = {'_properties' : [], '_order_index' : self._order_index}
                self._order_index += 1

            node = node[(selector_part,)]

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

        for selector_list, sub_tree in l:
            if selector_list in TREE_ATTRIBUTE_NAMES:
                # This should not happen at top level
                assert(_tree is not self._tree)

                # This is not a selector list, but additional attributes
                continue

            write_line()

            for selector in selector_list:
                write_line(selector)

            for property_line in sub_tree['_properties']:
                write_line('  ' + property_line)

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