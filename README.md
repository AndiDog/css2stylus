css2stylus
==========

Summary
-------

A converter from plain CSS to Stylus. I started this project to create a Stylus file out of the jQuery Mobile standard theme, but figured it might be useful as a generic tool.

WORK IN PROGRESS!

License
-------

[The MIT License](http://www.opensource.org/licenses/mit-license.html)

Copyright (c) 2012 Andreas Sommer

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Example
-------

If you wanted to

1. extract a Stylus file from the jQuery Mobile CSS file
2. change the theme by setting your own variable values
3. merge these values together with the Stylus file into a final Stylus file containing your theme

This is how you achieve the above:

    css2stylus.py convert --input jquery.mobile.theme-1.1.0.css --vars-output jquery.mobile.theme-1.1.0.css.autogen.vars --output jquery.mobile.theme-1.1.0.css.autogen.rules --vars-module jqm_variables

    # edit values in "jquery.mobile.theme-1.1.0.css.autogen.vars" and save it as "my-theme.vars.styl"

    css2stylus.py merge --input jquery.mobile.theme-1.1.0.css.autogen.rules --vars-input my-theme.vars.styl --output path/to/output/my-theme.styl

You may want to run this in an automatic build script to re-generate your theme file when you change the values. Above, I'm mentioning "path/to/output" separately because tools like Brunch (with Stylus plugin) automatically convert all ".styl" files to regular CSS, and you only want that to happen for the final "my-theme.styl" file.

How to define yourself which variables should be extracted
----------------------------------------------------------

Please see the file `some_test_rules.py`.