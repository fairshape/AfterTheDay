# Memory Experience product and art direction

A person records a day in a private Telegram chat or the web studio. On the table, a date, print and short quotation recall it at a glance. In Day Replay, the same materials unfold over time. Life Replay lets the author edit several published days into chapters with their original dates.

## One table, many kinds of notes

The home arranges private entries in spreads of up to three physical-looking objects. A large central note anchors smaller prints. Touching a print opens the note, where the original story, gallery and song are available beside the playback action. The paper interface uses a wooden surface and taped photographs. The neon interface uses a dark cutting mat, registration lines and lime controls. The choice belongs to the account. A light chosen for this device can be pinned independently of the automatic lighting derived from recent covers. [Interface comparison](interface-themes.jpg)

The note can take the form of a journal spread, a spare cinematic print, a collage, a geometric composition or a painterly wash. Framing, secondary print size, type and whitespace can change within a family. An illustrated sticker refers to a word in the story or its supplied details. The author can change the photo, ink or sticker and can remove the sticker. The reference brief and the actual rendering are available side by side. [Art direction brief](Memory_Experience_Art_Direction.docx) · [Print renderer](../web/scripts/memory-table.js)

## Finding and returning to a day

The five emotion collections («Светлые», «Тёплые», «Напряжённые», «Смешные», «Грустные») are views of the same archive. A record can appear in several at once. Searching for «какао» finds the original words even where the title is about the road or the park. The calendar keeps dates visible while favorite and mood filters narrow the set. The table can surface earlier memories from the same calendar date. [Collection labels](../web/scripts/museum.js) · [Mood rules](../app/services/anniversaries.py)

The day folder gives access to the untouched story and photographs alongside the edited timeline. Cover settings and the main frame can be chosen separately. The scene explanation points to concrete decisions, such as a palette sampled from the photos, measured timing, or a hold around a key phrase. Reminders bring returning viewers directly to the relevant day. The owner can choose whether the Telegram notification includes its title.

## How the same inputs travel through the product

| Input | In a note | In a replay |
| --- | --- | --- |
| Author's words | A local rule extracts a title and short quotations. The original remains in the folder. | A chosen line, a turn such as «Отправили», or a final phrase gives the edit a point to hold. |
| Photographs | Light and sampled colors guide the field, accent and print layout. A neutral fallback handles a nearly colorless image. | The saved sequence uses the actual image references, crop and camera trajectory. An explicitly chosen frame can receive a longer hold. |
| Song | The folder offers local playback for a file or an external action for a link. | A suitable uploaded file supplies an excerpt and measurable editing cues. For a link or weak cues the selected character supplies the pacing. |
| Corrections | Confirmed mood tags determine archive membership. Each day may belong to several collections. | Studio choices can change captions, duration, ordering and camera movement before the owner commits the result. |
| Voice | Optional local narration reads the full original story. | Shorter spoken lines fit into the timeline. For local music the generated mix lowers the soundtrack during speech. |

The quiet park and the waiting platform both leave space around the final words. The platform's rhythmic track supports closer cuts while the camera itself travels slowly. The park offers a controlled comparison. **Ровный монтаж** keeps the same source photographs and audio excerpt while distributing the holds evenly. The second score, **На шаг быстрее**, changes the musical input to the edit. [Three actual notes and final frames](art-direction-scenes.jpg) · [Scene comparisons](../demo/seed.py)

## Credits and media provenance

- **Team implementation.** The repository contains the capture flows, persistent draft and publication logic, authenticated media delivery, scene and palette rules, cue selection, cover compositions, original SVG sticker pack, player synchronization, local speech placement, reminder scheduling and cross-day film assembly. The [architecture](../ARCHITECTURE.md) maps these contributions to their source modules.
- **Fictional imagery.** The 17 JPEGs across six days were created for this demo using OpenAI ImageGen, including vertical frames cropped from generated contact sheets. The rain, kitchen and office sequences use three photographs each, the park and dawn three each, and the platform two. The generated oak table is separate interface artwork. [Photo assets](../demo/photos/) · [Table surface](../web/art/table.webp)
- **Music and illustrations.** The bundled tracks are original instrumental sequences synthesized locally by the demo score generator. The eight sticker drawings have Russian labels and shared selection rules. [Score generator](../demo/score.py) · [Sticker catalog](../web/art/catalog.json) · [Illustrations](../web/art/stickers/)
- **Type and voice.** The app bundles Golos Text and Cormorant Garamond Italic with their SIL Open Font Licenses. Piper models are installed separately. Consult each model card for its sources and terms. [Golos license](../web/fonts/GolosText-OFL.txt) · [Cormorant Garamond license](../web/fonts/CormorantGaramond-OFL.txt) · [Irina](https://huggingface.co/rhasspy/piper-voices/blob/main/ru/ru_RU/irina/medium/MODEL_CARD) · [Denis](https://huggingface.co/rhasspy/piper-voices/blob/main/ru/ru_RU/denis/medium/MODEL_CARD)
- **Visual references.** Rinko Kawauchi's *Illuminance* informs the change in scale from a street to a small gesture. *Apartamento* informs the domestic framing and cover type. Josef Müller-Brockmann's concert posters inform the grid and rhythmic spacing. Oblique compositions also draw on Rodchenko's photography. [Aperture](https://store.aperture.org/products/illuminance) · [Apartamento](https://www.itsnicethat.com/articles/apartamento-here-film-2016-190716) · [Müller-Brockmann](https://www.moma.org/artists/4154-josef-muller-brockmann) · [Rodchenko](https://www.moma.org/interactives/exhibitions/1998/rodchenko/texts/photography.html)

## Recorded image-generation prompts

These production prompts document the park, platform and dawn contact sheets. Personal uploads use the same scene generator as the fictional photos. Runtime generation uses local rules and the supplied photographs.

> Photorealistic editorial 35mm snapshots of one fictional autumn park walk for a private film diary. Make a landscape contact sheet split into three equal-width vertical portrait photographs, perfectly straight divisions, no gutters, no frames. Left: wide empty leaf-strewn park path receding through yellow trees beneath an overcast cool blue-grey sky. Middle: intimate close-up of two hands around a simple steaming cocoa cup with a knit sleeve, yellow leaves out of focus behind, muted amber sunlight. Right: wide unoccupied park bench with two paper cups on one end, still golden leaves and cooler shadows suggesting a conversation just finished. Restrained natural colors, soft daylight, subtle film grain. No text, logos, collage overlap, or borders.

> Photorealistic editorial 35mm diptych, two equal vertical panels in one landscape image, no borders and no text. Two photographs for the same fictional diary day. Left: empty railway platform, small bench to the far right, blue-grey late autumn diffuse daylight, symmetrical tracks recede and large clear negative space. Right: close-up of hands holding a folded, unmarked cream envelope on the same bench, muted sage and steel. Subtle authentic film grain, understated ordinary details, no timetables, logos or letters.

> Photorealistic editorial 35mm triptych in one landscape contact sheet with three equally sized straight vertical panels, no borders, no text. Three photographs for the same fictional first light city morning. Left: quiet downtown apartment window with framing and distant rooftops before dawn, cool slate. Centre: early sunlight narrowly catching a window edge across the street, small amber light, subtle dusty air. Right: wider city rooftops with clean peach gold first sunlight against muted violet sky, grounded candid natural light. No people, no signs, no logos, no collage bleed.
