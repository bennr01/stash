# -*- coding: utf-8 -*-
"""
This package contains the various StaSh testcases, both for StaSh itself
as well as the individual command scripts.

Please note that the tests for command scripts were added relatively
late during StaSh's developement and have a low coverage.

If you are looking into writing your own tests for StaSh, take a look
at the L{stash.tests.stashtest} module, especially the 
L{stash.tests.stashtest.StashTestCase} class, a subclass of
L{unittest.TestCase}. It provides several utility methods and takes care
of creating and destroying the L{stash.core.StaSh} instance.

The Tests for L{stash.system} are in L{stash.tests.system}, the tests
for StaSh's lib are in L{stash.tests.lib}. Command tests are both in
L{stash.tests} for complex commands as well as in L{stash.tests.misc}
for less complex commands.
"""
pass
