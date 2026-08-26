# tools

`facecrop.swift` — turns a photo into the square avatar the app uses. Apple's Vision framework
finds the largest face, and the crop is centred on it (3.2x the face, with a little headroom)
rather than on the middle of the image, which misses the face in group shots and full-length
photos. Falls back to an upper-middle crop if no face is found.

    swift tools/facecrop.swift "Photos/Wayne.jpg" docs/photos/wayne.jpg 640

The filename must match the drafter name in `data/picks.json`, lowercased with spaces as
hyphens: "Ben Callow" -> `ben-callow.jpg`. Anyone without a photo falls back to initials.
