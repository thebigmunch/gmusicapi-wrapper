# Change Log

Notable changes for the [gmusicapi-wrapper](https://github.com/thebigmunch/gmusicapi-wrapper) project. This project adheres to [Semantic Versioning](http://semver.org/).


## [0.5.0](https://github.com/thebigmunch/gmusicapi-wrapper/releases/tag/0.5.0) (2016-07-18)

[Commits](https://github.com/thebigmunch/gmusicapi-wrapper/compare/0.4.0...0.5.0)

### Added

* Add get_suggested_filename utility function.

### Changed

* Refactor template_to_filepath utility function.


## [0.4.0](https://github.com/thebigmunch/gmusicapi-wrapper/releases/tag/0.4.0) (2016-06-03)

[Commits](https://github.com/thebigmunch/gmusicapi-wrapper/compare/0.3.0...0.4.0)

### Added

* Add is_authenticated property to wrapper classes.
* Add is_subscribed property to MobileClientWrapper.
* Add exception handling to local file handlers.

### Changed

* A lot of refactoring.
* Check all metadata field values for local files when filtering. Mutagen returns list values; previously only the first item in the list was checked.
* Use wrapt module for decorators.
* Change return of MusicManagerWrapper.download method.

### Fixed

* Fix code error in MusicManagerWrapper.upload that caused an error on failed uploads.
* Fix %suggested% in template assigning same name to each song on multiple song downloads.


## [0.3.0](https://github.com/thebigmunch/gmusicapi-wrapper/releases/tag/0.3.0) (2016-02-29)

[Commits](https://github.com/thebigmunch/gmusicapi-wrapper/compare/0.2.1...0.3.0)

### Added

* Add get_local_playlists method to wrapper base class.
* Add get_local_playlist_songs method to wrapper base class.
* Add paramaters to MusicManagerWrapper.get_google_songs to enable/disable uploaded/purchased songs from being returned.
* Add get_google_playlist method to MobileClientWrapper.
* Add get_google_playlist_songs method to MobileClientWrapper.
* Add exclude_filepaths utility function.
* Add get_supported_filepaths utility function.

### Removed

* Remove exclude_path utility function.

### Changed

* Change log parameter to enable_logging in login methods.
* Change return value of MusicManagerWrapper.upload method.
* Change signature of walk_depth utility function.
* Remove formats parameter from get_local_* methods in favor of top-level constants.
* Remove recursive parameter from get_local_* methods. max-depth=0 serves the same purpose.


## [0.2.1](https://github.com/thebigmunch/gmusicapi-wrapper/releases/tag/0.2.1) (2016-02-15)

[Commits](https://github.com/thebigmunch/gmusicapi-wrapper/compare/0.2.0...0.2.1)

### Fixed

* Fix delete on success check.


## [0.2.0](https://github.com/thebigmunch/gmusicapi-wrapper/releases/tag/0.2.0) (2016-02-13)

[Commits](https://github.com/thebigmunch/gmusicapi-wrapper/compare/0.1.0...0.2.0)

### Added

* Python 3 support.

### Remove

* Python 2 support.

### Changed

* Port to Python 3. Python 2 is no longer supported.
* Add Google Music id to output for songs that already exist.

### Fixed

* Handle split number metadata fields for templates.


## [0.1.0](https://github.com/thebigmunch/gmusicapi-wrapper/releases/tag/0.1.0) (2015-12-02)

[Commits](https://github.com/thebigmunch/gmusicapi-wrapper/compare/ea58bb5fc797f358755d1f8280ea15a387c19fd2...0.1.0)

* First package release for PyPi.
