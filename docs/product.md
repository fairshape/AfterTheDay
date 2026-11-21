# After the Day · Genesis Hackathon ArtTech

A private film journal for the details you might forget. Send a story, a few photos, and a song to the Telegram bot. The Mini App gives the day a folder with its original materials and a short vertical scene you can play again.

The title and captions come from the author’s own words. A favorite photo or a chosen phrase earns a longer hold. Photo colors, brightness, and contrast set the background and accent. Each scrapbook cover pairs a photo print, a color field, a date stamp, and an illustrated sticker suggested from the story. The reader can change the color, sticker, or cover photo. In playback, the cover opens into the saved scene and the sticker returns once alongside a relevant caption. The music profile changes shot length, transition duration, and motion. A tense track can give way to a still frame when the text reaches a turning point. In the day folder, “Почему так выглядит день?” shows which signals shaped the scene.

“Осенний парк и какао” offers original music, a second score, and an even-paced edit of the same images and audio. “Ночь в офисе перед сдачей” moves through angular compositions and settles on “Отправили”. “Смех на кухне” cuts quicker around the dinner mishap. The other covers record the road after rain, a letter on an empty platform, and the first light over the city.

The listener can play the entire original story or enable a few spoken lines inside the scene. Piper synthesizes Russian speech on the application server. The scene uses the measured speech length to schedule each line. If an uploaded song is playing, the mix lowers its level around the voice. Linked tracks open in their own service.

## Art and implementation credits

- Rinko Kawauchi's *Illuminance* informed changes in photo scale, natural light, and attention to ordinary details. Apartamento informed strong cover type and colorful domestic imagery. Josef Müller-Brockmann's concert posters informed the repeated grid and rhythm. [Aperture](https://store.aperture.org/products/illuminance) · [It's Nice That](https://www.itsnicethat.com/articles/apartamento-here-film-2016-190716) · [MoMA](https://www.moma.org/artists/4154-josef-muller-brockmann)
- Further references include oblique composition and graphic lines in Aleksandr Rodchenko’s photography, candid domestic snapshot albums, and architectural night photography through glass. [MoMA on Rodchenko’s photography](https://www.moma.org/interactives/exhibitions/1998/rodchenko/texts/photography.html)
- The original nine fictional photos in [demo/photos](../demo/photos/) were created with built-in OpenAI ImageGen. Each prompt asked for three edge-to-edge vertical 35 mm editorial photos with natural grain and no text. The rain prompt requested a fogged Almaty bus window, hands holding hot cocoa, and a streetlight reflected in a puddle in blue and amber. The kitchen prompt requested friends laughing, hands at a pan, and burnt toast in warm tungsten light. The deadline prompt requested a diagonally framed room and laptop, a clock near 2:40, and a finger pressing a key in cool light.
- The demo instrumentals are original sequences synthesized by [demo/score.py](../demo/score.py). The repository includes no commercial recordings or samples.
- The scrapbook uses Golos Text and Old Standard TT under the SIL Open Font License. Its license is in `web/fonts/`. [Golos Text](https://github.com/google/fonts/tree/main/ofl/golostext) · [Old Standard TT](https://github.com/google/fonts/tree/main/ofl/oldstandardtt)
- The project implements the Telegram capture, persistent drafts, private archive and media API, visual rules, audio-cue selection, browser synchronization, narration placement and mixing, and demo comparison. It uses Telegram’s Mini App SDK, aiogram, FastAPI, SQLAlchemy, Alembic, Pillow, Mutagen, FFmpeg, Piper, and standard browser APIs. Local speech models are obtained separately. Voice models and their training-source notes are documented upstream. [Piper](https://github.com/OHF-Voice/piper1-gpl) · [Irina model card](https://huggingface.co/rhasspy/piper-voices/blob/main/ru/ru_RU/irina/medium/MODEL_CARD) · [Denis model card](https://huggingface.co/rhasspy/piper-voices/blob/main/ru/ru_RU/denis/medium/MODEL_CARD)

- The original sticker drawings are in [web/art/stickers](../web/art/stickers/). Their Russian labels and story cues share [one catalog](../web/art/catalog.json).


## Autumn example media

The three assets `demo/photos/park-1.jpg` through `park-3.jpg` were created with built-in OpenAI ImageGen and cropped from a contact sheet. They are fictional supplied images in the demo, available to the same scene builder as any user's uploaded photographs.

> Photorealistic editorial 35mm snapshots of one fictional autumn park walk for a private film diary. Make a landscape contact sheet split into three equal-width vertical portrait photographs, perfectly straight divisions, no gutters, no frames. Left: wide empty leaf-strewn park path receding through yellow trees beneath an overcast cool blue-grey sky. Middle: intimate close-up of two hands around a simple steaming cocoa cup with a knit sleeve, yellow leaves out of focus behind, muted amber sunlight. Right: wide unoccupied park bench with two paper cups on one end, still golden leaves and cooler shadows suggesting a conversation just finished. Restrained natural colors, soft daylight, subtle film grain. No text, logos, collage overlap, or borders.

“Тепло в ладонях” and the comparison score are synthesized by the project in `demo/score.py`. All sample synchronized playback uses the project's original scores.

## Platform and dawn example media

The five new JPEGs are cropped from two OpenAI ImageGen contact sheets. The same generator handles these fictional photos and uploaded diary photos.

> Photorealistic editorial 35mm diptych, two equal vertical panels in one landscape image, no borders and no text. Two photographs for the same fictional diary day. Left: empty railway platform, small bench to the far right, blue-grey late autumn diffuse daylight, symmetrical tracks recede and large clear negative space. Right: close-up of hands holding a folded, unmarked cream envelope on the same bench, muted sage and steel. Subtle authentic film grain, understated ordinary details, no timetables, logos or letters.

> Photorealistic editorial 35mm triptych in one landscape contact sheet with three equally sized straight vertical panels, no borders, no text. Three photographs for the same fictional first light city morning. Left: quiet downtown apartment window with framing and distant rooftops before dawn, cool slate. Centre: early sunlight narrowly catching a window edge across the street, small amber light, subtle dusty air. Right: wider city rooftops with clean peach gold first sunlight against muted violet sky, grounded candid natural light. No people, no signs, no logos, no collage bleed.
