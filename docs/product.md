# After the Day · Genesis Hackathon ArtTech

A private film journal for the details you might forget. Send a story, a few photos, and a song to the Telegram bot. The Mini App gives the day a folder with its original materials and a short vertical scene you can play again.

The title and captions come from the author’s own words. A favorite photo or a chosen phrase earns a longer hold. Photo colors, brightness, and contrast set the background and accent. Each scrapbook cover pairs a photo print, a color field, a date stamp, and an illustrated sticker suggested from the story. The reader can change the color, sticker, or cover photo. In playback, the cover opens into the saved scene and the sticker returns once alongside a relevant caption. The music profile changes shot length, transition duration, and motion. A tense track can give way to a still frame when the text reaches a turning point. In the day folder, “Почему сцена выглядит так” shows which signals shaped the scene.

“Дорога после дождя” plays with two original scores. The piano version holds on the cocoa and dissolves slowly. Switching to “Огни на ходу” keeps the same words, photos, and palette, while changing the actual audio, shortening shots, and increasing motion. “Смех на кухне” uses warmer household light and a rhythmic score. “Ночь перед сдачей” moves through cool, angular compositions and comes to a stop on “Отправили”.

## Art and implementation credits

- Artistic references include oblique composition and graphic lines in Aleksandr Rodchenko’s photography, candid domestic snapshot albums, and architectural night photography through glass. [MoMA on Rodchenko’s photography](https://www.moma.org/interactives/exhibitions/1998/rodchenko/texts/photography.html)
- The nine fictional photos in [demo/photos](../demo/photos/) were created with built-in OpenAI ImageGen. Each prompt asked for three edge-to-edge vertical 35 mm editorial photos with natural grain and no text. The rain prompt requested a fogged Almaty bus window, hands holding hot cocoa, and a streetlight reflected in a puddle in blue and amber. The kitchen prompt requested friends laughing, hands at a pan, and burnt toast in warm tungsten light. The deadline prompt requested a diagonally framed room and laptop, a clock near 2:40, and a finger pressing a key in cool light.
- The demo instrumentals are original sequences synthesized by [demo/score.py](../demo/score.py). The repository includes no commercial recordings or samples.
- The scrapbook uses Golos Text under the SIL Open Font License. Its license is in `web/fonts/`. [Golos Text](https://github.com/google/fonts/tree/main/ofl/golostext)
- The project implements the Telegram capture, persistent drafts, private archive and media API, visual rules, browser playback, and demo comparison. It uses Telegram’s Mini App SDK, aiogram, FastAPI, SQLAlchemy, Alembic, Pillow, Mutagen, and standard browser APIs.

- The original sticker drawings are in [web/art/stickers](../web/art/stickers/). Their Russian labels and story cues share [one catalog](../web/art/catalog.json).


## Autumn example media

The three assets `demo/photos/park-1.jpg` through `park-3.jpg` were created with built-in OpenAI ImageGen and cropped from a contact sheet. They are fictional supplied images in the demo, available to the same scene builder as any user's uploaded photographs.

> Photorealistic editorial 35mm snapshots of one fictional autumn park walk for a private film diary. Make a landscape contact sheet split into three equal-width vertical portrait photographs, perfectly straight divisions, no gutters, no frames. Left: wide empty leaf-strewn park path receding through yellow trees beneath an overcast cool blue-grey sky. Middle: intimate close-up of two hands around a simple steaming cocoa cup with a knit sleeve, yellow leaves out of focus behind, muted amber sunlight. Right: wide unoccupied park bench with two paper cups on one end, still golden leaves and cooler shadows suggesting a conversation just finished. Restrained natural colors, soft daylight, subtle film grain. No text, logos, collage overlap, or borders.

“Тепло в ладонях” and the comparison score are synthesized by the project in `demo/score.py`. The Apple catalogue supplies links and descriptive metadata. All sample synchronized playback uses the project's original scores.
