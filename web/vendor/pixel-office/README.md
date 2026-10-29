# Pixel Office vendor code

`layout.js` and `office.js` are reused from [basriayaz/pixel-office](https://github.com/basriayaz/pixel-office), licensed under MIT. The original license and copyright notice are in `LICENSE`.

`office.js` changes are limited to the paper-trading integration: desk drawing no longer renders the source people's legs, a `setCharacterRenderer` hook draws the project's mascot sheets, characters stay at assigned desks unless the paper-room patrol directs them, and movement speed/scale are adjusted for slower movement and narrow screens. The original project includes people sprites; those are not rendered here.
