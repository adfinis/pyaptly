=========
Changelog
=========

pyaptly


Version 1.2.0
===============

released 2016-10-24T15:25:13+0000 by Jean-Louis Fuchs <ganwell@fangorn.ch>:


* Important: Because of PR  #29 pyaptly needs at least aptly 0.9.6


* Merge pull request #29 from sliverc/support_flags

 - https://github.com/adfinis-sygroup/pyaptly/pull/29
 - Added additional option to skip contents file generation in publish


* Merge pull request #30 from sliverc/add_python26_support

 - https://github.com/adfinis-sygroup/pyaptly/pull/30
 - Add python26 tests


* Merge pull request #28 from winged/do_not_expect_timestamp_in_snapshot_dict

 - https://github.com/adfinis-sygroup/pyaptly/pull/28
 - Do not expect dict-snapshots to contain timestamps


* Merge pull request #27 from msabramo/patch-4

 - https://github.com/adfinis-sygroup/pyaptly/pull/27
 - README.rst: Add PyPI badge


* Merge pull request #26 from msabramo/patch-3

 - https://github.com/adfinis-sygroup/pyaptly/pull/26
 - Fix some typos


* Merge pull request #25 from msabramo/patch-2

 - https://github.com/adfinis-sygroup/pyaptly/pull/25
 - format.rst: Fix a few typos


* Merge pull request #24 from msabramo/patch-1

 - https://github.com/adfinis-sygroup/pyaptly/pull/24
 - setup.py: Set url to GitHub repo


* Merge pull request #22 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/22
 - Updated pyproject to support version suffix


* Merge pull request #21 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/21
 - Update pyproject for CI build


* Merge pull request #20 from karras/bug_fix_snapshot_update_when_publishing_repos

 - https://github.com/adfinis-sygroup/pyaptly/pull/20
 - Fix bug when executing snapshot update



Version 1.2.0
===============

released 2016-10-24T15:19:16+0000 by Jean-Louis Fuchs <ganwell@fangorn.ch>:


* Need at least aptly version 0.9.6


* Merge pull request #30 from sliverc/add_python26_support

 - https://github.com/adfinis-sygroup/pyaptly/pull/30
 - Add python26 tests


* Merge pull request #28 from winged/do_not_expect_timestamp_in_snapshot_dict

 - https://github.com/adfinis-sygroup/pyaptly/pull/28
 - Do not expect dict-snapshots to contain timestamps


* Merge pull request #27 from msabramo/patch-4

 - https://github.com/adfinis-sygroup/pyaptly/pull/27
 - README.rst: Add PyPI badge


* Merge pull request #26 from msabramo/patch-3

 - https://github.com/adfinis-sygroup/pyaptly/pull/26
 - Fix some typos


* Merge pull request #25 from msabramo/patch-2

 - https://github.com/adfinis-sygroup/pyaptly/pull/25
 - format.rst: Fix a few typos


* Merge pull request #24 from msabramo/patch-1

 - https://github.com/adfinis-sygroup/pyaptly/pull/24
 - setup.py: Set url to GitHub repo


* Merge pull request #22 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/22
 - Updated pyproject to support version suffix


* Merge pull request #21 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/21
 - Update pyproject for CI build


* Merge branch 'master' of https://github.com/adfinis-sygroup/pyaptly

 - https://github.com/adfinis-sygroup/pyaptly/commit/87094a2


* Merge pull request #20 from karras/bug_fix_snapshot_update_when_publishing_repos

 - https://github.com/adfinis-sygroup/pyaptly/pull/20
 - Fix bug when executing snapshot update



Version 1.2.0
===============

released 2016-10-24T15:19:16+0000 by Jean-Louis Fuchs <ganwell@fangorn.ch>:


* Merge pull request #30 from sliverc/add_python26_support

 - https://github.com/adfinis-sygroup/pyaptly/pull/30
 - Add python26 tests


* Merge pull request #28 from winged/do_not_expect_timestamp_in_snapshot_dict

 - https://github.com/adfinis-sygroup/pyaptly/pull/28
 - Do not expect dict-snapshots to contain timestamps


* Merge pull request #27 from msabramo/patch-4

 - https://github.com/adfinis-sygroup/pyaptly/pull/27
 - README.rst: Add PyPI badge


* Merge pull request #26 from msabramo/patch-3

 - https://github.com/adfinis-sygroup/pyaptly/pull/26
 - Fix some typos


* Merge pull request #25 from msabramo/patch-2

 - https://github.com/adfinis-sygroup/pyaptly/pull/25
 - format.rst: Fix a few typos


* Merge pull request #24 from msabramo/patch-1

 - https://github.com/adfinis-sygroup/pyaptly/pull/24
 - setup.py: Set url to GitHub repo


* Merge pull request #23 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/23
 - Installation


* Merge pull request #22 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/22
 - Updated pyproject to support version suffix


* Merge branch 'master' of https://github.com/adfinis-sygroup/pyaptly

 - https://github.com/adfinis-sygroup/pyaptly/commit/146e7b3


* Merge pull request #21 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/21
 - Update pyproject for CI build


* Merge branch 'master' of https://github.com/adfinis-sygroup/pyaptly

 - https://github.com/adfinis-sygroup/pyaptly/commit/87094a2


* Merge pull request #20 from karras/bug_fix_snapshot_update_when_publishing_repos

 - https://github.com/adfinis-sygroup/pyaptly/pull/20
 - Fix bug when executing snapshot update



Version 1.1.0
===============

released 2016-06-15T13:21:43+0000 by Jean-Louis Fuchs <ganwell@fangorn.ch>:


* Merge pull request #15 from ganwell/feature_gpg_for_publish

 - https://github.com/adfinis-sygroup/pyaptly/pull/15
 - Update documentation about gpg-key and the gpg-agent. Read public keys and subkeys from gpg


* Merge pull request #14 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/14
 - Meta PR: Fixing PR #11 and #12


* Merge pull request #9 from winged/fix_exponential_complexity_in_read_snapshot_map

 - https://github.com/adfinis-sygroup/pyaptly/pull/9
 - Fix exponential complexity when reading snapshot map.


* Merge pull request #7 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/7
 - Making hypothesis examples smaller to avoid timeouts


* Merge pull request #6 from karras/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/6
 - Fix typos in README


* Merge pull request #5 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/5
 - Display travis badge


* Merge pull request #4 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/4
 - Update CHANGELOG


* Merge pull request #3 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/3
 - Change to public documentation location



Version 1.0.1
===============

released 2016-05-07T14:17:42+0000 by Jean-Louis Fuchs <ganwell@fangorn.ch>:


* Merge pull request #3 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/3
 - Change to public documentation location



Version 1.0.0
===============

released 2016-05-06T19:40:42+0000 by Jean-Louis Fuchs <ganwell@fangorn.ch>:


* Merge pull request #2 from ganwell/master

 - https://github.com/adfinis-sygroup/pyaptly/pull/2
 - Semi-Automatic Release of deb and rpm Packages


* Added CHANGELOG

 - https://github.com/adfinis-sygroup/pyaptly/commit/9f8ea2e
