E = {}

for swatch in 'abcde':
    E[r'.ui-bar-%s' % swatch] = {r'background-image' : ((r'linear-gradient\(<COLOR>', '%s-bar-background-gradient-start' % swatch),
                                                                            (r'bar-background-start\}\*/, <COLOR> /', '%s-bar-background-gradient-end' % swatch)),
                                                     r'text-shadow' : [(r'<VALUE>', '%s-bar-text-shadow' % swatch)]}
    E[r'.ui-body-%s .ui-link(:.*)?' % swatch] = {r'color' : [(r'<COLOR>', '%s-body-link-color' % swatch)]}
    E[r'.ui-bar-%s .ui-link' % swatch] = {r'color' : [(r'<COLOR>', '%s-bar-link-color' % swatch)]}
    E[r'.ui-bar-%s .ui-link:.*' % swatch] = {r'color' : [(r'<COLOR>', '%s-bar-link-color-hoveractivevisited' % swatch)]}
    E[r'.ui-body-%s' % swatch] = {r'border' : [(r'solid\s+<COLOR>', '%s-body-border' % swatch)],
                                                      r'background-image' : [(r'linear-gradient\(\s*<COLOR>', '%s-body-background-gradient-start' % swatch),
                                                                             (r'-start\}\*/,\s*<COLOR>', '%s-body-background-gradient-end' % swatch)]}
    for button_state in ('up', 'down', 'hover'):
        E[r'.ui-btn-%s-%s' % (button_state, swatch)] = {r'border' : [(r'solid\s+<COLOR>', '%s-btn-%s-border' % (swatch, button_state))],
                                                                            r'background-image' : [(r'linear-gradient\(\s*<COLOR>', '%s-btn-%s-gradient-start' % (swatch, button_state)),
                                                                                                   (r'-start\}\*/,\s*<COLOR>', '%s-btn-%s-gradient-end' % (swatch, button_state))]}

EXTRACT_VARIABLES = E